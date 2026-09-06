import math
import time
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential

from semantic_anchors import POSITIVE_ANCHOR_VECTORS, NEGATIVE_ANCHOR_VECTOR

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two vectors using pure Python."""
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)

@retry(
    stop=stop_after_attempt(8),
    wait=wait_exponential(multiplier=2, min=10, max=65),
    before_sleep=lambda retry_state: print(f"[Rate Limit] Quota exceeded. Waiting {retry_state.next_action.sleep:.1f}s for quota window to reset...")
)
def get_embedding(client, text):
    res = client.models.embed_content(
        model="gemini-embedding-2",
        contents=text
    )
    return list(res.embeddings[0].values)

def stage3_filter(chunks_data: List[Dict], client: genai.Client, threshold: float = 0.50) -> Tuple[List[Dict], List[Dict]]:
    """
    Takes a list of JSON chunks (dictionaries), generates their embedding, 
    and compares them to pre-computed semantic anchors.
    
    Returns:
        Tuple of (relevant_chunks, discarded_chunks)
    """
    relevant_chunks = []
    discarded_chunks = []
    
    if not chunks_data:
        return relevant_chunks, discarded_chunks
        
    print(f"[Stage 3] Semantic filtering {len(chunks_data)} chunks...")
    CACHE_PATH = Path(r"d:\CODING\Hackathons\SIH\SIH-scraped-data\embeddings_cache.json")
    embeddings_cache = {}
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            try:
                embeddings_cache = json.load(f)
            except Exception:
                embeddings_cache = {}
            
    cache_updated = False
    new_embeddings_count = 0
    old_embeddings_count = 0
    
    def save_cache():
        if cache_updated:
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(embeddings_cache, f)

    try:
        for idx, chunk in enumerate(chunks_data):
            if "vector" in chunk and chunk["vector"]:
                continue
                
            content = chunk.get("content", "")
            text = content if content.strip() else " "
            
            # Calculate SHA256 of text
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            
            if text_hash in embeddings_cache:
                chunk["vector"] = embeddings_cache[text_hash]
                old_embeddings_count+=1
            else:
                vec = get_embedding(client, text)
                chunk["vector"] = vec
                embeddings_cache[text_hash] = vec
                cache_updated = True
                new_embeddings_count += 1
                
                # Save cache immediately every 5 embeddings so no progress is ever lost
                if new_embeddings_count % 5 == 0:
                    save_cache()
                    
                if new_embeddings_count % 25 == 0:
                    print(f"[Stage 3] Embedded {new_embeddings_count} new chunks...")
                    
                time.sleep(3) # Safe pacing to stay under 30k TPM
    finally:
        # Guarantee cache is saved even if interrupted by keyboard or error
        save_cache()
            
    if new_embeddings_count == 0:
        print("[Stage 3] Using pre-computed vectors from cached chunks for all items...")
    else:
        print(f"[Stage 3] Retrieved {old_embeddings_count} old chunks from `embedding_cache.json`.")
        print(f"[Stage 3] Embedded {new_embeddings_count} new chunks total.")
        
    # Compare each chunk against anchors
    for idx, chunk in enumerate(chunks_data):
        chunk_vector = chunk["vector"]

        
        # Calculate similarities
        positive_similarities = [cosine_similarity(chunk_vector, anchor_vec) for anchor_vec in POSITIVE_ANCHOR_VECTORS]
        negative_similarity = cosine_similarity(chunk_vector, NEGATIVE_ANCHOR_VECTOR)
        
        max_positive = max(positive_similarities) if positive_similarities else 0.0
        
        # Threshold comparison (we set 0.50 as an initial strict threshold, tune as necessary)
        if max_positive >= threshold and max_positive > negative_similarity:
            relevant_chunks.append(chunk)
        else:
            chunk["_debug_similarity"] = max_positive
            chunk["_debug_negative_similarity"] = negative_similarity
            discarded_chunks.append(chunk)
            
    print(f"[Stage 3] Retained {len(relevant_chunks)} chunks, discarded {len(discarded_chunks)} chunks.")
    return relevant_chunks, discarded_chunks
