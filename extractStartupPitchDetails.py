import json
import os
import re
import time
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from llama_cloud import LlamaCloud

API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

INPUT_DIR = "input"
OUTPUT_DIR = "output"

PARSE_TIER = "agentic"
EXTRACT_TIER = "agentic"
TIMEOUT_SECONDS = 600
POLL_INTERVAL = 2.0
TARGET_PAGES = os.environ.get("LLAMA_TARGET_PAGES")
CITE_SOURCES = os.environ.get("LLAMA_CITE_SOURCES", "false").lower() == "true"


class Competitor(BaseModel):
    name: str = Field(description="Competitor or alternative solution name")
    offering: Optional[str] = Field(default=None, description="What the competitor offers")
    size_or_reach: Optional[str] = Field(default=None, description="Scale, user base, or market reach if stated")
    gap: Optional[str] = Field(default=None, description="Gap or limitation relative to the team solution")


class MarketSizing(BaseModel):
    tam: Optional[str] = Field(default=None, description="Total Addressable Market, preserving numbers and units exactly if stated")
    sam: Optional[str] = Field(default=None, description="Serviceable Addressable Market, preserving numbers and units exactly if stated")
    som: Optional[str] = Field(default=None, description="Serviceable Obtainable Market, preserving numbers and units exactly if stated")
    target_customers: List[str] = Field(default_factory=list, description="Customer segments or target users")
    why_now: List[str] = Field(default_factory=list, description="Reasons the opportunity is timely")
    market_notes: List[str] = Field(default_factory=list, description="Other market or go-to-market details")


class Financials(BaseModel):
    revenue_model: List[str] = Field(default_factory=list, description="Revenue streams or monetization methods")
    pricing_model: Optional[str] = Field(default=None, description="Pricing approach if explicitly stated")
    cost_structure: List[str] = Field(default_factory=list, description="Main costs or cost drivers")
    profitability_notes: List[str] = Field(default_factory=list, description="Why the solution could be profitable or scalable")
    funding_needs: Optional[str] = Field(default=None, description="Funding ask or investment need, if present")
    financial_model_link_present: Optional[bool] = Field(default=None, description="Whether a financial model link is referenced")


class RoadmapItem(BaseModel):
    phase_or_stage: Optional[str] = Field(default=None, description="Phase, stage, timeline marker, or milestone group")
    title: str = Field(description="Roadmap item or milestone title")
    description: Optional[str] = Field(default=None, description="Short description of this roadmap item")


class PitchDeckExtraction(BaseModel):
    startup_name: Optional[str] = Field(default=None, description="Startup, team, or venture name")
    product_name: Optional[str] = Field(default=None, description="Product or app name")
    tagline: Optional[str] = Field(default=None, description="One-line description or tagline")
    pitch_summary: Optional[str] = Field(default=None, description="Concise overall summary of the pitch in 2 to 4 sentences")

    problem_statement: Optional[str] = Field(default=None, description="Primary problem statement the startup is solving")
    core_problem: Optional[str] = Field(default=None, description="Condensed version of the core problem")
    affected_users: List[str] = Field(default_factory=list, description="People affected by the problem")
    pain_points: List[str] = Field(default_factory=list, description="Specific user pain points, struggles, or frictions")
    impact_points: List[str] = Field(default_factory=list, description="Consequences or impacts of the problem")
    problem_frequency: List[str] = Field(default_factory=list, description="How often or in what situations the problem occurs")

    customer_discovery_summary: Optional[str] = Field(default=None, description="Summary of surveys, interviews, fieldwork, or validation activities")
    key_learnings: List[str] = Field(default_factory=list, description="Insights learned from users or customer discovery")
    changes_made: List[str] = Field(default_factory=list, description="Changes or pivots made after feedback")

    solution_summary: Optional[str] = Field(default=None, description="High-level description of the solution")
    solution_approach: List[str] = Field(default_factory=list, description="Approach, delivery model, or implementation strategy")
    features: List[str] = Field(default_factory=list, description="Named features, modules, or capabilities")
    differentiators: List[str] = Field(default_factory=list, description="Why this solution is different or stronger")

    competitors: List[Competitor] = Field(default_factory=list, description="Competitors, substitutes, or alternatives")
    competition_gaps: List[str] = Field(default_factory=list, description="Gaps in current solutions or unmet needs")

    market: Optional[MarketSizing] = Field(default=None, description="Market sizing and target market details")
    business_model: List[str] = Field(default_factory=list, description="Business model, pricing, channels, partnerships, or GTM")
    financials: Optional[Financials] = Field(default=None, description="Financial plan or business plan details")
    roadmap: List[RoadmapItem] = Field(default_factory=list, description="Roadmap, implementation plan, milestones, or product evolution")

    links_or_assets: List[str] = Field(
        default_factory=list,
        description="All product, demo, prototype, GitHub, landing page, drive, website, or asset URLs mentioned in the pitch deck"
    )
    reference_links: List[str] = Field(
        default_factory=list,
        description="All research, citation, bibliography, and reference URLs mentioned anywhere in the pitch deck, especially on references or research slides"
    )

    demo_links_present: Optional[bool] = Field(default=None, description="Whether demo or prototype links are present")
    github_link_present: Optional[bool] = Field(default=None, description="Whether a GitHub link is present")

    extraction_notes: List[str] = Field(
        default_factory=list,
        description="Notes on ambiguity, visually hard-to-read content, missing sections, or URLs that may not have been fully captured"
    )


def wait_for_extract_completion(client: LlamaCloud, job_id: str, timeout_seconds: float, poll_interval: float):
    start = time.monotonic()
    job = client.extract.get(job_id)
    while job.status not in ("COMPLETED", "FAILED", "CANCELLED"):
        elapsed = time.monotonic() - start
        if elapsed > timeout_seconds:
            raise TimeoutError(
                f"Extraction job {job_id} did not complete within {timeout_seconds} seconds. Last status: {job.status}"
            )
        time.sleep(poll_interval)
        job = client.extract.get(job_id)
        print(f"Extract status: {job.status}")
    return job


def build_configuration() -> dict:
    config = {
        "data_schema": PitchDeckExtraction.model_json_schema(),
        "extraction_target": "per_doc",
        "tier": EXTRACT_TIER,
        "system_prompt": (
            "Extract startup pitch deck information into structured JSON. "
            "Capture all business information accurately. "
            "Also capture URLs. "
            "Put demo, prototype, product, GitHub, drive, landing page, and asset links into links_or_assets. "
            "Put research, bibliography, citation, and references-slide URLs into reference_links."
        ),
    }
    if TARGET_PAGES:
        config["target_pages"] = TARGET_PAGES
    if CITE_SOURCES:
        config["cite_sources"] = True
    return config


PREFERRED_ORDER = [
    "startup_name",
    "product_name",
    "tagline",
    "pitch_summary",
    "problem_statement",
    "core_problem",
    "affected_users",
    "pain_points",
    "impact_points",
    "problem_frequency",
    "customer_discovery_summary",
    "key_learnings",
    "changes_made",
    "solution_summary",
    "solution_approach",
    "features",
    "differentiators",
    "competitors",
    "competition_gaps",
    "market",
    "business_model",
    "financials",
    "roadmap",
    "links_or_assets",
    "reference_links",
    "demo_links_present",
    "github_link_present",
    "extraction_notes",
]


def reorder_dict(data: dict, preferred_order: list[str]) -> dict:
    ordered = {}
    for key in preferred_order:
        if key in data:
            ordered[key] = data[key]
    for key, value in data.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def normalize_url(url: str) -> str:
    url = url.strip()
    url = url.strip("[]()<>\"'")
    url = url.rstrip('.,);]}"\'')
    url = re.sub(r"\s+", "", url)
    return url


def extract_urls_from_text(text: str) -> List[str]:
    urls = []

    markdown_urls = re.findall(r'\((https?://[^\s)]+)\)', text, flags=re.IGNORECASE)
    urls.extend(markdown_urls)

    plain_urls = re.findall(r'https?://[^\s<>"\')\]]+', text, flags=re.IGNORECASE)
    urls.extend(plain_urls)

    cleaned = []
    seen = set()

    for u in urls:
        u = normalize_url(u)

        if not u.startswith("http"):
            continue
        if "](" in u or "[" in u or "]" in u:
            continue

        if u not in seen:
            seen.add(u)
            cleaned.append(u)

    return cleaned


def classify_urls(urls: List[str]):
    asset_urls = []
    reference_urls = []

    asset_keywords = [
        "drive.google.com",
        "github.com",
        "figma.com",
        "youtube.com",
        "youtu.be",
        "canva.com",
        "demo",
        "prototype",
        "landing",
        "app.",
        "play.google.com",
    ]

    for url in urls:
        lower = url.lower()

        if any(k in lower for k in asset_keywords):
            asset_urls.append(url)
        else:
            reference_urls.append(url)

    asset_urls = list(dict.fromkeys(asset_urls))
    reference_urls = list(dict.fromkeys(reference_urls))

    return asset_urls, reference_urls


def merge_unique(existing: List[str], discovered: List[str]) -> List[str]:
    merged = []
    seen = set()

    for item in (existing or []) + (discovered or []):
        if item and item not in seen:
            seen.add(item)
            merged.append(item)

    return merged


def dedupe_urls(urls: List[str]) -> List[str]:
    cleaned = []
    seen = set()

    for url in urls:
        base = url.split(')')[0].strip()
        if base not in seen:
            seen.add(base)
            cleaned.append(base)

    return cleaned


def process_single_pdf(client: LlamaCloud, pdf_path: Path, output_json: Path) -> None:
    print(f"\nProcessing: {pdf_path.name}")

    print(f"Uploading file: {pdf_path}")
    file_obj = client.files.create(file=str(pdf_path), purpose="extract")
    print(f"Uploaded file id: {file_obj.id}")

    print("Starting parse job...")
    parse_job = client.parsing.create(
        file_id=file_obj.id,
        tier=PARSE_TIER,
        version="latest",
    )
    parse_result = client.parsing.wait_for_completion(
        parse_job.id,
        verbose=True,
        timeout=TIMEOUT_SECONDS
    )
    print(f"Parse completed with status: {parse_result.status}")

    parsed_detail = client.parsing.get(parse_job.id, expand=["markdown"])
    markdown_text = ""

    try:
        if hasattr(parsed_detail, "markdown") and parsed_detail.markdown and hasattr(parsed_detail.markdown, "pages"):
            for page in parsed_detail.markdown.pages:
                markdown_text += "\n" + (page.markdown or "")
    except Exception:
        pass

    all_urls = extract_urls_from_text(markdown_text)
    fallback_asset_urls, fallback_reference_urls = classify_urls(all_urls)

    config = build_configuration()
    print("Creating extract job...")
    extract_job = client.extract.create(
        file_input=parse_job.id,
        configuration=config,
    )
    print(f"Extract job id: {extract_job.id}")

    final_job = wait_for_extract_completion(
        client,
        extract_job.id,
        TIMEOUT_SECONDS,
        POLL_INTERVAL
    )

    if final_job.status != "COMPLETED":
        raise RuntimeError(
            f"Extraction job ended with status {final_job.status}: {getattr(final_job, 'error_message', None)}"
        )

    result = final_job.extract_result

    result["links_or_assets"] = merge_unique(
        result.get("links_or_assets", []),
        fallback_asset_urls
    )
    result["links_or_assets"] = dedupe_urls(result.get("links_or_assets", []))

    result["reference_links"] = merge_unique(
        result.get("reference_links", []),
        fallback_reference_urls
    )

    result = reorder_dict(result, PREFERRED_ORDER)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Saved extraction JSON to {output_json}")


def main() -> None:
    if not API_KEY:
        raise EnvironmentError("Set LLAMA_CLOUD_API_KEY before running this script.")

    input_dir = Path(INPUT_DIR)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input folder not found: {input_dir}")

    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in: {input_dir}")

    client = LlamaCloud(api_key=API_KEY)

    success_count = 0
    failed_files = []

    for pdf_path in pdf_files:
        output_json = output_dir / f"{pdf_path.stem}.json"

        try:
            process_single_pdf(client, pdf_path, output_json)
            success_count += 1
        except Exception as e:
            print(f"Error processing {pdf_path.name}: {e}")
            failed_files.append({"file": pdf_path.name, "error": str(e)})

    summary = {
        "total_files": len(pdf_files),
        "success_count": success_count,
        "failed_count": len(failed_files),
        "failed_files": failed_files,
    }

    with open(output_dir / "run_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\nRun complete.")
    print(f"Total files: {len(pdf_files)}")
    print(f"Success: {success_count}")
    print(f"Failed: {len(failed_files)}")
    print(f"Summary saved to: {output_dir / 'run_summary.json'}")


if __name__ == "__main__":
    main()
