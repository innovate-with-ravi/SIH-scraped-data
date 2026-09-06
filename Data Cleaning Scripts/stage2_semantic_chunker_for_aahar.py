import hashlib

def generate_sha256(content: str) -> str:
    """Generates a SHA-256 hash for the given text content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def process_ayurveda_aahara(md_content: str, filename: str, global_metadata: dict) -> tuple[str, list]:
    """
    Custom 1 Table = 1 Chunk parser.
    Bypasses LangChain to manually extract Markdown tables and their headers.
    """
    lines = md_content.split('\n')
    chunks_data = []
    
    current_category = ""
    current_table_lines = []
    in_table = False
    chunk_index = 0
    
    for line in lines:
        stripped_line = line.strip()
        
        # 1. Track the parent category (e.g., "## Dadhi/Takra")
        if stripped_line.startswith("## "):
            current_category = stripped_line.replace("## ", "").strip()
            continue
            
        # 2. Detect table boundaries (it's a table line)
        if stripped_line.startswith("|"):
            in_table = True
            current_table_lines.append(line) # Keep original line to preserve formatting
        else: # not a table line
            # 3. If we were in a table and hit a non-table line, the table is finished
            # append the table get out of it in_table = False
            if in_table:
                table_content = "\n".join(current_table_lines).strip()
                
                if table_content:
                    # Extract the exact Recipe Name from the first row of the table
                    recipe_name = "Unknown Recipe"
                    first_row_parts = current_table_lines[0].split('|')
                    if len(first_row_parts) > 2:
                        recipe_name = first_row_parts[2].strip()
                        
                    chunk_id = f"{filename}_{chunk_index}"
                    
                    structural_headers = {}
                    if current_category:
                        structural_headers["Category"] = current_category
                    structural_headers["Recipe_Name"] = recipe_name
                    
                    # Construct the JSON payload
                    chunk_json = {
                        "content": table_content,
                        "metadata": {
                            "structural_headers": structural_headers,
                            "global_metadata": global_metadata,
                            "technical_tags": {
                                "source_file": filename,
                                "chunk_index": chunk_index,
                                "chunk_id": chunk_id,
                                "content_sha256": generate_sha256(table_content)
                            }
                        }
                    }
                    chunks_data.append(chunk_json)
                    chunk_index += 1
                    
                # Reset tracking variables for the next table
                current_table_lines = []
                in_table = False
                
    # 4. Catch the final table if the document ends exactly on a table row
    if in_table and current_table_lines:
        table_content = "\n".join(current_table_lines).strip()
        if table_content:
            recipe_name = "Unknown Recipe"
            first_row_parts = current_table_lines[0].split('|')
            if len(first_row_parts) > 2:
                recipe_name = first_row_parts[2].strip()
                
            chunk_json = {
                "content": table_content,
                "metadata": {
                    "structural_headers": {
                        "Category": current_category,
                        "Recipe_Name": recipe_name
                    },
                    "global_metadata": global_metadata,
                    "technical_tags": {
                        "source_file": filename,
                        "chunk_index": chunk_index,
                        "chunk_id": f"{filename}_{chunk_index}",
                        "content_sha256": generate_sha256(table_content)
                    }
                }
            }
            chunks_data.append(chunk_json)
            
    return md_content, chunks_data