"""Child-process entrypoint for the isolated ``run_code`` executor.

Run as ``python -m realdataagentbench.harness._sandbox_worker <df_path> <result_path>``.
The code to execute is read from stdin; the JSON result envelope
``{"output": str, "error": str | None}`` is written to ``result_path``.

This process is short-lived and disposable. Running agent code here (rather than
in-process) means a namespace escape — e.g.
``().__class__.__bases__[0].__subclasses__()`` reaching ``os`` — lands in a
throwaway subprocess that the parent kills on timeout and that cannot corrupt or
read the benchmark driver's memory. It is still NOT a full security sandbox:
without a container there is no network namespace isolation. See SECURITY.md.
"""

from __future__ import annotations

import io
import json
import pickle
import sys
import textwrap
import traceback
from contextlib import redirect_stdout


def _build_namespace(dataframe) -> dict:
    """Construct the restricted namespace with safe libraries pre-injected.

    Kept byte-for-byte equivalent to the legacy in-process executor so that
    isolation does not change any benchmark result.
    """
    import pandas as pd

    namespace = {
        "df": dataframe,
        "pd": pd,
        "__builtins__": {
            "print": print,
            "len": len,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "sorted": sorted,
            "isinstance": isinstance,
            "type": type,
            "repr": repr,
        },
    }

    # Inject safe libraries — available without import statements, matching the
    # SYSTEM_PROMPT contract (np, stats, sklearn pre-imported).
    import numpy as np
    import scipy.stats as stats
    import sklearn
    import sklearn.linear_model  # noqa: F401
    import sklearn.ensemble  # noqa: F401
    import sklearn.preprocessing  # noqa: F401
    import sklearn.metrics  # noqa: F401
    import sklearn.model_selection  # noqa: F401

    namespace["np"] = np
    namespace["stats"] = stats
    namespace["sklearn"] = sklearn
    return namespace


def main() -> None:
    df_path, result_path = sys.argv[1], sys.argv[2]
    code = sys.stdin.read()

    with open(df_path, "rb") as fh:
        dataframe = pickle.load(fh)

    buf = io.StringIO()
    error = None
    try:
        namespace = _build_namespace(dataframe)
        with redirect_stdout(buf):
            exec(textwrap.dedent(code), namespace)  # noqa: S102
    except Exception:
        error = traceback.format_exc()

    with open(result_path, "w") as fh:
        json.dump({"output": buf.getvalue(), "error": error}, fh)


if __name__ == "__main__":
    main()
