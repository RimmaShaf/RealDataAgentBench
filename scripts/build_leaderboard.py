"""Build leaderboard — aggregates all outputs/*.json into docs/results.json.

Multiple runs of the same (task_id, model) pair are aggregated: the
leaderboard reports mean ± 95% CI so score uncertainty is visible.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from realdataagentbench.core.registry import TaskRegistry
from realdataagentbench.harness.pricing import PRICING_AS_OF, compute_cost
from realdataagentbench.harness.providers import resolve_model
from realdataagentbench.scoring.composite import CompositeScorer


def _t95(n: int) -> float:
    """Two-tailed t critical value at 95% CI for df = n-1 (approximation)."""
    if n <= 1:
        return float("nan")
    # Welford-free approximation via lookup; exact enough for n <= 30
    _TABLE = {
        2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776,
        6: 2.571, 7: 2.447, 8: 2.365, 9: 2.306, 10: 2.262,
        11: 2.228, 12: 2.201, 13: 2.179, 14: 2.160, 15: 2.145,
        20: 2.086, 25: 2.060, 30: 2.042,
    }
    # For n > 30 use normal approximation
    if n > 30:
        return 1.960
    # Find closest entry at or above n
    for k in sorted(_TABLE):
        if k >= n:
            return _TABLE[k]
    return 1.960


def _ci(scores: list[float]) -> tuple[float, float, float, float]:
    """Return (mean, std, ci_lower, ci_upper) for a list of scores."""
    n = len(scores)
    mean = sum(scores) / n
    if n == 1:
        return mean, 0.0, mean, mean
    variance = sum((s - mean) ** 2 for s in scores) / (n - 1)
    std = math.sqrt(variance)
    sem = std / math.sqrt(n)
    t = _t95(n)
    return mean, std, max(0.0, mean - t * sem), min(1.0, mean + t * sem)


REAL_DATA_TASK_IDS = {"eda_004", "eda_005", "feat_006", "model_006", "stat_006", "mod_006"}


def _compute(outputs_dir: Path, tasks_dir: Path) -> dict | None:
    """Aggregate ``outputs_dir`` into a leaderboard dict, or ``None`` if empty.

    This is the pure computation shared by :func:`build` (full rebuild) and
    :func:`merge` (splice the current outputs' models into an existing
    ``results.json``). It only ever knows about the models present in
    ``outputs_dir`` — merging preserves every other model untouched.
    """
    registry = TaskRegistry(tasks_dir)
    scorer = CompositeScorer()

    result_files = sorted(outputs_dir.glob("*.json"))
    if not result_files:
        print("No result files found in outputs/")
        return None

    # Collect all valid runs; key = (task_id, model)
    all_runs: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for path in result_files:
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        if data.get("dry_run"):
            continue
        trace = data.get("trace", {})
        if trace.get("error") and not trace.get("final_answer"):
            continue
        task_id = data.get("task_id")
        model = resolve_model(data.get("model", "unknown"))
        if not task_id or task_id not in registry:
            continue
        all_runs[(task_id, model)].append(data)

    # Score every run; aggregate per (task_id, model)
    task_rows = []
    model_scores: dict[str, list[float]] = defaultdict(list)
    model_costs: dict[str, list[float]] = defaultdict(list)

    for (task_id, model), runs in sorted(all_runs.items()):
        task = registry.get(task_id)
        dab_scores, costs = [], []
        subscores = {"correctness": [], "code_quality": [], "efficiency": [], "stat_validity": []}

        for data in runs:
            card = scorer.score(task, data)
            trace = data.get("trace", {})
            inp = trace.get("total_input_tokens", 0)
            out = trace.get("total_output_tokens", 0)
            cost = compute_cost(model, inp, out)
            dab_scores.append(card.dab_score)
            costs.append(cost)
            for dim in subscores:
                subscores[dim].append(getattr(card, dim))

        n = len(dab_scores)
        mean, std, ci_lo, ci_hi = _ci(dab_scores)

        # Latest run metadata for display
        latest = max(runs, key=lambda d: d.get("run_at", ""))
        latest_trace = latest.get("trace", {})

        task_rows.append({
            "task_id": task_id,
            "title": task.title,
            "difficulty": task.difficulty,
            "category": task.category,
            "data_source": "real" if task_id in REAL_DATA_TASK_IDS else "synthetic",
            "model": model,
            "n_runs": n,
            "dab_score": round(mean, 4),
            "dab_score_std": round(std, 4),
            "dab_score_ci_lower": round(ci_lo, 4),
            "dab_score_ci_upper": round(ci_hi, 4),
            "correctness": round(sum(subscores["correctness"]) / n, 4),
            "code_quality": round(sum(subscores["code_quality"]) / n, 4),
            "efficiency": round(sum(subscores["efficiency"]) / n, 4),
            "stat_validity": round(sum(subscores["stat_validity"]) / n, 4),
            "avg_cost_usd": round(sum(costs) / n, 6),
            "total_tokens": latest_trace.get("total_input_tokens", 0) + latest_trace.get("total_output_tokens", 0),
            "num_steps": latest_trace.get("num_steps", 0),
            "run_at": latest.get("run_at", ""),
        })

        model_scores[model].append(mean)
        model_costs[model].extend(costs)

    # Model-level summary with CI across all task-mean scores
    summaries = []
    for model, scores in model_scores.items():
        costs = model_costs[model]
        mean, std, ci_lo, ci_hi = _ci(scores)
        summaries.append({
            "model": model,
            "avg_dab_score": round(mean, 4),
            "dab_score_std": round(std, 4),
            "ci_lower": round(ci_lo, 4),
            "ci_upper": round(ci_hi, 4),
            "avg_cost_usd": round(sum(costs) / len(costs), 6),
            "total_cost_usd": round(sum(costs), 4),
            "tasks_run": len(scores),
            "total_runs": sum(len(v) for k, v in all_runs.items() if k[1] == model),
        })
    summaries.sort(key=lambda x: x["avg_dab_score"], reverse=True)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pricing_as_of": PRICING_AS_OF,
        "total_runs": sum(len(v) for v in all_runs.values()),
        "model_summary": summaries,
        "runs": task_rows,
    }


def _write(output: dict, docs_dir: Path) -> None:
    docs_dir.mkdir(exist_ok=True)
    out_path = docs_dir / "results.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(
        f"Leaderboard written to {out_path} "
        f"({len(output['runs'])} task-model pairs, {output['total_runs']} total runs)"
    )


def build(
    outputs_dir: Path = ROOT / "outputs",
    docs_dir: Path = ROOT / "docs",
    tasks_dir: Path = ROOT / "tasks",
) -> None:
    """Full rebuild: regenerate results.json from every file in ``outputs_dir``."""
    output = _compute(outputs_dir, tasks_dir)
    if output is not None:
        _write(output, docs_dir)


def merge(
    outputs_dir: Path = ROOT / "outputs",
    docs_dir: Path = ROOT / "docs",
    tasks_dir: Path = ROOT / "tasks",
) -> None:
    """Splice the models present in ``outputs_dir`` into the existing results.json.

    Every model NOT present in ``outputs_dir`` is preserved exactly as-is. This is
    the path for an external contributor who only holds their own raw outputs
    (``outputs/*.json`` is gitignored, so a full rebuild would drop other models).
    Idempotent: re-running replaces the contributed model's rows rather than
    duplicating them.
    """
    fresh = _compute(outputs_dir, tasks_dir)
    if fresh is None:
        return

    existing_path = docs_dir / "results.json"
    if not existing_path.exists():
        print("No existing results.json to merge into — doing a full write instead.")
        _write(fresh, docs_dir)
        return

    existing = json.loads(existing_path.read_text())
    new_models = {m["model"] for m in fresh["model_summary"]}

    runs = [r for r in existing.get("runs", []) if r["model"] not in new_models] + fresh["runs"]
    summary = [m for m in existing.get("model_summary", []) if m["model"] not in new_models] + fresh["model_summary"]
    summary.sort(key=lambda x: x["avg_dab_score"], reverse=True)

    merged = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pricing_as_of": existing.get("pricing_as_of", PRICING_AS_OF),
        "total_runs": sum(r["n_runs"] for r in runs),
        "model_summary": summary,
        "runs": runs,
    }
    _write(merged, docs_dir)
    print(f"Merged models: {', '.join(sorted(new_models))}")


if __name__ == "__main__":
    if "--merge" in sys.argv[1:]:
        merge()
    else:
        build()
