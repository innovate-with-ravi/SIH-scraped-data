import pymupdf  # PyMuPDF
import pymupdf.layout  # <-- CRITICAL: Forces initialization of the advanced layout module
import pymupdf4llm
import os

def extract_with_crop(pdf_path, output_md_path=None):
    print(f"Processing: {pdf_path}...")
    
    try:
        # 1. Open the document with standard PyMuPDF
        doc = pymupdf.open(pdf_path)
        
        # 2. Extract cleanly chunked pages using the layout engine
        # We drop the manual bounding-box crop entirely and let the layout model
        # cleanly strip repeating headers, running margins, and footers.
        page_chunks = pymupdf4llm.to_markdown(
            doc, 
            page_chunks=True, 
            header=False,     # Filters out running headers ("Nagoya Protocol...")
            footer=False,     # Filters out structural page numbers ("2", "3")
            # edge_threshold=0.75  # Sharpens column/gutter separation boundaries
            # you should only use a high edge_threshold if you are actively resolving double-sided layouts or dense columns.
        )
        
        # 3. Return the raw page chunks list for the batching pipeline
        return page_chunks
        
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return []

if __name__ == "__main__":
    from pathlib import Path
    
    # Target path adjusted to your structural layout environment
    pdf_dir = Path(r"d:\CODING\Hackathons\SIH\SIH-scraped-data\raw_data\raw_pdfs")
    
    if not pdf_dir.exists():
        print(f"Directory not found: {pdf_dir}")
    else:
        for pdf_path in pdf_dir.rglob("*.pdf"):
            output_md_path = pdf_path.with_suffix(".md")
            
            # Run layout extraction
            chunks = extract_with_crop(str(pdf_path), str(output_md_path))
            
            # Optional check to verify successful run on individual file loops
            if chunks:
                print(f"Successfully processed {len(chunks)} pages from {pdf_path.name}")
