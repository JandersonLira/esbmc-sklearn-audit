#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


VALIDATION_CATALOG: dict[int, dict[str, str | int]] = {
    1: {"slug": "predict_before_fit", "title": "Predicao antes do treinamento", "phase": "Fase 1", "severity": "Alta", "score": 3},
    2: {"slug": "xy_length_consistency", "title": "Consistencia entre X e y", "phase": "Fase 1", "severity": "Alta", "score": 3},
    3: {"slug": "valid_hyperparameters", "title": "Hiperparametros validos", "phase": "Fase 1", "severity": "Moderada", "score": 2},
    4: {"slug": "fit_predict_types", "title": "Tipagem em fit e predict", "phase": "Fase 2", "severity": "Alta", "score": 3},
    5: {"slug": "feature_consistency", "title": "Consistencia de atributos", "phase": "Fase 2", "severity": "Alta", "score": 3},
    6: {"slug": "none_parameters", "title": "Parametros None", "phase": "Fase 2", "severity": "Moderada", "score": 2},
    7: {"slug": "expected_exceptions", "title": "Tratamento de excecoes", "phase": "Fase 2", "severity": "Moderada", "score": 2},
    8: {"slug": "index_bounds", "title": "Limites de indice", "phase": "Fase 3", "severity": "Critica", "score": 4},
    9: {"slug": "safe_numeric_domain", "title": "Dominio numerico seguro", "phase": "Fase 3", "severity": "Alta", "score": 3},
    10: {"slug": "critical_paths", "title": "Caminhos criticos", "phase": "Fase 3", "severity": "Critica", "score": 4},
    11: {"slug": "reconfigure_after_fit", "title": "Reconfiguracao apos treino", "phase": "Fase 4", "severity": "Moderada", "score": 2},
    12: {"slug": "retrain_dimension_conflict", "title": "Retreinamento com dimensionalidade conflitante", "phase": "Fase 4", "severity": "Alta", "score": 3},
    13: {"slug": "failure_state_propagation", "title": "Propagacao de estado de falha", "phase": "Fase 4", "severity": "Alta", "score": 3},
    14: {"slug": "safe_state_reset", "title": "Reset seguro de estado", "phase": "Fase 4", "severity": "Moderada", "score": 2},
    15: {"slug": "repeated_predict_consistency", "title": "Consistencia entre multiplas predicoes", "phase": "Fase 4", "severity": "Moderada", "score": 2},
    16: {"slug": "preprocessing_chain_contract", "title": "Cadeia de pre-processamento abstrata", "phase": "Fase 4", "severity": "Moderada", "score": 2},
    17: {"slug": "training_counter_monotonicity", "title": "Monotonicidade de contadores de treino", "phase": "Fase 4", "severity": "Baixa", "score": 1},
    18: {"slug": "controlled_fallback_path", "title": "Fallback controlado por caminho", "phase": "Fase 4", "severity": "Alta", "score": 3},
    19: {"slug": "bounded_numeric_accumulation", "title": "Acumulacao numerica com limite", "phase": "Fase 4", "severity": "Moderada", "score": 2},
    20: {"slug": "symbolic_composite_configuration", "title": "Configuracao composta simbolica", "phase": "Fase 4", "severity": "Alta", "score": 3},
}

SEVERITY_ORDER = {"Baixa": 1, "Moderada": 2, "Alta": 3, "Critica": 4}
REGRESSOR_NAMES = {
    "linear_regression": "LinearRegression",
    "ridge": "Ridge",
    "decision_tree_regressor": "DecisionTreeRegressor",
}


@dataclass
class RunRow:
    file: str
    status: str
    exit_code: int
    log: str


@dataclass
class Finding:
    file: str
    regressor: str
    validation_id: int
    validation_title: str
    phase: str
    sklearn_status: str
    wrapper_status: str
    comparison_note: str
    severity: str
    score: int
    rationale: str
    issue_candidate: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ESBMC sklearn audit methodology.")
    parser.add_argument("--root", required=True, help="Root directory of the study workspace.")
    parser.add_argument("--python-bin", default="", help="Python interpreter for sklearn executables.")
    parser.add_argument("--esbmc-bin", default="", help="ESBMC binary.")
    parser.add_argument("--timeout", default="120s", help="ESBMC timeout value.")
    parser.add_argument("--unwind", type=int, default=8, help="ESBMC unwind bound.")
    parser.add_argument("--skip-sklearn", action="store_true", help="Skip sklearn runtime execution.")
    parser.add_argument("--skip-wrapper", action="store_true", help="Skip ESBMC wrapper execution.")
    parser.add_argument("--reuse-existing", action="store_true", help="Reuse existing result summaries when present.")
    return parser.parse_args()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_tsv(path: Path) -> dict[str, RunRow]:
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return {
            row["file"]: RunRow(
                file=row["file"],
                status=row["status"],
                exit_code=int(row["exit_code"]),
                log=row["log"],
            )
            for row in reader
        }


def write_tsv(path: Path, rows: Iterable[RunRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["file", "status", "exit_code", "log"], delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def run_command(command: list[str], log_path: Path) -> int:
    with log_path.open("w", encoding="utf-8") as handle:
        proc = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    return proc.returncode


def status_from_wrapper_log(log_text: str) -> str:
    if "VERIFICATION SUCCESSFUL" in log_text:
        return "SUCCESS"
    if "VERIFICATION FAILED" in log_text:
        return "FAILED"
    lower = log_text.lower()
    if "timed out" in lower or "timeout" in lower:
        return "TIMEOUT"
    if "error:" in lower:
        return "ERROR"
    return "UNKNOWN"


def discover_files(exec_dir: Path) -> list[Path]:
    if not exec_dir.is_dir():
        raise FileNotFoundError(f"Diretorio nao encontrado: {exec_dir}")
    files = sorted(exec_dir.glob("*.py"))
    if not files:
        raise FileNotFoundError(f"Nenhum executavel encontrado em {exec_dir}")
    return files


def detect_python_bin(root: Path, explicit: str) -> str:
    if explicit:
        return explicit
    candidates = [
        root / ".venv-sklearn" / "bin" / "python",
        root / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return sys.executable


def detect_esbmc_bin(root: Path, explicit: str) -> str:
    if explicit:
        return explicit
    candidates = [
        root / ".venv" / "bin" / "esbmc",
    ]
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    detected = shutil_which("esbmc")
    if not detected:
        raise FileNotFoundError("esbmc nao encontrado. Use --esbmc-bin.")
    return detected


def shutil_which(binary: str) -> str:
    from shutil import which

    found = which(binary)
    return found or ""


def run_sklearn_batch(root: Path, python_bin: str, out_dir: Path) -> Path:
    exec_dir = root / "sklearn" / "executaveis"
    log_dir = out_dir / "logs"
    ensure_dir(log_dir)
    rows: list[RunRow] = []
    for file_path in discover_files(exec_dir):
        log_path = log_dir / f"{file_path.stem}.log"
        exit_code = run_command([python_bin, str(file_path)], log_path)
        status = "PASS" if exit_code == 0 else "FAIL"
        rows.append(RunRow(file=file_path.name, status=status, exit_code=exit_code, log=str(log_path)))
    summary_path = out_dir / "summary.tsv"
    write_tsv(summary_path, rows)
    return summary_path


def run_wrapper_batch(root: Path, esbmc_bin: str, timeout: str, unwind: int, out_dir: Path) -> Path:
    exec_dir = root / "wrapper" / "executaveis"
    log_dir = out_dir / "logs"
    ensure_dir(log_dir)
    rows: list[RunRow] = []
    for file_path in discover_files(exec_dir):
        log_path = log_dir / f"{file_path.stem}.log"
        command = [esbmc_bin, str(file_path), "--timeout", timeout, "--unwind", str(unwind)]
        exit_code = run_command(command, log_path)
        status = status_from_wrapper_log(log_path.read_text(encoding="utf-8", errors="replace"))
        rows.append(RunRow(file=file_path.name, status=status, exit_code=exit_code, log=str(log_path)))
    summary_path = out_dir / "summary.tsv"
    write_tsv(summary_path, rows)
    return summary_path


def parse_filename(file_name: str) -> tuple[str, int]:
    stem = file_name.removesuffix(".py")
    match = re.match(r"^(linear_regression|ridge|decision_tree_regressor)_(\d{2})_", stem)
    if not match:
        raise ValueError(f"Nome de arquivo fora do padrao esperado: {file_name}")
    return REGRESSOR_NAMES[match.group(1)], int(match.group(2))


def comparison_note(sklearn_status: str, wrapper_status: str) -> str:
    if sklearn_status == "PASS" and wrapper_status == "SUCCESS":
        return "ambos_ok"
    if sklearn_status != "PASS" and wrapper_status == "SUCCESS":
        return "falha_execucao_sklearn"
    if sklearn_status == "PASS" and wrapper_status != "SUCCESS":
        return "falha_verificacao_wrapper"
    return "falha_ambos"


def stronger_severity(left: str, right: str) -> str:
    return left if SEVERITY_ORDER[left] >= SEVERITY_ORDER[right] else right


def read_log(path_str: str) -> str:
    path = Path(path_str)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def classify_finding(file_name: str, sk: RunRow | None, wr: RunRow | None) -> Finding:
    regressor, validation_id = parse_filename(file_name)
    catalog = VALIDATION_CATALOG[validation_id]
    sk_status = sk.status if sk else "MISSING"
    wr_status = wr.status if wr else "MISSING"
    note = comparison_note(sk_status, wr_status)
    severity = "Baixa"
    score = 0
    rationale = "Sem falha observavel dentro dos limites executados."
    issue_candidate = False
    default_severity = str(catalog["severity"])
    default_score = int(catalog["score"])
    wrapper_log = read_log(wr.log if wr else "")

    if note == "ambos_ok":
        pass
    elif note == "falha_execucao_sklearn":
        severity = stronger_severity(default_severity, "Alta")
        score = SEVERITY_ORDER[severity]
        rationale = "O executavel concreto falhou enquanto o wrapper formal permaneceu consistente."
    elif note == "falha_verificacao_wrapper":
        severity = default_severity
        score = default_score
        rationale = "O wrapper falhou, mas o executavel concreto passou; tratar como divergencia formal/runtime."
        issue_candidate = True
        if validation_id == 19 and re.search(r"nan|inf", wrapper_log, re.IGNORECASE):
            severity = "Moderada"
            score = 2
            rationale = (
                "Divergencia recorrente na validacao 19 com valor simbolico NaN/Infinito no ESBMC; "
                "indica oportunidade de melhoria no frontend Python em vez de falha concreta do sklearn."
            )
        elif wr_status in {"TIMEOUT", "ERROR", "UNKNOWN", "MISSING"}:
            severity = "Baixa"
            score = 1
            rationale = "O wrapper nao produziu uma conclusao verificavel; registrar como obstaculo metodologico."
            issue_candidate = False
    else:
        severity = stronger_severity(default_severity, "Alta")
        score = SEVERITY_ORDER[severity]
        rationale = "A falha aparece tanto no wrapper quanto na execucao concreta; investigar comportamento funcional."

    return Finding(
        file=file_name,
        regressor=regressor,
        validation_id=validation_id,
        validation_title=str(catalog["title"]),
        phase=str(catalog["phase"]),
        sklearn_status=sk_status,
        wrapper_status=wr_status,
        comparison_note=note,
        severity=severity if score else "Nenhuma",
        score=score,
        rationale=rationale,
        issue_candidate=issue_candidate,
    )


def build_findings(sklearn_rows: dict[str, RunRow], wrapper_rows: dict[str, RunRow]) -> list[Finding]:
    files = sorted(set(sklearn_rows) | set(wrapper_rows))
    return [classify_finding(file_name, sklearn_rows.get(file_name), wrapper_rows.get(file_name)) for file_name in files]


def write_comparison_csv(path: Path, findings: list[Finding]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = list(Finding.__dataclass_fields__.keys())
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for finding in findings:
            writer.writerow(asdict(finding))


def aggregate(findings: list[Finding]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = defaultdict(lambda: {"successes": 0, "failures": 0, "score": 0, "divergences": 0})
    for finding in findings:
        row = summary[finding.regressor]
        if finding.comparison_note == "ambos_ok":
            row["successes"] += 1
        else:
            row["failures"] += 1
        if finding.comparison_note == "falha_verificacao_wrapper":
            row["divergences"] += 1
        row["score"] += finding.score
    return dict(summary)


def detect_issue_candidates(findings: list[Finding]) -> list[Finding]:
    return [finding for finding in findings if finding.issue_candidate]


def extract_esbmc_version(findings: list[Finding], wrapper_rows: dict[str, RunRow]) -> str:
    for finding in findings:
        wr = wrapper_rows.get(finding.file)
        if not wr:
            continue
        text = read_log(wr.log)
        match = re.search(r"ESBMC version ([^\n]+)", text)
        if match:
            return match.group(1).strip()
    return "nao identificado"


def extract_solver(findings: list[Finding], wrapper_rows: dict[str, RunRow]) -> str:
    for finding in findings:
        wr = wrapper_rows.get(finding.file)
        if not wr:
            continue
        text = read_log(wr.log)
        match = re.search(r"Solving with solver ([^\n]+)", text)
        if match:
            return match.group(1).strip()
    return "nao identificado"


def build_issue_draft(root: Path, findings: list[Finding], wrapper_rows: dict[str, RunRow], report_dir: Path) -> Path | None:
    candidates = detect_issue_candidates(findings)
    if not candidates:
        return None

    focused = [finding for finding in candidates if finding.validation_id == 19]
    selected = focused if focused else candidates
    selected_files = [finding.file for finding in selected]
    evidence_lines = []
    for finding in selected:
        wr = wrapper_rows.get(finding.file)
        if not wr:
            continue
        text = read_log(wr.log)
        if re.search(r"step_value = .*NAN", text, re.IGNORECASE):
            evidence_lines.append(f"- `{finding.file}`: ESBMC instanciou `step_value` como `-NaN` antes da verificacao principal.")
        else:
            evidence_lines.append(f"- `{finding.file}`: wrapper divergiu do executavel concreto; revisar log `{wr.log}`.")

    issue_body = "\n".join(
        [
            "# Proposed ESBMC Issue",
            "",
            "## Title",
            "",
            "Python frontend: symbolic NaN/infinite values can violate numeric `assume` guards and trigger false positives",
            "",
            "## Summary",
            "",
            "While reproducing the ESBMC Scikit-Learn regression methodology, the concrete sklearn executables passed but the paired ESBMC wrappers failed in the same numeric-accumulation scenario. The counterexamples indicate symbolic floating-point values such as `-NaN` violating numeric assumptions before the intended scenario logic advances.",
            "",
            "## Environment",
            "",
            f"- Workspace: `{root}`",
            f"- ESBMC version: `{extract_esbmc_version(findings, wrapper_rows)}`",
            f"- Solver: `{extract_solver(findings, wrapper_rows)}`",
            "",
            "## Repeated Evidence",
            "",
            *evidence_lines,
            "",
            "## Expected Behavior",
            "",
            "The Python frontend should offer clearer handling for symbolic `NaN` and infinite values in numeric assumptions so that bounded numeric scenarios do not produce misleading false positives when the concrete runtime artifact is consistent.",
            "",
            "## Observed Behavior",
            "",
            "The wrapper fails during the assumption stage, while the equivalent sklearn runtime executable completes successfully.",
            "",
            "## Suggested Improvement",
            "",
            "- Add explicit diagnostics when symbolic floating-point assumptions are violated by `NaN` or infinite values.",
            "- Consider frontend-side guards or modeling support for numeric assumptions involving symbolic floats.",
            "- Document the limitation and include a minimal reproducible Python example.",
            "",
            "## Minimal Reproducer Candidates",
            "",
            *[f"- `{file_name}`" for file_name in selected_files],
        ]
    )
    issue_path = report_dir / "esbmc_issue_proposal.md"
    issue_path.write_text(issue_body + "\n", encoding="utf-8")
    return issue_path


def write_summary(report_dir: Path, findings: list[Finding], aggregate_rows: dict[str, dict[str, int]], issue_path: Path | None) -> tuple[Path, Path]:
    json_path = report_dir / "summary.json"
    md_path = report_dir / "summary.md"
    payload = {
        "findings": [asdict(finding) for finding in findings],
        "aggregate": aggregate_rows,
        "issue_proposal": str(issue_path) if issue_path else "",
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# ESBMC Sklearn Audit Summary",
        "",
        "## Aggregate",
        "",
        "| Regressor | Successes | Failures | Divergences | Score |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for regressor, row in sorted(aggregate_rows.items()):
        lines.append(f"| {regressor} | {row['successes']} | {row['failures']} | {row['divergences']} | {row['score']} |")

    lines.extend(
        [
            "",
            "## Findings",
            "",
            "| File | Validation | Concrete | Wrapper | Note | Severity | Score |",
            "| --- | --- | --- | --- | --- | --- | ---: |",
        ]
    )
    for finding in findings:
        lines.append(
            f"| {finding.file} | {finding.validation_id:02d} - {finding.validation_title} | "
            f"{finding.sklearn_status} | {finding.wrapper_status} | {finding.comparison_note} | "
            f"{finding.severity} | {finding.score} |"
        )

    if issue_path:
        lines.extend(["", "## Issue Proposal", "", f"Saved at `{issue_path}`."])

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def maybe_reuse_or_run(args: argparse.Namespace, root: Path, base_out: Path) -> tuple[Path, Path]:
    sklearn_out = base_out / "sklearn_runtime"
    wrapper_out = base_out / "wrapper_esbmc"
    ensure_dir(sklearn_out)
    ensure_dir(wrapper_out)
    sklearn_summary = sklearn_out / "summary.tsv"
    wrapper_summary = wrapper_out / "summary.tsv"

    if not args.skip_sklearn:
        if not (args.reuse_existing and sklearn_summary.exists()):
            sklearn_summary = run_sklearn_batch(root, detect_python_bin(root, args.python_bin), sklearn_out)
    elif not sklearn_summary.exists():
        raise FileNotFoundError("Resumo sklearn nao encontrado para reuse.")

    if not args.skip_wrapper:
        if not (args.reuse_existing and wrapper_summary.exists()):
            wrapper_summary = run_wrapper_batch(root, detect_esbmc_bin(root, args.esbmc_bin), args.timeout, args.unwind, wrapper_out)
    elif not wrapper_summary.exists():
        raise FileNotFoundError("Resumo wrapper nao encontrado para reuse.")

    return sklearn_summary, wrapper_summary


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    base_out = root / "results" / "skill_audit"
    comparison_dir = base_out / "comparison"
    report_dir = base_out / "report"
    ensure_dir(comparison_dir)
    ensure_dir(report_dir)

    sklearn_summary, wrapper_summary = maybe_reuse_or_run(args, root, base_out)
    sklearn_rows = load_tsv(sklearn_summary)
    wrapper_rows = load_tsv(wrapper_summary)
    findings = build_findings(sklearn_rows, wrapper_rows)
    aggregate_rows = aggregate(findings)

    comparison_csv = comparison_dir / "comparison.csv"
    write_comparison_csv(comparison_csv, findings)
    issue_path = build_issue_draft(root, findings, wrapper_rows, report_dir)
    json_path, md_path = write_summary(report_dir, findings, aggregate_rows, issue_path)

    print(f"Resumo sklearn: {sklearn_summary}")
    print(f"Resumo wrapper: {wrapper_summary}")
    print(f"Comparacao CSV: {comparison_csv}")
    print(f"Resumo JSON: {json_path}")
    print(f"Resumo Markdown: {md_path}")
    if issue_path:
        print(f"Proposta de issue: {issue_path}")


if __name__ == "__main__":
    main()
