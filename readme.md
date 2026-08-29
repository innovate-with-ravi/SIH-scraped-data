# Contributing to the SIH Data Lake (`SIH-scraped-data`)

Welcome to the data repository for our Smart India Hackathon project. This repository serves as our centralized **Data Lake**, storing all raw and structured legal datasets, acts, guidelines, and reference documents required to power our Retrieval-Augmented Generation (RAG) assistant.

---

## 1. Purpose & How This Fits into the AI Pipeline

Our AI assistant relies on exact, hallucination-free legal guidance. To achieve this:
* **The Vector Database:** Reads every JSON file from this repository, converts the text into vector embeddings, and stores them alongside metadata.
* **Retrieval & Citations:** When a user asks a query, our backend searches for matching sections and uses the metadata (`url_source`, `section_number`) to return official, verifiable citations.
* **LLM Context:** The AI reads the structured text stored in the `content` field to generate human-readable explanations.

---

## 2. Repository Structure

```text
SIH-scraped-data/
├── cleaned_data/                  # Processed, machine-readable JSON data
│   ├── indiacode/                 # Statutes & Acts from indiacode.nic.in
│   │   ├── biological_diversity_act_2002/
│   │   │   └── chapter_1.json
│   │   └── patents_act_1970/
│   │       ├── chapter_1.json
│   │       └── chapter_2.json
│   ├── ipindia/                   # Rules & IP registry data from ipindia.gov.in
│   │   └── patents_rules_2024/
│   │       └── part_1.json
│   ├── nbaindia/                  # ABS guidelines from nbaindia.org
│   │   └── abs_guidelines/
│   └── tkdl/                      # Prior art & reference data from tkdl.res.in
│       └── prior_art_examples/
├── raw_data/                      # Unmodified source files for debugging
│   ├── raw_html/                  # Raw HTML page dumps
│   └── raw_pdfs/                  # Official PDF downloads
└── sample.json                    # Template schema for contributors
```

---

## 3. Data Schema & Formatting Rules

Every processed file in `cleaned_data/` must follow the JSON schema below. 

### Standard Schema (`sample.json`)

```json
{
  "jurisdiction": "India",
  "document_title": "The Patents Act, 1970",
  "section_number": "Section 3",
  "url_source": "https://indiacode.nic.in/show-data?actid=AC_CEN_11_60_00005_197039_1517807323983&sectionId=15306",
  "content": "### Section 3: What are not inventions\n\nThe following are not inventions within the meaning of this Act:\n\n* **(p)** an invention which in effect, is traditional knowledge or which is an aggregation or duplication of known properties of traditionally known component or components."
}
```

### Field Definitions

| Field | Type | Description | Purpose in RAG Pipeline |
| :--- | :--- | :--- | :--- |
| `jurisdiction` | `string` | Target jurisdiction (e.g., `"India"`, `"International"`). | Enables the Jurisdiction Toggle filter in the database. |
| `document_title` | `string` | Official name of the Act, Rulebook, or Treaty. | Displayed in citations and used for high-level routing. |
| `section_number` | `string` | Specific section, chapter, or clause identifier. | Allows granular retrieval and exact citation anchoring. |
| `url_source` | `string` | Direct URL to the official source text. | Generates clickable verification links in the UI. |
| `content` | `string` | The extracted legal text formatted as **Markdown**. | Fed directly to the LLM as grounding context. |

---

## 4. Crucial Formatting Rules for `content`

1. **Always Use Markdown Strings:** Legal documents contain hierarchical information (sub-clauses, lists, conditions). Use Markdown headers (`###`), lists (`*` or `-`), and bold text (`**term**`) inside the string. This structure significantly improves LLM comprehension and retrieval quality.
2. **Preserve Section Identifiers:** Always include the clause or subsection identifiers (e.g., `(a)`, `(b)`, `(p)`) exactly as they appear in the source.
3. **Clean Unwanted Artifacts:** Remove website headers, navigation menus, ads, broken Unicode characters, and duplicate page numbers during extraction.

> **Note on Extensibility:** The JSON schema is modular. As our pipeline grows, we may add optional metadata keys (e.g., `"act_year"`, `"category"`, `"tags"`, `"amendment_year"`) without breaking existing ingestion scripts.

---

## 5. Contribution Workflow

To maintain clean data and prevent merge conflicts:

1. **Assigned Portals:** Each team member can be assigned a specific website/portal (e.g., IndiaCode, IP India, NBA).
2. **Save Raw Dumps:** If writing automated scrapers, save the original HTML/PDF files in `raw_data/` for auditing and scraper debugging.
3. **Generate Clean JSON:** Write clean, structured JSON files into the appropriate folder under `cleaned_data/`.
4. **Create a Pull Request:** Work on your dedicated feature branch (e.g., `data/indiacode-patents`) and submit a PR against `main` for merging.