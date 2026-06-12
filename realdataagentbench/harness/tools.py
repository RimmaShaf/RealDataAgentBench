"""Tools available to the agent during benchmark execution.

``run_code`` executes model-generated Python in a *restricted namespace*. By
default it runs that code in a short-lived **subprocess** with a wall-clock
timeout and a CPU-seconds limit, so a namespace escape (e.g.
``().__class__.__bases__[0].__subclasses__()`` reaching ``os``) lands in a
disposable child that cannot corrupt or read the benchmark driver's memory and
gets killed if it runs away. This is process isolation, NOT a full security
sandbox: without a container there is no network isolation. For untrusted models
run the whole benchmark inside a container (``--network none``). See SECURITY.md.

Set ``RDAB_SANDBOX=inprocess`` to fall back to the legacy in-process executor
(faster, no per-call subprocess startup) for local runs against trusted
providers — explicitly opting out of isolation.
"""

from __future__ import annotations

import io
import json
import os
import pickle
import subprocess
import sys
import tempfile
import textwrap
import traceback
from contextlib import redirect_stdout

import pandas as pd

# Resource limits for the isolated executor. Overridable via env for CI/local.
_WALL_TIMEOUT_S = float(os.environ.get("RDAB_SANDBOX_TIMEOUT", "60"))
_CPU_SECONDS = int(os.environ.get("RDAB_SANDBOX_CPU", "60"))
# Invoke the worker by file path (not ``-m``) so the child imports only
# pandas/numpy/sklearn — running ``-m`` would trigger harness/__init__.py and
# pull in the providers/runner (API clients) the child has no need for.
_WORKER_PATH = os.path.join(os.path.dirname(__file__), "_sandbox_worker.py")


def _cpu_limit_preexec(cpu_seconds: int):
    """Return a preexec_fn that caps child CPU time (POSIX only)."""
    def _set_limits():  # pragma: no cover - runs in the forked child
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))

    return _set_limits


def _run_code_inprocess(code: str, dataframe: pd.DataFrame) -> dict:
    """Legacy in-process executor (no isolation). Used only when opted in."""
    from realdataagentbench.harness._sandbox_worker import _build_namespace

    namespace = _build_namespace(dataframe)
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            exec(textwrap.dedent(code), namespace)  # noqa: S102
        return {"output": buf.getvalue(), "error": None}
    except Exception:
        return {"output": buf.getvalue(), "error": traceback.format_exc()}


def run_code(code: str, dataframe: pd.DataFrame) -> dict:
    """Execute agent Python against ``df``; return ``{"output", "error"}``.

    Runs in an isolated subprocess by default (see module docstring). The
    restricted namespace is *not* a security boundary on its own — isolation
    comes from the separate process + resource limits.
    """
    if os.environ.get("RDAB_SANDBOX") == "inprocess":
        return _run_code_inprocess(code, dataframe)

    # Hand the dataframe and a result slot to the child via temp files so that
    # the child's stdout (where agent print() output goes) never collides with
    # the JSON envelope we read back.
    tmpdir = tempfile.mkdtemp(prefix="rdab_sandbox_")
    df_path = os.path.join(tmpdir, "df.pkl")
    result_path = os.path.join(tmpdir, "result.json")
    try:
        with open(df_path, "wb") as fh:
            pickle.dump(dataframe, fh, protocol=pickle.HIGHEST_PROTOCOL)

        preexec = _cpu_limit_preexec(_CPU_SECONDS) if os.name == "posix" else None
        try:
            proc = subprocess.run(
                [sys.executable, _WORKER_PATH, df_path, result_path],
                input=code,
                capture_output=True,
                text=True,
                timeout=_WALL_TIMEOUT_S,
                preexec_fn=preexec,
            )
        except subprocess.TimeoutExpired:
            return {
                "output": "",
                "error": f"Execution exceeded the {_WALL_TIMEOUT_S:.0f}s wall-clock limit and was terminated.",
            }

        if os.path.exists(result_path):
            with open(result_path) as fh:
                return json.load(fh)

        # No result file → the child died before writing (CPU limit, OOM, crash).
        detail = proc.stderr.strip() or f"exit code {proc.returncode}"
        return {
            "output": "",
            "error": f"Execution was terminated before completing ({detail}).",
        }
    finally:
        for path in (df_path, result_path):
            try:
                os.remove(path)
            except OSError:
                pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass


def get_dataframe_info(dataframe: pd.DataFrame) -> dict:
    """Return shape, dtypes, missing counts, and head(3) as a dict."""
    return {
        "shape": list(dataframe.shape),
        "columns": list(dataframe.columns),
        "dtypes": {col: str(dtype) for col, dtype in dataframe.dtypes.items()},
        "missing_counts": dataframe.isnull().sum().to_dict(),
        "missing_rates": (dataframe.isnull().mean().round(4)).to_dict(),
        "head": dataframe.head(3).to_dict(orient="records"),
    }


def get_column_stats(column_name: str, dataframe: pd.DataFrame) -> dict:
    """Return descriptive statistics for a single column."""
    if column_name not in dataframe.columns:
        return {"error": f"Column {column_name!r} not found. Available: {list(dataframe.columns)}"}
    col = dataframe[column_name].dropna()
    if pd.api.types.is_numeric_dtype(col):
        import numpy as np
        from scipy.stats import skew, kurtosis
        return {
            "column": column_name,
            "dtype": str(dataframe[column_name].dtype),
            "count": int(col.count()),
            "missing": int(dataframe[column_name].isnull().sum()),
            "mean": float(col.mean()),
            "median": float(col.median()),
            "std": float(col.std()),
            "min": float(col.min()),
            "max": float(col.max()),
            "q1": float(col.quantile(0.25)),
            "q3": float(col.quantile(0.75)),
            "skewness": float(skew(col)),
            "kurtosis": float(kurtosis(col)),
        }
    else:
        return {
            "column": column_name,
            "dtype": str(dataframe[column_name].dtype),
            "count": int(col.count()),
            "missing": int(dataframe[column_name].isnull().sum()),
            "unique": int(col.nunique()),
            "top_values": {str(k): int(v) for k, v in col.value_counts().head(5).items()},
        }


# Anthropic tool-use definitions
TOOL_DEFINITIONS = [
    {
        "name": "run_code",
        "description": (
            "Execute Python code against the task dataframe `df`. "
            "numpy (np), pandas (pd), and scipy.stats (stats) are pre-imported. "
            "Use print() to produce output. Returns stdout and any error."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Valid Python code. Use print() for output.",
                }
            },
            "required": ["code"],
        },
    },
    {
        "name": "get_dataframe_info",
        "description": "Return shape, dtypes, missing value counts and rates, and the first 3 rows.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_column_stats",
        "description": "Return descriptive statistics for a single column (mean, std, skewness, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "column_name": {
                    "type": "string",
                    "description": "Name of the column to analyse.",
                }
            },
            "required": ["column_name"],
        },
    },
]
