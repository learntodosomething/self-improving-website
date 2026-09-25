# 🌱 Website RSI — Recursive Self-Improving Website Optimizer

A local, LLM-driven loop that takes a static website (HTML/CSS/JS), and repeatedly proposes, tests, and accepts or rejects changes across three dimensions — **appearance**, **usability**, and **security** — while a **meta-improver** watches which kinds of changes actually pay off and adjusts its own strategy accordingly.

This is a sibling project to [recursive-code-improver](../recursive-code-improver): same local-LLM approach, applied to a different domain, with an added meta-learning layer.

## What "RSI" means here

Two levels are running at once:

- **Object level** — the system proposes a concrete code change (a new CSS rule, a fixed HTML attribute, a rewritten JS function) and tests whether it actually improved the score. This is the "normal" optimization loop, and on its own it's just hill-climbing.
- **Meta level** — every few generations, the system looks back at *what kinds of changes have been working* and changes **how it generates future changes**: which category it focuses on more, how much randomness (`temperature`) it allows itself per category, and what extra guidance gets added to the prompt. This is the recursive part: the strategy that produces improvements is itself being improved, based on evidence from its own results.

Without the meta level, this would just be an LLM-in-a-loop optimizer. With it, the system's *behavior* — not just the website — changes over the course of a run.

## How object-level vs. meta-level improvement works in the code

| | Object level | Meta level |
|---|---|---|
| Lives in | `generator/improver.py` | `meta/meta_improver.py` |
| Acts on | the website's files | its own `Strategy` (weights, temperatures, prompt guidance) |
| Runs | every generation | every `REFLECT_EVERY` generations (default: 5) |
| Input | current site + this generation's guidance | the last N `GenerationRecord`s (category, accepted?, score delta) |
| Output | one proposed file change | an updated `Strategy` |

Concretely, each generation:

1. `MetaImprover.choose_category()` picks a category (`appearance` / `usability` / `security`), weighted by `Strategy.category_weights` — categories that have been paying off get picked more often.
2. `MetaImprover.get_guidance(category)` builds a short text block: the current `prompt_style` (e.g. *"make a small, safe change"* vs *"be bold"*) plus up to 3 short "lessons learned" notes extracted from past successful changes in that category.
3. `generator.generate_improvement()` sends the whole site + that guidance + a category-specific focus description to the local LLM, and asks for exactly one file change.
4. `evaluator.scorer.evaluate()` scores the candidate; the change is accepted only if the *overall* weighted score doesn't drop.
5. The outcome is recorded as a `GenerationRecord`. Every 5 generations, `MetaImprover.reflect()` looks at the recent records and:
   - shifts `category_weights` toward categories with a better average score gain,
   - raises `category_temperature` for a category with a low acceptance rate (encourage it to try something different) or a suspiciously high one (keep exploring instead of settling),
   - pulls a short guidance note out of the best accepted change's description,
   - adjusts the global `prompt_style` based on the overall acceptance rate this window.

Both `runs/<timestamp>/score_history.png` (website score over time) and `runs/<timestamp>/strategy_history.png` (category weights over time) get saved at the end of a run, so you can see the object-level and meta-level changes side by side.

## Evaluator — what's actually being measured

Since there's no browser/vision model in this prototype, all three scorers are **static, heuristic checks** on the HTML/CSS/JS text (`html.parser` + regex), not a real design/UX/security review:

- **Appearance** (`evaluator/appearance.py`): responsive viewport tag, CSS custom properties, flexbox/grid usage, color palette size, font-family count, explicit spacing.
- **Usability** (`evaluator/usability.py`): image alt text, form `<label>` association, semantic HTML5 tags, generic link text ("click here"), `:hover` states.
- **Security** (`evaluator/security.py`): inline event handler attributes, `http://` resources, `target="_blank"` without `rel="noopener"`, password fields in `method="get"` forms, `eval()`/`document.write()`, `innerHTML` built via string concatenation.

Each check is commented in the source with what it's approximating and why — read those files first if you want to tighten or replace a check.

**Known simplifications**, worth knowing before you trust the numbers:
- No real rendering — an actually broken layout can still score well if the CSS "looks" modern on paper.
- No real accessibility audit (no contrast-ratio checks, no ARIA validation) — consider wiring in a real tool like `axe-core` later.
- No real security scanner — this catches obvious static red flags only, not a CSP/header audit or a real XSS analysis.
- Acceptance is greedy (`overall_after >= overall_before`) — the loop can get stuck in a local optimum. A future version could accept slightly-worse-overall changes occasionally (simulated annealing style) to escape one.

## Project structure

```
website-rsi/
├── README.md
├── requirements.txt
├── config.py
├── main.py
├── website/
│   └── site.py            # Website: load/save/clone a set of HTML/CSS/JS files
├── generator/
│   └── improver.py        # object-level: LLM proposes one change
├── evaluator/
│   ├── appearance.py
│   ├── usability.py
│   ├── security.py
│   └── scorer.py           # combines the three into one weighted score
├── meta/
│   └── meta_improver.py    # meta-level: strategy that adapts itself
├── logging_utils/
│   └── logger.py           # console + JSON logs + score/strategy charts
├── sites/
│   └── example_site/       # a small flower-shop site with deliberate issues
│       ├── index.html
│       ├── style.css
│       └── script.js
└── runs/                    # created at runtime, one folder per run (gitignored)
```

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Start a local LLM server** — in [LM Studio](https://lmstudio.ai/), load `qwen2.5-coder-7b-instruct` (or any other OpenAI-API-compatible model) and start the local server on `http://localhost:1234/v1`.
3. **Run it** (from this project's root, the folder containing `main.py`):
   ```bash
   python main.py
   ```

Each run creates `runs/<timestamp>/` containing `log.json` (every generation's details), `strategy_history.json` (every strategy snapshot), `score_history.png`, `strategy_history.png`, and `final_site/` (the improved website's final files).

## Adding a new website

1. Create a new folder under `sites/`, e.g. `sites/my_site/`, with `.html`/`.css`/`.js` files (only these three extensions are picked up — no images or other assets in this prototype).
2. In `config.py`, set:
   ```python
   SITE_SOURCE_DIR = "sites/my_site"
   ```
3. Run `python main.py` as usual.

There's nothing else to register — `Website.load()` picks up every `.html`/`.css`/`.js` file in the folder automatically.

## Example starting site

`sites/example_site/` is a small flower-shop page with realistic beginner mistakes seeded on purpose, roughly one or two per category (a missing viewport tag and an inconsistent color palette for appearance; an unlabeled form input and a "click here" link for usability; an inline `onclick`, an `http://` resource, and a password field in a GET form for security) — so the very first evaluation already shows clear room for improvement in all three categories, rather than starting from an already-polished page.

## Roadmap ideas

- Real accessibility auditing (`axe-core` or similar) instead of the alt-text/label heuristics
- Screenshot + vision-model-based appearance scoring instead of CSS regex
- Occasionally accept a slightly-worse-overall change to escape local optima
- Multi-page sites, and a real diff/rollback history instead of only the current + final snapshot
- Let the meta-improver also evolve the category *focus descriptions* themselves, not just weights/temperature/notes
