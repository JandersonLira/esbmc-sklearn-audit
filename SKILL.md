---
name: esbmc-sklearn-audit
description: Execute the ESBMC-based verification methodology for Scikit-Learn regression artifacts, using paired `wrapper/` and `sklearn/` executable families, the 20 controlled validations from the reference study, and the same severity scoring model (`Baixa=1`, `Moderada=2`, `Alta=3`, `Critica=4`). Use when Codex needs to run or reproduce the article workflow, compare formal ESBMC results against concrete sklearn runtime behavior, summarize failure scores per tested regressor, and draft an ESBMC repository issue when divergences indicate tooling or modeling improvement opportunities.
---

# ESBMC Sklearn Audit

Execute the same four-stage methodology used in the reference article: run the concrete sklearn executables, run the abstract ESBMC wrappers, compare both result sets, and summarize the findings with severity scoring plus an issue proposal when the evidence suggests a frontend limitation or false positive in ESBMC.

## Expected Workspace

Work from a repository or study folder that follows this layout:

- `wrapper/executaveis/*.py`: abstract ESBMC-oriented wrappers
- `sklearn/executaveis/*.py`: concrete sklearn runtime executables
- optional `wrapper/prompts/` and `sklearn/prompts/`: generation prompts used in the study
- optional `results/`: existing summaries or logs

Assume the tested executables follow the study naming contract:

- `linear_regression_01_predict_before_fit.py`
- `ridge_19_bounded_numeric_accumulation.py`
- `decision_tree_regressor_20_symbolic_composite_configuration.py`

If the workspace diverges from that structure, inspect it first and adapt the commands before running the scripts.

## Workflow

1. Confirm the workspace contains the paired `wrapper/executaveis` and `sklearn/executaveis` directories.
2. Read [references/validation-catalog.md](references/validation-catalog.md) if you need the exact meaning of the 20 validations or their default severity guidance.
3. Run the full methodology with:

```bash
python3 ~/.codex/skills/esbmc-sklearn-audit/scripts/run_methodology.py \
  --root /path/to/workspace \
  --python-bin /path/to/python \
  --esbmc-bin /path/to/esbmc
```

4. Review the generated outputs under `results/skill_audit/`:
   - `sklearn_runtime/summary.tsv`
   - `wrapper_esbmc/summary.tsv`
   - `comparison/comparison.csv`
   - `report/summary.json`
   - `report/summary.md`
   - `report/esbmc_issue_proposal.md` when issue candidates are found
5. Present the user with:
   - the tested regressors
   - the count of successes, failures, and divergences
   - the score per regressor
   - the scored findings table
   - the issue proposal when generated
6. Interpret the ranking cautiously. The score is comparative evidence for the tested scenarios, not an absolute measure of model or library security.

## Severity And Scoring

Use the article's scoring system exactly:

- `Baixa`: 1 point
- `Moderada`: 2 points
- `Alta`: 3 points
- `Critica`: 4 points
- no observed failure: 0 points

Base each classification on the same four dimensions from the study:

- impacto potencial
- facilidade de ativacao
- reprodutibilidade
- abrangencia no fluxo de uso

The bundled runner applies a default severity recommendation per validation from the reference study so the workflow stays reproducible. If a log shows stronger evidence than the default recommendation, prefer the stronger severity and explain why in the final write-up.

## Concrete Operating Rules

- Run the concrete sklearn executables before the ESBMC wrappers.
- Keep the comparison file-by-file. Each wrapper must be paired with the concrete executable that shares the same filename stem.
- Treat `sklearn PASS` plus `wrapper FAILED` as a divergence worth investigating. This is the main trigger for a possible ESBMC improvement issue.
- Treat repeated divergences concentrated in the same validation family as stronger evidence of a tooling or modeling gap.
- For validation `19` (`bounded_numeric_accumulation`), if the wrapper log shows symbolic `NaN` or infinite values violating numeric assumptions while the concrete sklearn executable passes, treat that as the reference study's canonical improvement opportunity and generate an issue proposal.

## Reporting Guidance

Always report the results in two layers:

1. Validation-level findings:
   - file
   - regressor
   - validation id and title
   - concrete status
   - wrapper status
   - comparison note
   - severity
   - score
   - short rationale
2. Regressor-level aggregation:
   - successes
   - failures
   - total score
   - technical tie or ranking

When the generated report contains an issue draft, summarize it for the user and point to the saved file instead of rewriting it from scratch.

## Resources

- [references/validation-catalog.md](references/validation-catalog.md): 20 validations, phases, file suffixes, and default severity recommendations
- [references/methodology-notes.md](references/methodology-notes.md): condensed article methodology and interpretation rules
- `scripts/run_methodology.py`: end-to-end execution, comparison, scoring, and report generation
