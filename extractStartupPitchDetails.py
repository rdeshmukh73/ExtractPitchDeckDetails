import json
import os
import time
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from llama_cloud import LlamaCloud
import os


API_KEY = os.getenv("API_KEY")
PDF_PATH = "Pitch Deck PDF Path"
OUTPUT_JSON = "output/pitch_deck_extraction.json" #OR any folder of your choice
PARSE_TIER =  "agentic"
EXTRACT_TIER =  "agentic"
TIMEOUT_SECONDS = 600
POLL_INTERVAL = 2.0
TARGET_PAGES = os.environ.get("LLAMA_TARGET_PAGES") #If you want to restrict reading only a few pages
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

    links_or_assets: List[str] = Field(default_factory=list, description="Mentioned assets such as GitHub repo, landing page, demo, or prototype")
    demo_links_present: Optional[bool] = Field(default=None, description="Whether demo or prototype links are present")
    github_link_present: Optional[bool] = Field(default=None, description="Whether a GitHub link is present")

    extraction_notes: List[str] = Field(default_factory=list, description="Notes on ambiguity, visually hard-to-read content, or missing sections")

def wait_for_extract_completion(client: LlamaCloud, job_id: str, timeout_seconds: float, poll_interval: float):
    start = time.monotonic()
    job = client.extract.get(job_id)
    while job.status not in ("COMPLETED", "FAILED", "CANCELLED"):
        elapsed = time.monotonic() - start
        if elapsed > timeout_seconds:
            raise TimeoutError(f"Extraction job {job_id} did not complete within {timeout_seconds} seconds. Last status: {job.status}")
        time.sleep(poll_interval)
        job = client.extract.get(job_id)
        print(f"Extract status: {job.status}")
    return job

def build_configuration() -> dict:
    config = {
        "data_schema": PitchDeckExtraction.model_json_schema(),
        "extraction_target": "per_doc",
        "tier": EXTRACT_TIER,
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

def main() -> None:
    if not API_KEY:
        raise EnvironmentError("Set LLAMA_CLOUD_API_KEY before running this script.")

    pdf_path = Path(PDF_PATH)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    Path(OUTPUT_JSON).parent.mkdir(parents=True, exist_ok=True)

    client = LlamaCloud(api_key=API_KEY)

    print(f"Uploading file: {pdf_path}")
    file_obj = client.files.create(file=str(pdf_path), purpose="extract")
    print(f"Uploaded file id: {file_obj.id}")

    print("Starting parse job...")
    parse_job = client.parsing.create(
        file_id=file_obj.id,
        tier=PARSE_TIER,
        version="latest",
    )
    parse_result = client.parsing.wait_for_completion(parse_job.id, verbose=True, timeout=TIMEOUT_SECONDS)
    print(f"Parse completed with status: {parse_result.status}")

    config = build_configuration()
    print("Creating extract job...")
    extract_job = client.extract.create(
        file_input=parse_job.id,
        configuration=config,
    )
    print(f"Extract job id: {extract_job.id}")

    final_job = wait_for_extract_completion(client, extract_job.id, TIMEOUT_SECONDS, POLL_INTERVAL)

    if final_job.status != "COMPLETED":
        raise RuntimeError(f"Extraction job ended with status {final_job.status}: {getattr(final_job, 'error_message', None)}")

    result = final_job.extract_result
    result1 = reorder_dict(result, PREFERRED_ORDER)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result1, f, indent=2, ensure_ascii=False)

    print(f"Saved extraction JSON to {OUTPUT_JSON}")

    if CITE_SOURCES:
        try:
            detailed_job = client.extract.get(final_job.id, expand=["extract_metadata", "metadata"])
            metadata_path = str(Path(OUTPUT_JSON).with_name(Path(OUTPUT_JSON).stem + "_metadata.json"))
            extra = {
                "status": detailed_job.status,
                "extract_metadata": getattr(detailed_job, "extract_metadata", None),
                "metadata": getattr(detailed_job, "metadata", None),
            }
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(extra, f, indent=2, ensure_ascii=False, default=str)
            print(f"Saved metadata JSON to {metadata_path}")
        except Exception as e:
            print(f"Warning: Could not fetch expanded metadata: {e}")


if __name__ == "__main__":
    main()