"""Run logging: console output, JSON log files, and score/strategy charts."""
import json
from datetime import datetime
from pathlib import Path
from typing import List

import matplotlib
matplotlib.use("Agg")  # headless-safe backend, no display needed
import matplotlib.pyplot as plt

from meta.meta_improver import GenerationRecord, Strategy


class RunLogger:
    def __init__(self, base_dir: str = "runs"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = Path(base_dir) / timestamp
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.records: List[dict] = []
        self.weight_snapshots: List[dict] = []

    def log_generation(self, record: GenerationRecord, overall_before: float, overall_after: float) -> None:
        status = "ACCEPTED" if record.accepted else "rejected"
        print(
            f"[gen {record.generation:>3}] category={record.category:<10} "
            f"temp={record.temperature:.2f}  overall {overall_before:.1f} -> {overall_after:.1f}  [{status}]"
        )
        print(f"           {record.change_description}")

        self.records.append({
            "generation": record.generation,
            "category": record.category,
            "temperature": record.temperature,
            "score_before": record.score_before,
            "score_after": record.score_after,
            "overall_before": overall_before,
            "overall_after": overall_after,
            "accepted": record.accepted,
            "change_description": record.change_description,
        })

    def log_strategy(self, generation: int, strategy: Strategy) -> None:
        self.weight_snapshots.append({
            "generation": generation,
            "weights": dict(strategy.category_weights),
            "temperatures": dict(strategy.category_temperature),
            "prompt_style": strategy.prompt_style,
        })

    def finalize(self) -> None:
        (self.run_dir / "log.json").write_text(json.dumps(self.records, indent=2), encoding="utf-8")
        (self.run_dir / "strategy_history.json").write_text(json.dumps(self.weight_snapshots, indent=2), encoding="utf-8")
        self._plot_scores()
        self._plot_strategy()
        print(f"\nRun artifacts saved to: {self.run_dir}")

    def _plot_scores(self) -> None:
        if not self.records:
            return
        gens = [r["generation"] for r in self.records]
        overall = [r["overall_after"] for r in self.records]

        plt.figure(figsize=(8, 4.5))
        plt.plot(gens, overall, marker="o")
        plt.title("Overall website score over generations")
        plt.xlabel("Generation")
        plt.ylabel("Overall score (0-100)")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(self.run_dir / "score_history.png")
        plt.close()

    def _plot_strategy(self) -> None:
        if not self.weight_snapshots:
            return
        gens = [s["generation"] for s in self.weight_snapshots]
        categories = self.weight_snapshots[0]["weights"].keys()

        plt.figure(figsize=(8, 4.5))
        for category in categories:
            values = [s["weights"][category] for s in self.weight_snapshots]
            plt.plot(gens, values, marker="o", label=category)
        plt.title("Meta-improver: category weight evolution")
        plt.xlabel("Generation")
        plt.ylabel("Selection weight")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(self.run_dir / "strategy_history.png")
        plt.close()
