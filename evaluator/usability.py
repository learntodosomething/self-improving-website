"""Heuristic usability / UX scorer, based on structural HTML signals."""
import re
from html.parser import HTMLParser
from typing import List, Tuple

from website.site import Website

GENERIC_LINK_TEXTS = {"click here", "here", "link", "read more", "more"}
SEMANTIC_TAGS = {"header", "nav", "main", "footer", "article", "section"}


class _UsabilityParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images_total = 0
        self.images_missing_alt = 0
        self.inputs_total = 0
        self.input_ids: List[str] = []
        self.label_fors: List[str] = []
        self.semantic_tags_found = set()
        self.generic_links = 0
        self.total_links = 0
        self._current_link_text = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "img":
            self.images_total += 1
            if not attrs_dict.get("alt", "").strip():
                self.images_missing_alt += 1
        elif tag == "input":
            self.inputs_total += 1
            if attrs_dict.get("id"):
                self.input_ids.append(attrs_dict["id"])
        elif tag == "label":
            if attrs_dict.get("for"):
                self.label_fors.append(attrs_dict["for"])
        elif tag in SEMANTIC_TAGS:
            self.semantic_tags_found.add(tag)
        elif tag == "a":
            self.total_links += 1
            self._current_link_text = ""

    def handle_data(self, data):
        if self._current_link_text is not None:
            self._current_link_text += data

    def handle_endtag(self, tag):
        if tag == "a" and self._current_link_text is not None:
            text = self._current_link_text.strip().lower()
            if text in GENERIC_LINK_TEXTS:
                self.generic_links += 1
            self._current_link_text = None


def score_usability(site: Website) -> Tuple[float, List[str]]:
    findings: List[str] = []
    score = 50.0

    html = "\n".join(v for k, v in site.files.items() if k.endswith(".html"))
    css = "\n".join(v for k, v in site.files.items() if k.endswith(".css"))

    parser = _UsabilityParser()
    parser.feed(html)

    if parser.images_total:
        ok = parser.images_total - parser.images_missing_alt
        ratio = ok / parser.images_total
        gained = 10 * ratio
        score += gained
        findings.append(f"+{gained:.0f} {ok}/{parser.images_total} images have alt text")

    if parser.inputs_total:
        labelled = len(set(parser.input_ids) & set(parser.label_fors))
        ratio = labelled / parser.inputs_total
        gained = 10 * ratio
        score += gained
        findings.append(f"+{gained:.0f} {labelled}/{parser.inputs_total} inputs have an associated <label>")

    gained = 3 * len(parser.semantic_tags_found)
    score += gained
    findings.append(f"+{gained} uses semantic tags: {sorted(parser.semantic_tags_found) or 'none'}")

    if parser.total_links and parser.generic_links:
        penalty = min(10, 3 * parser.generic_links)
        score -= penalty
        findings.append(f"-{penalty} {parser.generic_links} link(s) use generic text like 'click here'")

    if re.search(r':hover', css):
        score += 5
        findings.append("+5 interactive elements have :hover states")
    else:
        findings.append("+0 no :hover states found")

    return max(0.0, min(100.0, score)), findings
