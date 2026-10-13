"""
Uses 
(i) pymupdf4llm to extract the raw markdown
(ii) gemini-2.5-flash to format the md document
"""

from raw_md_assembler import assemble_raw_markdown
from consecutive_headings_merger import merge_consecutive_headings
from stage1_extractor import extract_with_crop
import os
# import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
# import pymupdf4llm

# Load environment variables from .env file located in the root project directory
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

# Initialize the Gemini client
client = genai.Client()

SYSTEM_INSTRUCTION = """You are an expert legal data extractor and formatter. I am providing you with the raw Markdown text extracted from an Indian legal document. 
Your job is to REFORMAT this text into a perfectly structured Markdown hierarchy.

Follow these strict rules:
1. PRESERVE all Markdown tables exactly as they are. The raw text already has perfectly formatted tables; do not break them.
2. REFORMAT all headings into this strict hierarchy:
   - Use `#` for Acts / Main Titles
   - Use `##` for Chapters / Parts
   - Use `###` for Sections / Articles
3. MERGE MULTIPLE HEADINGS that belong together. If a 'title is broken across multiple lines' or 'multiple headings are close to each other', you MUST merge them into a single correct heading line.
   Example:
   [Raw Input]:
   # MINISTRY OF COMMERCE AND INDUSTRY
   (Department for Promotion of Industry and Internal Trade)
   
   # NOTIFICATION
   [Your Output]:
   # MINISTRY OF COMMERCE AND INDUSTRY (Department for Promotion of Industry and Internal Trade) NOTIFICATION
4. Ignore and completely remove any Hindi/Devanagari text. Output ONLY the English text.
5. Remove any existing improper markdown headings from the raw text and replace them with the correct semantic headings.
6. If the ENTIRE provided text cuts off abruptly in the middle of a table at the very end, you MUST properly close the markdown table structure. Do not close tables prematurely if they just cross a page break within the text.
7. If the ENTIRE provided text begins with raw table data that is missing headers at the very start, you MUST format it as a valid standalone markdown table. If 'CRITICAL CONTEXT' provides previous table headers, use them exactly. Otherwise, provide generic placeholder headers (e.g., `| Col 1 | Col 2 |`). Do not insert dummy headers for tables that continue naturally within the middle of the text.
8. Do not include any conversational filler; output only the Markdown text.
"""
def get_last_table_headers(md_text: str):
    """Finds the last markdown table in a batch and returns its header lines."""
    lines = md_text.strip().split('\n')
    table_lines = []
    
    # Extract the last contiguous block of table lines
    for line in reversed(lines):
        if line.strip().startswith('|') and line.strip().endswith('|'):
            table_lines.insert(0, line)
        elif table_lines:
            break
            
    if len(table_lines) >= 2:
        return table_lines[0] + '\n' + table_lines[1]
    return None

class RateLimitException(Exception):
    pass

@retry(
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type(RateLimitException),
    before_sleep=lambda retry_state: print(f"[Rate Limit] Retrying in {retry_state.next_action.sleep} seconds...")
)
def _call_gemini_with_retry(raw_md_text: str, previous_table_headers: str = None) -> str:
    print("  Sending raw markdown to Gemini for restructuring (Streaming)...")
    
    prompt = "Reformat this document into perfectly structured Markdown according to your system instructions."
    if previous_table_headers:
        prompt += f"\n\nCRITICAL CONTEXT: If the text begins with raw table data missing its headers, use these exact headers from the previous page to complete it:\n{previous_table_headers}"
        print(f"[_call_gemini_with_retry]: attached\n{previous_table_headers}")
        
    try:
        response = client.models.generate_content_stream(
            model="gemini-1.5-flash",
            contents=[raw_md_text, prompt],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.1
            )
        )
        
        md_text = ""
        for chunk in response:
            if chunk.text:
                print(chunk.text, end="", flush=True) # avoid streaming for now to easily debug
                md_text += chunk.text
        print("\n")  # Newline after streaming finishes
        return md_text
    except Exception as e:
        # Catch all rate limits, server errors, and network disconnects to trigger tenacity retry
        error_msg = str(e).lower()
        if "400" in error_msg and "invalid" in error_msg:
            # Fatal error (bad request), don't retry
            raise e
        # For all other errors (429, 503, socket disconnects, timeouts, etc), trigger a retry
        raise RateLimitException(f"Network or server error: {e}")

import json

def extract_hybrid(pdf_path: str, output_md_path: str):
    """
    Extracts structured markdown from a PDF using a Hybrid Approach with Batching:
    1. Extract raw Markdown using pymupdf4llm locally (page by page) and cache it.
    2. Pass raw Markdown batches to Gemini API to restructure and cache each batch.
    3. Concatenate all batches into the final markdown file.
    """
    pdf_name = Path(pdf_path).name
    pdf_stem = Path(pdf_path).stem
    processing_dir = Path(output_md_path).parent
    
    print(f"Processing Hybrid Extraction for: {pdf_name}...")
    
    try:
        # Step 1: Extract/Load Raw Markdown Pages
        raw_json_path = processing_dir / f"{pdf_stem}_raw_pages.json"
        
        if raw_json_path.exists(): # load
            print(f"  Loading cached raw pages from {raw_json_path.name}...")
            with open(raw_json_path, "r", encoding="utf-8") as f:
                page_chunks = json.load(f)
        else: # extract
            print("  Extracting raw markdown locally with extract_with_crop(pymupdf4llm)...")
            page_chunks = extract_with_crop(pdf_path)
            # Cache it
            with open(raw_json_path, "w", encoding="utf-8") as f:
                json.dump(page_chunks, f, ensure_ascii=False, indent=2)
                
        if not page_chunks:
            raise ValueError(f"No text could be extracted from {pdf_name}")
        
        # ---------------------------------------------------------------- #
        # new extract_with_crop & assembling raw_md comment after testing
        print(f"saved raw_json pages at :{raw_json_path}")

        # use assemble_raw_markdown to assemble _raw_json_pages
        assemble_raw_markdown(json_path=raw_json_path, output_md_path=output_md_path)
        print(f"assembled raw_json pages at :{output_md_path},\nreturning")
        return
        # ---------------------------------------------------------------- #

        # Step 2: Batching
        
        BATCH_SIZE = 30
        total_pages = len(page_chunks)
        final_md_text = ""
        previous_headers = None
        
        for i in range(0, total_pages, BATCH_SIZE):
            batch_num = (i // BATCH_SIZE) + 1
            batch_pages = page_chunks[i:i + BATCH_SIZE]
            
            # Combine raw markdown for this batch
            # if batch_md_path exists we don't need batch_raw_md
            batch_raw_md = "\n\n".join([page.get("text", "") for page in batch_pages])
            
            batch_md_path = processing_dir / f"{pdf_stem}_formatted_batch_{batch_num}.md"
            
            # load or extract batch_formatted_md
            # we need batch_formatted_md in both cases so that we can Extract table headers for the NEXT batch
            if batch_md_path.exists(): # load
                print(f"  [Batch {batch_num}] Loading cached formatted batch...")
                with open(batch_md_path, "r", encoding="utf-8") as f:
                    batch_formatted_md = f.read()
            else: # extract
                print(f"  [Batch {batch_num}] Sending pages {i+1} to {min(i+BATCH_SIZE, total_pages)} to Gemini...")

                # Merge scattered headings in the raw text BEFORE sending to Gemini
                batch_raw_md = merge_consecutive_headings(batch_raw_md)
                batch_formatted_md = _call_gemini_with_retry(batch_raw_md, previous_headers)
                
                # Strip code blocks
                if batch_formatted_md.startswith("```markdown\n"):
                    batch_formatted_md = batch_formatted_md[12:]
                elif batch_formatted_md.startswith("```markdown"):
                    batch_formatted_md = batch_formatted_md[11:]
                    
                if batch_formatted_md.endswith("```\n"):
                    batch_formatted_md = batch_formatted_md[:-4]
                elif batch_formatted_md.endswith("```"):
                    batch_formatted_md = batch_formatted_md[:-3]
                    
                batch_formatted_md = batch_formatted_md.strip()
                
                # Cache the formatted batch
                with open(batch_md_path, "w", encoding="utf-8") as f:
                    f.write(batch_formatted_md)
                    
            # Extract table headers for the NEXT batch
            previous_headers = get_last_table_headers(batch_formatted_md)
            
            # Append to final
            final_md_text += f"\n\n{batch_formatted_md}"
            
        # Save the final stitched output
        final_md_text = final_md_text.strip()
        with open(output_md_path, "w", encoding="utf-8") as file:
            file.write(final_md_text)
            
        print(f"Success! Hybrid Extracted Markdown saved to: {output_md_path}")
        
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        raise e

if __name__ == "__main__":
    # Test on the problematic file
    test_pdf = r"d:\CODING\Hackathons\SIH\SIH-scraped-data\raw_data\raw_pdfs\01-IP_Laws\1_69_1_Trade_Marks_Rules_2017 (1)-53-97.pdf"
    test_md = test_pdf.replace(".pdf", ".md")
    
    if os.path.exists(test_pdf):
        extract_hybrid(test_pdf, test_md)
    else:
        print(f"Test PDF not found: {test_pdf}")
