
# Student Pitch Deck Extraction (Llama Cloud v2)

This script extracts structured fields from student startup pitch decks (PDFs) using the latest **Llama Cloud** Python SDK and LlamaExtract v2.  
It is tuned for decks that mix text and images (including LLM‑generated visuals) and **reorders** the output JSON so identity and problem fields appear at the top.

---

## What this script does

- Uploads a pitch deck PDF to Llama Cloud. 
- Runs a Parse API v2 job on the file.
- Runs a LlamaExtract v2 job with a custom JSON schema (`PitchDeckExtraction`) using the `per_doc` extraction target (one document → one startup). 
- Reorders the returned JSON so these fields appear first:
  - `startup_name`
  - `product_name`
  - `tagline`
  - `pitch_summary`
  - `problem_statement`
  - `core_problem`
  - `affected_users`
- Saves the final, ordered JSON to disk.

The schema is designed for student pitch decks like your AI health companion example and works well even when slides contain screenshots or LLM‑generated images with text baked in. 

---

## Extracted fields

The `PitchDeckExtraction` Pydantic model captures (high‑level):

- **Identity and summary**
  - `startup_name`, `product_name`, `tagline`, `pitch_summary`
- **Problem space**
  - `problem_statement`, `core_problem`, `affected_users`, `pain_points`, `impact_points`, `problem_frequency`
- **Customer discovery**
  - `customer_discovery_summary`, `key_learnings`, `changes_made`
- **Solution**
  - `solution_summary`, `solution_approach`, `features`, `differentiators`
- **Competition and market**
  - `competitors`, `competition_gaps`, `market` (with `tam`, `sam`, `som`, `target_customers`, `why_now`, `market_notes`)
- **Business and finance**
  - `business_model`, `financials` (revenue model, pricing, cost structure, profitability notes, funding needs, financial model link flag)
- **Roadmap**
  - `roadmap` (phases, milestones, implementation plan)
- **Links and metadata**
  - `links_or_assets`, `demo_links_present`, `github_link_present`, `extraction_notes`

This maps directly to typical pitch‑deck sections: problem, solution, competition, market opportunity, revenue model, and roadmap. 

---

## Installation

Create and activate a virtual environment (recommended), then install dependencies:

```bash
pip install -U "llama-cloud>=2.1" pydantic>=2.0
```

- `llama-cloud` is the new Python SDK recommended for LlamaExtract v2 and Parse API v2, replacing the deprecated `llama-cloud-services` package. 
- `pydantic>=2.0` is used for the schema definition and validation. 

---

## Environment variables

Set your Llama Cloud API key:

```bash
export API_KEY="your_key_here"
```

Optional environment variables:

- `PITCH_DECK_PDF`  
  Path to the PDF (default: `TeamTesla.pdf`).

- `PITCH_DECK_OUTPUT`  
  Output JSON path (default: `output/pitch_deck_extraction_v2.json`).

- `LLAMA_PARSE_TIER`  
  Parse tier, e.g. `agentic` or `fast` (default: `agentic`). 

- `LLAMA_EXTRACT_TIER`  
  Extract tier, e.g. `agentic` (default: `agentic`). 

- `LLAMA_TIMEOUT_SECONDS`  
  Overall timeout for parse + extract in seconds (default: `600`).

- `LLAMA_POLL_INTERVAL`  
  Polling interval in seconds when waiting for the extract job (default: `2.0`).

- `LLAMA_TARGET_PAGES`  
  Optional page filter, e.g. `"3,6-10"` to bill and extract only selected slides. 

- `LLAMA_CITE_SOURCES`  
  Set to `true` to request citations and reasoning metadata from LlamaExtract; the script will then also save a metadata JSON file. 

---

## Running the script

### Basic usage

```bash
python extractStartupPitchDetails.py
```

This will:

1. Upload `YourTeamIdea.pdf` (or whatever `PITCH_DECK_PDF` points to).
2. Run a parse job using Parse API v2.
3. Run a LlamaExtract v2 job with your pitch‑deck schema in `per_doc` mode. 
NOTE: `per_doc` and other options are available to read here: [LlamaParseExtract](https://developers.llamaindex.ai/llamaparse/extract/guides/options/)
4. Reorder the resulting JSON so startup and problem fields appear at the top.
5. Write the ordered JSON to:

```bash
output/pitch_deck_extraction_v2.json
```

### Using a different PDF

```bash
PITCH_DECK_PDF="/absolute/path/to/your_pitch_deck.pdf" \
python extractStartupPitchDetails.py
```

### With citations and page targeting

```bash
LLAMA_CITE_SOURCES=true \
LLAMA_TARGET_PAGES="3,5-10" \
PITCH_DECK_PDF="TeamTesla.pdf" \
python pitch_deck_llamacloud_v2.py
```

If `LLAMA_CITE_SOURCES=true`, the script will also fetch expanded metadata (citations, reasoning, etc.) and save it alongside the main extraction. This leverages LlamaExtract’s ability to attach source spans and reasoning traces to extracted fields for auditing and grading. 

---

## JSON field ordering

By default, LlamaExtract returns a JSON object that matches your schema but does not guarantee key order. The script applies a post‑processing step to reorder keys before saving:

1. It defines a `PREFERRED_ORDER` list beginning with:

   ```text
   startup_name
   product_name
   tagline
   pitch_summary
   problem_statement
   core_problem
   affected_users
   ```

2. It builds a new dict:
   - First, it inserts any keys found in `PREFERRED_ORDER` in that sequence.
   - Then, it appends any remaining keys in their original order.

Because Python 3.7+ preserves dictionary insertion order, the final `json.dump(...)` writes the file in exactly this layout, making it much easier to visually scan each team’s JSON for evaluation. 

---

## Adapting for a whole cohort

To use this for many student teams:

1. Put all pitch‑deck PDFs in a folder, e.g. `decks/`.
2. Write a small driver script that:
   - Iterates over `decks/*.pdf`.
   - For each file, calls the same logic used here (upload → parse → extract).
   - Saves `output/{stem}_extraction_v2.json` for each team.

3. Optionally, flatten a subset of fields into a CSV for rubric‑based scoring, for example:
   - `startup_name`
   - `problem_statement`
   - `solution_summary`
   - `tam`, `sam`, `som`
   - `revenue_model`
   - `roadmap` presence/length

The `per_doc` extraction target is a good fit for this pattern because each deck typically represents one startup, not many entities per table row. 

---
```
