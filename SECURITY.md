# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.x (latest) | ✅ Active |

RealDataAgentBench is pre-1.0 software. Security fixes are applied to the latest
release only.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report security issues privately by emailing:

> venkatamanideep20@gmail.com

Include in your report:
- A description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept (if safe to share)
- Affected version(s)
- Any suggested fix (optional but appreciated)

You can expect an acknowledgement within **48 hours** and a resolution plan
within **7 days**. We will credit researchers who responsibly disclose issues
(unless they prefer to remain anonymous).

## Scope

| Area | In Scope |
|------|----------|
| Code execution / namespace escape (`harness/tools.py`) | ✅ High priority |
| API key handling / environment variable leakage | ✅ High priority |
| Dependency vulnerabilities | ✅ |
| CLI input validation | ✅ |
| GitHub Actions workflows | ✅ |

## API Key Safety

RealDataAgentBench reads API keys exclusively from environment variables (via
`.env` file or shell environment). Keys are **never** hardcoded in source code.

When setting up the project:
1. Copy `.env.example` to `.env`
2. Fill in your keys — **never commit `.env` to version control**
3. The `.gitignore` already excludes `.env` and `*.env`

If you believe an API key has been accidentally committed to this repository,
please report it immediately so it can be revoked.

## Code Execution — Restricted Namespace (NOT a Security Boundary)

The `run_code` tool executes arbitrary Python provided by LLM agents inside a
**restricted namespace**. To be explicit about what this is and is not:

- It runs in-process via `exec()` with a trimmed `__builtins__` allowlist.
- This is **not** a security sandbox. The restriction is trivially escapable —
  e.g. `().__class__.__bases__[0].__subclasses__()` reaches `os`, file handles,
  and the network from pure-Python object traversal without needing any builtin
  or `import` statement. Treat any code passed to `run_code` as code that runs
  with the **full privileges of the host process**.
- There is currently no enforced network, filesystem, CPU, or memory isolation.

**Safe usage:** run the benchmark only against trusted providers, on a machine
where running untrusted Python would be acceptable (e.g. a disposable VM or
container you control). Do **not** point `run_code` at adversarial or unknown
model output without real isolation around the whole process.

**Planned hardening (tracked):** move execution into a subprocess with resource
limits (CPU seconds, memory cap, no network), and ideally a short-lived
container (`--network none --read-only --memory 512m`), matching the approach
SWE-bench-style harnesses use. Until that lands, the wording above is the
accurate description of the threat model.
