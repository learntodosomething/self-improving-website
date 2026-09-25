"""Object-level improvement generator.

Asks the local LLM for exactly one concrete change to one file, scoped to
a single improvement category (appearance / usability / security).

Note: we deliberately do NOT ask the model for JSON here. Asking a small
local model to correctly JSON-escape a full multi-line HTML/CSS/JS file
(quotes, newlines, backslashes) is a common source of parse failures with
7B-class models. A simple delimited text format is far more reliable for
embedding a whole file's contents.
"""
from typing import Dict, Optional

from openai import OpenAI

from website.site import Website

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",  # LM Studio does not check this
)

MODEL_NAME = "qwen2.5-coder-7b-instruct"

CATEGORY_FOCUS = {
    "appearance": (
        "visual design: color palette consistency, typography, spacing, "
        "modern layout (flexbox/grid), visual hierarchy."
    ),
    "usability": (
        "usability and UX: navigation clarity, mobile responsiveness, "
        "accessible forms (labels, alt text), descriptive link text, "
        "interactive feedback (:hover / focus states)."
    ),
    "security": (
        "security best practices for a static site: remove inline event "
        "handler attributes (onclick=, onerror=, ...), avoid eval()/"
        "document.write(), never build innerHTML via string concatenation, "
        "use https:// for external resources, add rel=\"noopener noreferrer\" "
        "to target=\"_blank\" links, use method=\"post\" for forms that "
        "contain password fields."
    ),
}

CONTENT_START = "---CONTENT-START---"
CONTENT_END = "---CONTENT-END---"


def _build_prompt(site: Website, category: str, guidance: str) -> str:
    return f"""You are improving a small static website (HTML/CSS/JS), one focused change at a time.

Category for this change: {category}
Focus area: {CATEGORY_FOCUS[category]}

{guidance}

Current website files:
{site.combined_source()}

Propose EXACTLY ONE concrete, self-contained change to ONE file that improves this category.
Reply in EXACTLY this format and nothing else (no markdown fences, no extra commentary):

TARGET_FILE: <one of the existing file names, exactly as given above>
CHANGE: <one short sentence describing the change>
{CONTENT_START}
<the COMPLETE new content of that file after the change, nothing else>
{CONTENT_END}
"""


def _parse_response(raw: str, site: Website) -> Optional[Dict]:
    if CONTENT_START not in raw or CONTENT_END not in raw:
        return None

    header, rest = raw.split(CONTENT_START, 1)
    content_part, _, _ = rest.partition(CONTENT_END)
    new_content = content_part.strip("\n")

    target_file = None
    change_description = ""
    for line in header.splitlines():
        line = line.strip()
        if line.startswith("TARGET_FILE:"):
            target_file = line.split(":", 1)[1].strip()
        elif line.startswith("CHANGE:"):
            change_description = line.split(":", 1)[1].strip()

    if not target_file or target_file not in site.files:
        return None
    if not new_content.strip():
        return None

    return {
        "target_file": target_file,
        "change_description": change_description or "(no description given)",
        "new_content": new_content,
    }


def generate_improvement(site: Website, category: str, guidance: str, temperature: float) -> Optional[Dict]:
    prompt = _build_prompt(site, category, guidance)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=2500,
    )

    raw = response.choices[0].message.content.strip()
    return _parse_response(raw, site)
