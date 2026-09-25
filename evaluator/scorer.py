"""Combines the three category scorers into one overall evaluation."""
from dataclasses import dataclass
from typing import Dict, List

from website.site import Website
from evaluator.appearance import score_appearance
from evaluator.usability import score_usability
from evaluator.security import score_security

CATEGORY_SCORERS = {
    "appearance": score_appearance,
    "usability": score_usability,
    "security": score_security,
}


@dataclass
class ScoreReport:
    category_scores: Dict[str, float]
    findings: Dict[str, List[str]]
    weights: Dict[str, float]

    @property
    def overall(self) -> float:
        total_weight = sum(self.weights.values()) or 1.0
        weighted = sum(self.category_scores[c] * self.weights.get(c, 0) for c in self.category_scores)
        return weighted / total_weight


def evaluate(site: Website, weights: Dict[str, float]) -> ScoreReport:
    category_scores: Dict[str, float] = {}
    findings: Dict[str, List[str]] = {}
    for category, scorer in CATEGORY_SCORERS.items():
        score, notes = scorer(site)
        category_scores[category] = score
        findings[category] = notes
    return ScoreReport(category_scores=category_scores, findings=findings, weights=dict(weights))
