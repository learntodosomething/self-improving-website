"""Heuristic appearance / visual design scorer.

This is intentionally simple: regex-based checks on the CSS/HTML text.
It is NOT a substitute for an actual visual review - there is no
rendering or screenshot comparison here, only structural signals that
correlate with "looks more put together". A natural upgrade path is to
render the page (e.g. headless browser), take a screenshot, and score it
with a vision-capable model instead.
"""
import re
from typing import List, Tuple

from website.site import Website


def score_appearance(site: Website) -> Tuple[float, List[str]]:
    findings: List[str] = []
    score = 50.0  # neutral baseline; individual checks add or subtract points

    css = "\n".join(v for k, v in site.files.items() if k.endswith(".css"))
    html = "\n".join(v for k, v in site.files.items() if k.endswith(".html"))

    if re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.I):
        score += 10
        findings.append("+10 has a responsive viewport meta tag")
    else:
        score -= 10
        findings.append('-10 missing <meta name="viewport">')

    css_vars = re.findall(r'--[\w-]+\s*:', css)
    if len(css_vars) >= 3:
        score += 10
        findings.append(f"+10 uses {len(css_vars)} CSS custom properties (design tokens)")
    elif len(css_vars) > 0:
        score += 5
        findings.append(f"+5 uses {len(css_vars)} CSS custom properties")
    else:
        findings.append("+0 no CSS custom properties (design tokens) found")

    if re.search(r'display\s*:\s*(flex|grid)', css):
        score += 10
        findings.append("+10 uses flexbox/grid for layout")
    else:
        findings.append("+0 no flexbox/grid layout detected")

    hex_colors = set(re.findall(r'#(?:[0-9a-fA-F]{3}){1,2}\b', css))
    if 0 < len(hex_colors) <= 6:
        score += 10
        findings.append(f"+10 focused color palette ({len(hex_colors)} distinct colors)")
    elif len(hex_colors) > 10:
        score -= 10
        findings.append(f"-10 color palette looks inconsistent ({len(hex_colors)} distinct colors)")
    else:
        findings.append(f"+0 {len(hex_colors)} distinct colors used (neither focused nor excessive)")

    font_families = set(re.findall(r'font-family\s*:\s*([^;]+);', css))
    if len(font_families) > 4:
        score -= 5
        findings.append(f"-5 too many distinct font-family declarations ({len(font_families)})")

    if re.search(r'(margin|padding)\s*:', css):
        score += 5
        findings.append("+5 explicit spacing (margin/padding) is defined")

    return max(0.0, min(100.0, score)), findings
