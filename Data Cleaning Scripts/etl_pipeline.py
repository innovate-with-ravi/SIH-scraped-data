from stage2_semantic_chunker_for_aahar import process_ayurveda_aahara
import json
from pathlib import Path
import sys

# Import stages
try:
    from stage1_hybrid_extractor import extract_hybrid
    from stage2_semantic_chunker import process_stage2
    from stage3_semantic_filter import stage3_filter
except ImportError as e:
    print(f"Error importing pipeline stages: {e}. Make sure they are in the same directory.")
    sys.exit(1)

from google import genai
from dotenv import load_dotenv

# Import metadata map
from document_metadata import DOCUMENT_METADATA_MAP


def process_pipeline(raw_pdfs_dir: Path):
    """
    Executes Stage 1 (Extraction), Stage 2 (Semantic Chunking & Metadata Injection),
    and Stage 3 (Semantic Filtering) of the ETL pipeline.
    Saves the output JSONs individually next to each PDF.
    """
    print("Initializing Gemini Client for Stage 3 embeddings...")
    load_dotenv()
    client = genai.Client()

    print(f"Starting pipeline on: {raw_pdfs_dir}")

    # Support passing either a single file or a directory
    if raw_pdfs_dir.is_file():
        pdf_paths = [raw_pdfs_dir]
    else:
        pdf_paths = list(raw_pdfs_dir.rglob("*.pdf"))

    total_chunks_parsed = 0
    total_relevant = 0
    total_discarded = 0

    # Process each PDF through Stage 1, Stage 2, and Stage 3
    for pdf_path in pdf_paths:
        print(f"\n--- Processing Document: {pdf_path.name} ---")
        
        processing_dir = pdf_path.parent / f"processing_{pdf_path.stem}"
        processing_dir.mkdir(exist_ok=True)
        
        md_output_path = processing_dir / f"{pdf_path.stem}.md"
        relevant_json_path = processing_dir / f"{pdf_path.stem}_relevant_chunks.json"
        discarded_json_path = processing_dir / f"{pdf_path.stem}_discarded_chunks.json"
        all_chunks_path = processing_dir / f"{pdf_path.stem}_all_chunks.json"
        
        if all_chunks_path.exists():
            print(f"[Stage 1 & 2] Skipping parsing, loading existing chunks from {all_chunks_path.name}")
            with open(all_chunks_path, "r", encoding="utf-8") as f:
                chunks_data = json.load(f)
        else:
            # --- STAGE 1: Extraction ---
            if not md_output_path.exists():
                print(f"[Stage 1] Extracting markdown to {md_output_path.name}...")
                extract_hybrid(str(pdf_path), str(md_output_path))
            else:
                print(f"[Stage 1] Markdown already exists for {pdf_path.name}, using existing file.")
                
            if not md_output_path.exists():
                print(f"[Warning] Skipping {pdf_path.name} as markdown extraction failed or file not found.")
                continue
                
            # # ----------------------------------------------------------------- #
            # # stage1_hybrid_extractor then continue to next-pdf
            # continue
            
            # Read the extracted markdown content
            with open(md_output_path, "r", encoding="utf-8") as f:
                md_content = f.read()
                
            # Get metadata for the current file
            filename = pdf_path.name
            global_metadata = DOCUMENT_METADATA_MAP.get(filename, {})
            
            # --- STAGE 2: Semantic Chunking & Rich Metadata Injection ---
            print(f"[Stage 2] Semantic chunking and metadata injection...")
            # merged_md_content, chunks_data = process_stage2(md_content, filename, global_metadata)
            merged_md_content, chunks_data = process_ayurveda_aahara(md_content, filename, global_metadata)
            
            # Update the markdown file with merged md content
            print(f"[Stage 2] Updating {md_output_path.name} with merged headings content...")
            with open(md_output_path, 'w', encoding='utf-8') as f:
                f.write(merged_md_content)

            # # -----------testing aahar.pdf---------------- #
            # with open(all_chunks_path, "w", encoding="utf-8") as f:
            #     json.dump(chunks_data, f, indent=4, ensure_ascii=False)
            # return

        # --- STAGE 3: Semantic Filtering ---
        print(f"[Stage 3] Semantic Filtering for {pdf_path.name}...")
        relevant_chunks, discarded_chunks = stage3_filter(chunks_data, client, threshold=0.30)
        
        # Save all chunks (now with vectors injected by stage3 directly in chunks_data)
        if not all_chunks_path.exists():
            with open(all_chunks_path, "w", encoding="utf-8") as f:
                json.dump(chunks_data, f, indent=4, ensure_ascii=False)
        
        # Save the relevant chunks
        with open(relevant_json_path, "w", encoding="utf-8") as f:
            json.dump(relevant_chunks, f, indent=4, ensure_ascii=False)
            
        # Save the discarded chunks for review
        with open(discarded_json_path, "w", encoding="utf-8") as f:
            json.dump(discarded_chunks, f, indent=4, ensure_ascii=False)
            
        print(f"Saved: {relevant_json_path.name}")
        print(f"Saved: {discarded_json_path.name}")
        
        total_chunks_parsed += len(chunks_data)
        total_relevant += len(relevant_chunks)
        total_discarded += len(discarded_chunks)
        
    # shows total for the given dir or file & not for each file
    print(f"\nPipeline successfully completed for {raw_pdfs_dir.stem} dir or file:!")
    print(f"Total chunks parsed: {total_chunks_parsed}")
    print(f"Total relevant chunks: {total_relevant}")
    print(f"Total discarded chunks: {total_discarded}")


if __name__ == "__main__":
    # Define directories and outputs
    # RAW_PDFS_DIR = Path(r"D:\CODING\Hackathons\SIH\SIH-scraped-data\raw_data\raw_pdfs\01-IP_Laws\1_113_1_The_Patents_Act__1970___incorporating_all_amendments_till_1-08-2024.pdf")
    RAW_PDFS_DIR = Path(r"D:\CODING\Hackathons\SIH\SIH-scraped-data\raw_data\raw_pdfs\05-ayurveda_aahara\68835f872eaf4Order dated 25-07-2025 enclosing Ayurveda Aahara.pdf")
    
    if not RAW_PDFS_DIR.exists():
        print(f"Error: Raw PDFs directory '{RAW_PDFS_DIR}' does not exist.")
    else:
        process_pipeline(RAW_PDFS_DIR)
