from consecutive_headings_merger import merge_consecutive_headings
import hashlib
from langchain_text_splitters import MarkdownHeaderTextSplitter

def generate_sha256(content: str) -> str:
    """Generates a SHA-256 hash for the given text content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def process_stage2(md_content: str, filename: str, global_metadata: dict) -> tuple[str, list]:
    """
    Performs Stage 2: Semantic Chunking (one chunk per section) and Rich Metadata Injection.
    No llm is used, 100% python
    
    Returns:
        tuple[str, list]: The merged markdown content and a list of chunk data dictionaries.
    """
    # 1. Merge scattered headings deterministically before splitting using MarkdownHeaderTextSplitter
    md_content = merge_consecutive_headings(md_content)

    # 2. Semantic Chunking
    headers_to_split_on = [
        ("#", "Act"),
        ("##", "Chapter"),
        ("###", "Section"),
    ]

    # only for trips.pdf hierarchy
    # headers_to_split_on = [
    #     ("#", "Act"),
    #     ("##", "Part"),
    #     ("###", "Section"),
    #     ("####", "Article") 
    # ]
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )
    splits = markdown_splitter.split_text(md_content)
    
    chunks_data = []
    
    current_act, previous_act = None, None
    current_chapter, previous_chapter = None, None
    current_section, previous_section = None, None
    
    # create json for each chunk
    for chunk_index, split in enumerate(splits):
        chunk_content = split.page_content
        structural_headers = split.metadata.copy()
        
        # Track Act hierarchy
        act = structural_headers.get("Act")
        if act and act != current_act:
            previous_act = current_act
            current_act = act
            
        # Track Chapter hierarchy
        chapter = structural_headers.get("Chapter")
        if chapter and chapter != current_chapter:
            previous_chapter = current_chapter
            current_chapter = chapter
            
        # Track Section hierarchy
        section = structural_headers.get("Section")
        if section and section != current_section:
            previous_section = current_section
            current_section = section
            
        # Inject previous fallbacks
        if previous_act:
            structural_headers["previousAct"] = previous_act
        if previous_chapter:
            structural_headers["previousChapter"] = previous_chapter
        if previous_section:
            structural_headers["previousSection"] = previous_section
        
        chunk_id = f"{filename}_{chunk_index}"
        
        # Construct the rich JSON object for the chunk
        chunk_json = {
            "content": chunk_content,
            "metadata": {
                "structural_headers": structural_headers,
                "global_metadata": global_metadata,
                "technical_tags": {
                    "source_file": filename,
                    "chunk_index": chunk_index,
                    "chunk_id": chunk_id,
                    "content_sha256": generate_sha256(chunk_content)
                }
            }
        }
        chunks_data.append(chunk_json)
        
    return md_content, chunks_data
