"""The recursive / meta-level part of the system.

The MetaImprover doesn't touch the website directly - it watches how well
the object-level generator's proposals do, per category, and adjusts:
  - which category gets picked next (category_weights)
  - how creative/random the generator is allowed to be (category_temperature)
  - what extra guidance gets injected into the next prompt (guidance_notes,
    prompt_style)

This is what makes the loop "recursive self-improvement" rather than a
plain hill-climbing optimizer: the STRATEGY that produces changes is
itself being changed, based on the results those changes get.
"""
import random
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class GenerationRecord:
    generation: int
    category: str
    temperature: float
    score_before: float   # this category's score before the change
    score_after: float    # this category's score after the change
    accepted: bool
    change_description: str


@dataclass
class Strategy:
    category_weights: Dict[str, float] = field(
        default_factory=lambda: {"appearance": 1.0, "usability": 1.0, "security": 1.0}
    )
    category_temperature: Dict[str, float] = field(
        default_factory=lambda: {"appearance": 0.4, "usability": 0.4, "security": 0.3}
    )
    guidance_notes: Dict[str, List[str]] = field(
        default_factory=lambda: {"appearance": [], "usability": [], "security": []}
    )
    prompt_style: str = "Make one focused, meaningful change. Prefer changes you are confident will help."


class MetaImprover:
    REFLECT_EVERY = 5        # how often (in generations) to update the strategy
    MAX_NOTES_PER_CATEGORY = 3

    def __init__(self):
        self.strategy = Strategy()
        self.history: List[GenerationRecord] = []

    def choose_category(self) -> str:
        categories = list(self.strategy.category_weights.keys())
        weights = [max(0.05, self.strategy.category_weights[c]) for c in categories]
        return random.choices(categories, weights=weights, k=1)[0]

    def get_guidance(self, category: str) -> str:
        notes = self.strategy.guidance_notes[category]
        note_text = ""
        if notes:
            note_text = "\nLessons from previous attempts in this category:\n" + "\n".join(f"- {n}" for n in notes)
        return f"{self.strategy.prompt_style}{note_text}"

    def record(self, record: GenerationRecord) -> None:
        self.history.append(record)
        if record.generation % self.REFLECT_EVERY == 0:
            self.reflect()

    def reflect(self) -> None:
        """Look at the most recent window of generations and adjust the strategy."""
        recent = self.history[-self.REFLECT_EVERY:]
        if not recent:
            return

        # --- Re-weight categories by average score gain per attempt ---
        gains: Dict[str, List[float]] = {c: [] for c in self.strategy.category_weights}
        for r in recent:
            gains.setdefault(r.category, [])
            gains[r.category].append(r.score_after - r.score_before if r.accepted else 0.0)

        for category, deltas in gains.items():
            if deltas:
                avg_gain = sum(deltas) / len(deltas)
                current = self.strategy.category_weights.get(category, 1.0)
                self.strategy.category_weights[category] = max(0.1, current + avg_gain * 0.05)

        # --- Adjust temperature per category based on acceptance rate ---
        for category in self.strategy.category_temperature:
            cat_records = [r for r in recent if r.category == category]
            if not cat_records:
                continue
            acceptance_rate = sum(r.accepted for r in cat_records) / len(cat_records)
            current_temp = self.strategy.category_temperature[category]
            if acceptance_rate < 0.3:
                # Too many rejected changes: try being a bit more exploratory.
                self.strategy.category_temperature[category] = min(0.9, current_temp + 0.1)
            elif acceptance_rate > 0.8:
                # Almost everything gets accepted - nudge exploration up a
                # little anyway, so the search doesn't just settle.
                self.strategy.category_temperature[category] = min(0.9, current_temp + 0.03)

        # --- Extract a guidance note from the best accepted change this window ---
        accepted = [r for r in recent if r.accepted]
        if accepted:
            best = max(accepted, key=lambda r: r.score_after - r.score_before)
            note = best.change_description.strip()
            notes = self.strategy.guidance_notes.setdefault(best.category, [])
            if note and note not in notes:
                notes.append(note)
                if len(notes) > self.MAX_NOTES_PER_CATEGORY:
                    notes.pop(0)

        # --- Adjust global prompt style based on overall acceptance rate ---
        overall_rate = sum(r.accepted for r in recent) / len(recent)
        if overall_rate < 0.3:
            self.strategy.prompt_style = "Make a SMALL, safe, incremental change. Avoid large rewrites."
        elif overall_rate > 0.8:
            self.strategy.prompt_style = "Be bold - try a more substantial change than last time, not just a tweak."
        else:
            self.strategy.prompt_style = "Make one focused, meaningful change. Prefer changes you are confident will help."
