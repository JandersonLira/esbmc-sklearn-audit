# Methodology Notes

## Objective

Compare formal ESBMC verification results against concrete sklearn runtime behavior for Scikit-Learn regression artifacts in controlled scenarios.

## Reference Workflow

1. Select the regressors to test.
2. Keep the fixed validation catalog of 20 scenarios.
3. Pair each concrete sklearn executable with one abstract ESBMC wrapper sharing the same filename stem.
4. Run the concrete sklearn batch first.
5. Run the ESBMC wrapper batch second.
6. Consolidate the results file-by-file.
7. Score only observed failures.
8. Aggregate the score by regressor.
9. Draft an ESBMC issue when repeated divergences suggest a frontend or modeling gap.

## Severity Dimensions

- `Impacto potencial`: quanto a falha compromete confiabilidade, corretude ou seguranca
- `Facilidade de ativacao`: quao facil e reproduzir a falha em uso plausivel
- `Reprodutibilidade`: quao sistematica e a ocorrencia no cenario modelado
- `Abrangencia no fluxo de uso`: em que ponto do ciclo de uso a falha compromete o artefato

## Interpretation Guardrails

- Do not present the final score as a proof of absolute safety.
- Do not claim intrinsic superiority of a regressor unless the scored evidence clearly differentiates them.
- Treat concentrated formal/runtime divergences as evidence for methodology or tooling improvement, not immediately as concrete sklearn defects.
- Repeated `wrapper FAILED` plus `sklearn PASS` in the same validation family is strong issue-candidate evidence for ESBMC.
