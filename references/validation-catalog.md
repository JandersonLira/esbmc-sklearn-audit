# Validation Catalog

Use this file when you need the exact semantic meaning of each validation, its phase in the workflow, and the default severity recommendation used by the bundled runner.

## Severity Scale

- `Baixa` = 1
- `Moderada` = 2
- `Alta` = 3
- `Critica` = 4

## Catalog

| ID | Suffix | Phase | Property | Default severity if violated |
| --- | --- | --- | --- | --- |
| 01 | `predict_before_fit` | Fase 1 | Impedir `predict` antes de `fit` | Alta |
| 02 | `xy_length_consistency` | Fase 1 | Consistencia entre `X` e `y` | Alta |
| 03 | `valid_hyperparameters` | Fase 1 | Hiperparametros validos | Moderada |
| 04 | `fit_predict_types` | Fase 2 | Tipagem em `fit` e `predict` | Alta |
| 05 | `feature_consistency` | Fase 2 | Consistencia de atributos entre treino e predicao | Alta |
| 06 | `none_parameters` | Fase 2 | Tratamento seguro de `None` | Moderada |
| 07 | `expected_exceptions` | Fase 2 | Tratamento coerente de excecoes | Moderada |
| 08 | `index_bounds` | Fase 3 | Limites de indice | Critica |
| 09 | `safe_numeric_domain` | Fase 3 | Dominio numerico seguro | Alta |
| 10 | `critical_paths` | Fase 3 | Preservacao de caminhos criticos e assertivas | Critica |
| 11 | `reconfigure_after_fit` | Fase 4 | Reconfiguracao apos treino | Moderada |
| 12 | `retrain_dimension_conflict` | Fase 4 | Retreinamento com dimensionalidade conflitante | Alta |
| 13 | `failure_state_propagation` | Fase 4 | Propagacao de estado de falha | Alta |
| 14 | `safe_state_reset` | Fase 4 | Reset seguro de estado | Moderada |
| 15 | `repeated_predict_consistency` | Fase 4 | Consistencia entre multiplas predicoes | Moderada |
| 16 | `preprocessing_chain_contract` | Fase 4 | Cadeia abstrata de pre-processamento | Moderada |
| 17 | `training_counter_monotonicity` | Fase 4 | Monotonicidade de contadores de treino | Baixa |
| 18 | `controlled_fallback_path` | Fase 4 | Fallback controlado por caminho | Alta |
| 19 | `bounded_numeric_accumulation` | Fase 4 | Acumulacao numerica com limite | Moderada |
| 20 | `symbolic_composite_configuration` | Fase 4 | Configuracao composta simbolica | Alta |

## Interpretation Notes

- The default severity is a reproducible starting point for the study workflow.
- Raise the severity when the log shows broader impact than the catalog implies.
- Lower the severity only when you can justify that the observed failure is a narrow modeling artifact with limited practical impact.
- The article's reference outcome assigns score `2` to validation `19` for all three regressors because the divergence appears to stem from symbolic `NaN` handling in ESBMC rather than a concrete sklearn runtime fault.
