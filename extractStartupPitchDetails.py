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
OUTPUT_DIR = "output_tweaked"

PARSE_TIER = "agentic"
EXTRACT_TIER = "agentic"
TIMEOUT_SECONDS = 600
POLL_INTERVAL = 2.0
TARGET_PAGES = os.environ.get("LLAMA_TARGET_PAGES")
CITE_SOURCES = os.environ.get("LLAMA_CITE_SOURCES", "false").lower() == "true"

# TEST MODE: set to a partial filename string to test one specific team, or None to run all
TEST_TEAM_NAME = os.environ.get("TEST_TEAM_NAME", None)


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
    revenue_milestones: List[str] = Field(
        default_factory=list,
        description=(
            "Revenue or volume projections at scale, e.g. '1M units → ₹1.7 Cr', '5M units → ₹8.5 Cr'. "
            "Also include break-even point, timeline to profitability, and total build cost if stated."
        )
    )
    key_assumptions: List[str] = Field(
        default_factory=list,
        description=(
            "Key business or market assumptions explicitly listed on financial, profit model, or revenue slides. "
            "e.g. 'Number of genetic patents will continue to grow', "
            "'Research labs prefer automated checks over consulting lawyers for every sequence'. "
            "Capture verbatim or near-verbatim as stated."
        )
    )
    funding_needs: Optional[str] = Field(default=None, description="Funding ask or investment need, if present")
    financial_model_link_present: Optional[bool] = Field(default=None, description="Whether a financial model link is referenced")


class RoadmapItem(BaseModel):
    phase_or_stage: Optional[str] = Field(default=None, description="Phase, stage, timeline marker, or milestone group")
    title: str = Field(description="Roadmap item or milestone title")
    description: Optional[str] = Field(default=None, description="Short description of this roadmap item")


class SurveyDataPoint(BaseModel):
    question: str = Field(description="The survey question or topic")
    finding: str = Field(
        description=(
            "The key statistic or finding, including the exact percentage and what it refers to. "
            "e.g. '81.1% cited improper storage conditions as a doubt factor', "
            "'48.6% suspected a drug did not work as expected', "
            "'94.6% expressed interest in improved methods'."
        )
    )


class Interviewee(BaseModel):
    name: str = Field(description="Full name of the person interviewed or consulted.")
    role: Optional[str] = Field(
        default=None,
        description="Their role, title, or area of expertise as stated in the deck. e.g. 'IPR lawyer', 'Professor in genetics', 'Biotech patent agent'."
    )


class PitchPlanQA(BaseModel):
    pitch_hook: Optional[str] = Field(
        default=None,
        description=(
            "The opening hook or narrative used to open the pitch, if explicitly written on a pitch plan or hook slide. "
            "Capture the full hook text verbatim or near-verbatim as it appears."
        )
    )
    pitch_structure: List[str] = Field(
        default_factory=list,
        description=(
            "Ordered list of pitch sections with timestamps if present. "
            "e.g. 'Hook + Problem (0:00–1:00)', 'Solution (4:00–4:30)'."
        )
    )
    anticipated_questions: List[str] = Field(
        default_factory=list,
        description="Anticipated jury or investor questions listed in the pitch deck."
    )
    prepared_answers: List[str] = Field(
        default_factory=list,
        description="Prepared answers corresponding to the anticipated questions, in the same order."
    )


class DemoPlan(BaseModel):
    segments: List[str] = Field(
        default_factory=list,
        description=(
            "Ordered list of demo or presentation segments with timestamps and slide references. "
            "e.g. '0:00–1:30: Slide 1 — Title & Hook (Ozempic scenario)', "
            "'1:30–2:30: Slide 4 — Existing Solutions'. "
            "Capture ALL segments from any demo plan, presentation flow, or pitch timeline slide."
        )
    )
    total_duration: Optional[str] = Field(
        default=None,
        description="Total presentation duration if stated, e.g. '10 minutes'."
    )


class ImplementationStats(BaseModel):
    beta_target_users: Optional[str] = Field(
        default=None,
        description="Target number of beta users stated on the implementation or roadmap slide. e.g. '120+'."
    )
    total_milestones: Optional[str] = Field(
        default=None,
        description="Total number of milestones stated. e.g. '9'."
    )
    end_goal: Optional[str] = Field(
        default=None,
        description="End goal stated on the roadmap slide. e.g. 'Global SaaS'."
    )
    phase1_budget: Optional[str] = Field(
        default=None,
        description="Phase 1 or initial budget stated. e.g. '₹13,31,466'."
    )


class PitchDeckExtraction(BaseModel):
    startup_name: Optional[str] = Field(default=None, description="Startup, team, or venture name")
    product_name: Optional[str] = Field(default=None, description="Product or app name")
    tagline: Optional[str] = Field(default=None, description="One-line description or tagline")
    pitch_summary: Optional[str] = Field(default=None, description="Concise overall summary of the pitch in 2 to 4 sentences")

    team_members: List[str] = Field(
        default_factory=list,
        description="Names of all team members as listed in the pitch deck."
    )

    problem_statement: Optional[str] = Field(default=None, description="Primary problem statement the startup is solving")
    core_problem: Optional[str] = Field(default=None, description="Condensed version of the core problem")
    affected_users: List[str] = Field(default_factory=list, description="People affected by the problem")
    pain_points: List[str] = Field(default_factory=list, description="Specific user pain points, struggles, or frictions")
    impact_points: List[str] = Field(default_factory=list, description="Consequences or impacts of the problem")
    problem_frequency: List[str] = Field(default_factory=list, description="How often or in what situations the problem occurs")

    customer_discovery_summary: Optional[str] = Field(default=None, description="Summary of surveys, interviews, fieldwork, or validation activities")

    interviewees: List[Interviewee] = Field(
        default_factory=list,
        description=(
            "All named individuals the team interviewed or consulted during customer discovery, "
            "with their name and role/expertise as stated in the deck. "
            "Look for 'Interacted with', 'Spoke to', 'Interviewed' sections. "
            "Capture every named person separately."
        )
    )

    key_learnings: List[str] = Field(default_factory=list, description="Insights learned from users or customer discovery")
    changes_made: List[str] = Field(default_factory=list, description="Changes or pivots made after feedback")

    survey_data: List[SurveyDataPoint] = Field(
        default_factory=list,
        description=(
            "All specific survey statistics from any survey or validation slide. "
            "Each entry captures one question and its key finding with the exact percentage. "
            "Include ALL data points: bar chart entries, pie chart results, multi-select question results. "
            "Do NOT aggregate or summarise — capture each stat separately."
        )
    )

    solution_summary: Optional[str] = Field(default=None, description="High-level description of the solution")
    solution_approach: List[str] = Field(default_factory=list, description="Approach, delivery model, or implementation strategy")
    features: List[str] = Field(default_factory=list, description="Named features, modules, or capabilities")
    differentiators: List[str] = Field(default_factory=list, description="Why this solution is different or stronger")

    technical_details: List[str] = Field(
        default_factory=list,
        description=(
            "Named materials, chemicals, dyes, biological components, or mechanisms explicitly mentioned. "
            "e.g. 'Sentinel protein', 'Congo Red dye', 'Thioflavin T', 'protein-dye binding mechanism'. "
            "Preserve exact names as stated in the deck."
        )
    )

    competitors: List[Competitor] = Field(default_factory=list, description="Competitors, substitutes, or alternatives")
    competition_gaps: List[str] = Field(default_factory=list, description="Gaps in current solutions or unmet needs")

    market: Optional[MarketSizing] = Field(default=None, description="Market sizing and target market details")
    business_model: List[str] = Field(default_factory=list, description="Business model, pricing, channels, partnerships, or GTM")
    financials: Optional[Financials] = Field(default=None, description="Financial plan or business plan details")
    roadmap: List[RoadmapItem] = Field(default_factory=list, description="Roadmap, implementation plan, milestones, or product evolution")

    implementation_stats: Optional[ImplementationStats] = Field(
        default=None,
        description=(
            "Summary statistics shown at the bottom or footer of the implementation/roadmap slide. "
            "Includes beta user targets, total milestones, end goal label, and phase 1 budget."
        )
    )

    pitch_plan: Optional[PitchPlanQA] = Field(
        default=None,
        description=(
            "Pitch plan or grand finale slide: opening hook, ordered pitch structure with timestamps, "
            "anticipated jury/investor questions, and the team's prepared answers. "
            "If a hook paragraph or opening narrative is written on this slide, capture it in pitch_hook."
        )
    )

    demo_plan: Optional[DemoPlan] = Field(
        default=None,
        description=(
            "Demo plan or presentation flow slide with a timed sequence of segments. "
            "This is SEPARATE from pitch_plan. Look for slides titled 'Demo Plan', 'Presentation Flow', "
            "or any slide showing a timeline of segments with timestamps (e.g. '0:00–1:30', '1:30–2:30'). "
            "Capture every segment with its timestamp and slide/content description."
        )
    )

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
            "Keep the output concise, readable, and close to the wording in the PDF. "
            "Do not invent facts. Do not guess missing values. "
            "If a field is not clearly present, leave it null or empty. "
            "For pitch_summary, problem_statement, and solution_summary, lightly compress but do not embellish. "
            "Only include URLs that are clearly visible in the PDF. "
            "Put demo, prototype, product, GitHub, drive, landing page, website, and asset URLs into links_or_assets. "
            "Put research, bibliography, citation, and references-slide URLs into reference_links. "
            "Do not set github_link_present, demo_links_present, or financial_model_link_present based on labels alone. "

            "For survey_data: extract EVERY statistic from any survey or validation slide individually. "
            "Include bar chart entries, pie chart percentages, and multi-select results as separate items. "
            "Use the exact percentage as shown — do not round or estimate. "
            "Each SurveyDataPoint must have the question context and the precise finding. "

            "For team_members: extract the full name of every team member shown on any team slide. "

            "For interviewees: look for any slide with sections like 'Interacted with', 'Spoke to', "
            "'Who we spoke to', or 'Interviewed'. Extract every named individual as a separate entry "
            "with their name and role/expertise exactly as written. Do not merge multiple people. "

            "For technical_details: capture all named chemicals, dyes, proteins, materials, or biological "
            "mechanisms explicitly named in the deck, preserving exact names. "

            "For financials.revenue_milestones: capture all volume-to-revenue projections, "
            "break-even targets, profitability timelines, and total build/setup cost ranges. "

            "For financials.key_assumptions: extract any explicitly listed key assumptions from "
            "financial, profit model, or revenue slides. These are business/market assumptions "
            "the team states their model depends on. Capture each assumption as a separate item. "

            "For pitch_plan: if the deck contains a pitch plan, grand finale plan, or pitch structure slide, "
            "extract the opening hook paragraph into pitch_hook (verbatim or near-verbatim), "
            "the ordered sections with timestamps into pitch_structure, and all anticipated "
            "questions into anticipated_questions with their corresponding answers into prepared_answers "
            "in the same order. "

            "For demo_plan: look for any slide titled 'Demo Plan', 'Presentation Flow', or showing a "
            "timed sequence of presentation segments. This is SEPARATE from pitch_plan. "
            "Extract every segment with its timestamp range and content/slide description into segments. "
            "e.g. '0:00–1:30: Slide 1 — Title & Hook'. Capture ALL segments listed. "

            "For implementation_stats: look at the footer or summary section of the implementation "
            "or roadmap slide for summary statistics like target beta users, total milestones count, "
            "end goal label, and phase 1 budget. Capture each if present. "
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
    "team_members",
    "problem_statement",
    "core_problem",
    "affected_users",
    "pain_points",
    "impact_points",
    "problem_frequency",
    "customer_discovery_summary",
    "interviewees",
    "key_learnings",
    "changes_made",
    "survey_data",
    "solution_summary",
    "solution_approach",
    "features",
    "differentiators",
    "technical_details",
    "competitors",
    "competition_gaps",
    "market",
    "business_model",
    "financials",
    "roadmap",
    "implementation_stats",
    "pitch_plan",
    "demo_plan",
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


def is_valid_url(url: str) -> bool:
    url = normalize_url(url)
    pattern = re.compile(
        r"^(https?://)"
        r"(([A-Za-z0-9-]+\.)+[A-Za-z]{2,}|localhost)"
        r"(:\d+)?"
        r"(/[^\s]*)?$",
        flags=re.IGNORECASE,
    )
    return bool(pattern.match(url))


def extract_urls_from_text(text: str) -> List[str]:
    urls = []

    markdown_urls = re.findall(r"\((https?://[^\s)]+)\)", text, flags=re.IGNORECASE)
    urls.extend(markdown_urls)

    plain_urls = re.findall(r"https?://[^\s<>\"')\]]+", text, flags=re.IGNORECASE)
    urls.extend(plain_urls)

    cleaned = []
    seen = set()

    for u in urls:
        u = normalize_url(u)

        if not u.startswith("http"):
            continue
        if "](" in u or "[" in u or "]" in u:
            continue
        if not is_valid_url(u):
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
        "vercel.app",
        "lovable.app",
        "run.app",
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
        if not item:
            continue
        item = normalize_url(item)
        if not is_valid_url(item):
            continue
        if item not in seen:
            seen.add(item)
            merged.append(item)

    return merged


def dedupe_urls(urls: List[str]) -> List[str]:
    cleaned = []
    seen = set()

    for url in urls:
        url = normalize_url(url)
        if not is_valid_url(url):
            continue
        if url not in seen:
            seen.add(url)
            cleaned.append(url)

    return cleaned


def remove_prefix_truncated_urls(urls: List[str]) -> List[str]:
    cleaned = dedupe_urls(urls)
    to_remove = set()

    for i, u1 in enumerate(cleaned):
        for j, u2 in enumerate(cleaned):
            if i == j:
                continue
            if len(u1) < len(u2) and u2.startswith(u1):
                to_remove.add(u1)

    return [u for u in cleaned if u not in to_remove]


def separate_cross_duplicates(asset_urls: List[str], reference_urls: List[str]):
    asset_urls = dedupe_urls(asset_urls)
    reference_urls = dedupe_urls(reference_urls)

    asset_set = set(asset_urls)
    reference_urls = [u for u in reference_urls if u not in asset_set]

    return asset_urls, reference_urls


def has_demo_link(urls: List[str]) -> bool:
    demo_domains = [
        "youtube.com",
        "youtu.be",
        "drive.google.com",
        "vercel.app",
        "lovable.app",
        "run.app",
        "prototype",
        "demo",
    ]
    return any(any(k in url.lower() for k in demo_domains) for url in urls)


def has_github_link(urls: List[str]) -> bool:
    return any("github.com" in url.lower() for url in urls)


def has_financial_model_link(urls: List[str]) -> bool:
    keywords = ["financial-model", "financialmodel", "sheet", "docs.google.com/spreadsheets"]
    return any(any(k in url.lower() for k in keywords) for url in urls)


def post_process_result(result: dict, fallback_asset_urls: List[str], fallback_reference_urls: List[str]) -> dict:
    notes = list(result.get("extraction_notes", []) or [])

    raw_assets = result.get("links_or_assets", []) or []
    raw_refs = result.get("reference_links", []) or []

    merged_assets = merge_unique(raw_assets, fallback_asset_urls)
    merged_refs = merge_unique(raw_refs, fallback_reference_urls)

    merged_assets = remove_prefix_truncated_urls(merged_assets)
    merged_refs = remove_prefix_truncated_urls(merged_refs)

    merged_assets, merged_refs = separate_cross_duplicates(merged_assets, merged_refs)

    removed_asset_count = max(0, len(raw_assets) + len(fallback_asset_urls) - len(merged_assets))
    removed_ref_count = max(0, len(raw_refs) + len(fallback_reference_urls) - len(merged_refs))

    if removed_asset_count > 0:
        notes.append("Some malformed or duplicate asset links were removed.")
    if removed_ref_count > 0:
        notes.append("Some malformed, truncated, or duplicate reference links were removed.")

    result["links_or_assets"] = merged_assets
    result["reference_links"] = merged_refs

    all_urls = dedupe_urls(merged_assets + merged_refs)

    result["demo_links_present"] = has_demo_link(all_urls)
    result["github_link_present"] = has_github_link(all_urls)

    if result.get("financials") and isinstance(result["financials"], dict):
        result["financials"]["financial_model_link_present"] = has_financial_model_link(all_urls)

    if not all_urls:
        result["demo_links_present"] = False
        result["github_link_present"] = False
        if result.get("financials") and isinstance(result["financials"], dict):
            result["financials"]["financial_model_link_present"] = False

    # light cleanup for empty strings
    for key, value in list(result.items()):
        if isinstance(value, str) and not value.strip():
            result[key] = None

    result["extraction_notes"] = list(dict.fromkeys([n for n in notes if n.strip()]))

    return result


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

    result = post_process_result(
        result=result,
        fallback_asset_urls=fallback_asset_urls,
        fallback_reference_urls=fallback_reference_urls,
    )

    result["parser_version"] = "code_tweaked_v4"

    result = reorder_dict(result, PREFERRED_ORDER + ["parser_version"])

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

    # TEST MODE: filter to a specific team by filename, or take only the first PDF
    if TEST_TEAM_NAME:
        pdf_files = [p for p in pdf_files if TEST_TEAM_NAME.lower() in p.name.lower()]
        if not pdf_files:
            raise FileNotFoundError(f"No PDF found matching TEST_TEAM_NAME='{TEST_TEAM_NAME}' in: {input_dir}")
        print(f"TEST MODE: running on 1 file matching '{TEST_TEAM_NAME}': {pdf_files[0].name}")
    else:
        # Remove this line when ready to run all files
        pdf_files = pdf_files[:1]
        print(f"TEST MODE: running on first PDF only: {pdf_files[0].name}")
        print("To run all files, remove the pdf_files[:1] line and set TEST_TEAM_NAME=None.")

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
