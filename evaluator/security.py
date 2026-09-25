"""Heuristic security scorer for a static HTML/CSS/JS site.

These are basic, static pattern checks - not a real security audit. They
catch the kind of obvious issues an LLM-generated site can easily
introduce (inline handlers, unescaped innerHTML, http:// resources,
password fields in GET forms, etc.). A natural upgrade path is to run a
real scanner (e.g. an HTML/CSS/JS linter with security rules, or a
headless-browser-based header/CSP check) instead of these regexes.
"""
import re
from html.parser import HTMLParser
from typing import List, Tuple

from website.site import Website


class _SecurityParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inline_handlers = 0
        self.http_resources = 0
        self.blank_targets_without_noopener = 0
        self.password_inputs_in_get_form = False
        self._current_form_method = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        for key in attrs_dict:
            if key.lower().startswith("on"):
                self.inline_handlers += 1

        for attr_name in ("src", "href"):
            val = attrs_dict.get(attr_name, "")
            if val.startswith("http://"):
                self.http_resources += 1

        if tag == "a" and attrs_dict.get("target") == "_blank":
            rel = attrs_dict.get("rel", "")
            if "noopener" not in rel:
                self.blank_targets_without_noopener += 1

        if tag == "form":
            self._current_form_method = attrs_dict.get("method", "get").lower()
        if tag == "input" and attrs_dict.get("type") == "password":
            if self._current_form_method == "get":
                self.password_inputs_in_get_form = True

    def handle_endtag(self, tag):
        if tag == "form":
            self._current_form_method = None


def score_security(site: Website) -> Tuple[float, List[str]]:
    findings: List[str] = []
    score = 70.0  # security starts higher: absence of red flags is the common case

    html = "\n".join(v for k, v in site.files.items() if k.endswith(".html"))
    js = "\n".join(v for k, v in site.files.items() if k.endswith(".js"))

    parser = _SecurityParser()
    parser.feed(html)

    if parser.inline_handlers:
        penalty = min(20, 5 * parser.inline_handlers)
        score -= penalty
        findings.append(f"-{penalty} {parser.inline_handlers} inline event handler attribute(s) (onclick=, onerror=, ...)")
    else:
        score += 5
        findings.append("+5 no inline event handler attributes")

    if parser.http_resources:
        penalty = min(15, 5 * parser.http_resources)
        score -= penalty
        findings.append(f"-{penalty} {parser.http_resources} resource(s) loaded over plain http://")

    if parser.blank_targets_without_noopener:
        penalty = min(10, 3 * parser.blank_targets_without_noopener)
        score -= penalty
        findings.append(f'-{penalty} target="_blank" link(s) missing rel="noopener"')

    if parser.password_inputs_in_get_form:
        score -= 20
        findings.append('-20 a password field lives inside a form using method="get"')

    if re.search(r'\beval\s*\(', js):
        score -= 15
        findings.append("-15 JS uses eval(...)")

    if re.search(r'document\.write\s*\(', js):
        score -= 10
        findings.append("-10 JS uses document.write(...)")

    if re.search(r'\.innerHTML\s*(\+=|=[^;]*\+)', js):
        score -= 15
        findings.append("-15 JS builds innerHTML via string concatenation (possible XSS)")

    return max(0.0, min(100.0, score)), findings
