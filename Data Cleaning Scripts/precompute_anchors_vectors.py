import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google import genai
import json

project_root = Path(r"d:\CODING\Hackathons\SIH\SIH-scraped-data")
load_dotenv(project_root / ".env")

client = genai.Client()

POSITIVE_ANCHORS = {
    "national_ip": "Indian intellectual property laws including the Patents Act and 2024 Rules, Geographical Indications (GI), Trade Marks, Designs, Copyright, and Plant-Variety regimes. Covers registry procedures, IP infringement, opposition, and intellectual property protection.",
    "international_treaties": "International intellectual property and biodiversity treaties including TRIPS, Convention on Biological Diversity (CBD), Nagoya Protocol, WIPO Treaty on Genetic Resources and Associated Traditional Knowledge (GRATK), PCT, Madrid system, Hague system, and Budapest Treaty.",
    "ayurvedic_formulations": "Classification and regulation of Ayurvedic products, including classical and generic medicines drawn from authoritative texts (First Schedule), patent or proprietary medicines, new drugs, phytopharmaceuticals, Ayurveda-Aahar, nutraceuticals, cosmetics, and medicinal plant therapeutics.",
    "biodiversity_and_abs": "Biological Diversity Act 2002, 2023 amendments, and 2024 Rules. Covers the National Biodiversity Authority (NBA), Access and Benefit Sharing (ABS) duties, sovereign rights over biological resources, and compliance for commercializing genetic resources.",
    "drug_regulatory_and_advertising": "Regulatory compliance for manufacturing, marketing, and labelling. Covers the Drugs and Cosmetics Act, Drugs and Magic Remedies (Objectionable Advertisements) Act, FSSAI regulations, safety, clinical evidence, and efficacy requirements for AYUSH startups.",
    "traditional_knowledge_and_prior_art": "Protection of community-held traditional knowledge (TK), the Traditional Knowledge Digital Library (TKDL), prior art, Section 3(p) of the Patents Act, defense against misappropriation, and codification of traditional Indian medical knowledge.",
    "legal_procedures_and_administration": "Administrative procedures, legal rules, timelines, filing applications, registrar decisions, correction of irregularities, fees, hearing mechanisms, official notifications, powers of the registrar, registries, forms, scale of costs, and communication of decisions."
}

NEGATIVE_ANCHOR = (
    "Meaningless text, single letters, OCR artifacts, empty tables, broken sentences, blank pages, "
    "page numbers, index, table of contents, list of tables, meaningless headers without content, "
    "random numbers, formatting noise, irrelevant signatures, and disconnected words."
)

import time
print("Fetching embeddings for anchors...")

embeddings = []
texts = list(POSITIVE_ANCHORS.values()) + [NEGATIVE_ANCHOR]

for text in texts:
    result = client.models.embed_content(
        model="gemini-embedding-2",
        contents=text
    )
    embeddings.append(list(result.embeddings[0].values))
    time.sleep(0.5)

output_content = f'''# semantic_anchors.py

"""
Semantic anchors used for zero-shot relevance classification of extracted chunks.
Each anchor represents a specific persona or domain within the IP-SAKTI Sahayak project.
Chunks will be compared against these anchors using cosine similarity.

The vectors have been pre-computed using google-genai text-embedding-004 (768d)
to avoid unnecessary API calls during extraction.
"""

POSITIVE_ANCHORS = {json.dumps(POSITIVE_ANCHORS, indent=4)}

POSITIVE_ANCHOR_VECTORS = {json.dumps(embeddings[:-1])}

NEGATIVE_ANCHOR = {json.dumps(NEGATIVE_ANCHOR)}

NEGATIVE_ANCHOR_VECTOR = {json.dumps(embeddings[-1])}
'''

output_path = project_root / "Data Cleaning Scripts" / "semantic_anchors.py"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(output_content)

print(f"Successfully generated vectors and saved to {output_path.name}")
