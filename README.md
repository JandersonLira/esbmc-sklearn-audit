# ESBMC Sklearn Audit

`ESBMC Sklearn Audit` is an open source Codex Skill that reproduces an ESBMC-based verification methodology for regression artifacts built around Scikit-Learn.

The repository packages a reusable workflow for:

- running concrete `sklearn` executables;
- running paired abstract `wrapper` programs with ESBMC;
- comparing formal and runtime outcomes file-by-file;
- scoring observed failures using the same severity model from the reference study;
- summarizing the score for each tested regressor;
- generating a draft GitHub issue for ESBMC when repeated divergences suggest a tooling or modeling improvement opportunity.

The current implementation follows the methodology applied to:

- `LinearRegression`
- `Ridge`
- `DecisionTreeRegressor`

## Motivation

Traditional machine learning evaluation usually emphasizes predictive metrics. This project complements that view with a formal software verification workflow focused on controlled properties of usage, configuration, training, prediction, and state transitions.

The goal is not to prove the complete internal safety of Scikit-Learn. Instead, the goal is to provide a reproducible and comparable methodology for auditing Python verification artifacts related to Scikit-Learn regressors using ESBMC.

## Repository Structure

```text
.
├── SKILL.md
├── LICENSE
├── README.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── methodology-notes.md
│   └── validation-catalog.md
└── scripts/
    └── run_methodology.py
```

## What The Skill Does

The Skill operationalizes a four-step audit loop:

1. Run concrete Scikit-Learn executables.
2. Run abstract ESBMC wrappers for the same scenarios.
3. Consolidate the results by matching paired filenames.
4. Score findings and produce a summary plus an issue proposal when appropriate.

The bundled workflow preserves the same validation catalog and scoring model from the study:

- `Baixa`: 1 point
- `Moderada`: 2 points
- `Alta`: 3 points
- `Critica`: 4 points
- no observed failure: 0 points

The methodology evaluates 20 controlled validations, including:

- predict before fit
- `X` and `y` consistency
- valid hyperparameters
- fit/predict typing
- feature consistency
- `None` parameter handling
- expected exceptions
- index bounds
- safe numeric domain
- critical paths
- reconfiguration after fit
- retraining with conflicting dimensions
- failure-state propagation
- safe state reset
- repeated prediction consistency
- preprocessing-chain contract
- training-counter monotonicity
- controlled fallback path
- bounded numeric accumulation
- symbolic composite configuration

## Requirements

Before using the Skill, confirm the environment contains:

- `esbmc` available in `PATH` or supplied explicitly
- a Python interpreter with `scikit-learn` installed for the concrete executables
- a workspace containing paired directories such as:
  - `wrapper/executaveis/*.py`
  - `sklearn/executaveis/*.py`

## Usage

### As a Codex Skill

Invoke the Skill from Codex with a prompt such as:

```text
Use $esbmc-sklearn-audit to execute the ESBMC verification methodology on this Scikit-Learn regression workspace and summarize the failure scores.
```

### As a Standalone Script

You can also run the workflow directly:

```bash
python3 scripts/run_methodology.py \
  --root /path/to/workspace \
  --python-bin /path/to/python \
  --esbmc-bin /path/to/esbmc
```

Optional arguments:

- `--timeout 120s`
- `--unwind 8`
- `--skip-sklearn`
- `--skip-wrapper`
- `--reuse-existing`

## Outputs

The workflow writes its results under:

```text
results/skill_audit/
```

Key outputs include:

- `sklearn_runtime/summary.tsv`
- `wrapper_esbmc/summary.tsv`
- `comparison/comparison.csv`
- `report/summary.json`
- `report/summary.md`
- `report/esbmc_issue_proposal.md`

## Interpretation

Scores are comparative indicators for the tested scenarios only.

They should not be interpreted as:

- a proof of complete correctness of a regressor;
- a full security judgment of Scikit-Learn;
- a definitive ranking of algorithmic quality.

Instead, they help compare verification behavior across controlled artifacts and expose recurring mismatches between formal abstraction and concrete runtime behavior.

## Relationship To ESBMC

This repository is inspired by and intended to be used with ESBMC, the Efficient SMT-Based Context-Bounded Model Checker:

- ESBMC repository: https://github.com/esbmc/esbmc

This project is not an official ESBMC repository. It is a separate open source Skill that uses ESBMC as the core verification engine for the methodology it automates.

## License

This repository is licensed under the Apache License 2.0, following the same open source licensing direction used by the ESBMC project.

See [LICENSE](LICENSE) for details.
