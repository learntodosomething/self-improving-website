"""Main loop: generate -> evaluate -> accept/reject -> let the meta-improver
learn from the outcome -> repeat.
"""
from website.site import Website
from generator.improver import generate_improvement
from evaluator.scorer import evaluate
from meta.meta_improver import MetaImprover, GenerationRecord
from logging_utils.logger import RunLogger

import config


def main():
    site = Website.load(config.SITE_SOURCE_DIR)
    meta = MetaImprover()
    logger = RunLogger()

    baseline_report = evaluate(site, meta.strategy.category_weights)
    print(f"Starting scores: {baseline_report.category_scores}")
    print(f"Starting overall: {baseline_report.overall:.1f}\n")

    for generation in range(1, config.GENERATIONS + 1):
        # Evaluate the current site fresh each generation, using this
        # generation's weights - the meta-improver can change
        # category_weights between generations, so we don't want to
        # compare against a stale overall score computed with old weights.
        current_report = evaluate(site, meta.strategy.category_weights)

        category = meta.choose_category()
        temperature = meta.strategy.category_temperature[category]
        guidance = meta.get_guidance(category)

        proposal = generate_improvement(site, category, guidance, temperature)

        if proposal is None:
            print(f"[gen {generation:>3}] category={category:<10} - generation failed to parse, skipping")
            continue

        candidate = site.clone()
        candidate.set_file(proposal["target_file"], proposal["new_content"])

        candidate_report = evaluate(candidate, meta.strategy.category_weights)

        accepted = candidate_report.overall >= current_report.overall

        record = GenerationRecord(
            generation=generation,
            category=category,
            temperature=temperature,
            score_before=current_report.category_scores[category],
            score_after=candidate_report.category_scores[category],
            accepted=accepted,
            change_description=f"[{proposal['target_file']}] {proposal['change_description']}",
        )

        logger.log_generation(record, current_report.overall, candidate_report.overall)

        if accepted:
            site = candidate

        meta.record(record)
        logger.log_strategy(generation, meta.strategy)

    final_report = evaluate(site, meta.strategy.category_weights)
    site.save(str(logger.run_dir / "final_site"))
    logger.finalize()

    print("\nFinal scores:")
    for category, score in final_report.category_scores.items():
        print(f"  {category:<10}: {score:.1f}")
    print(f"  overall   : {final_report.overall:.1f}")


if __name__ == "__main__":
    main()
