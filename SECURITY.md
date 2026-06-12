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

- The agent code runs inside a `exec()` namespace with a trimmed
  `__builtins__` allowlist. That namespace restriction is **not** a security
  boundary on its own: it is trivially escapable — e.g.
  `().__class__.__bases__[0].__subclasses__()` reaches `os`, file handles, and
  the network from pure-Python object traversal without needing any builtin or
  `import` statement.
- **Isolation comes from the process, not the namespace.** By default
  `run_code` executes that code in a short-lived **subprocess** with a
  wall-clock timeout and a CPU-seconds `RLIMIT_CPU` cap (POSIX). A namespace
  escape therefore lands in a disposable child that the parent kills on timeout
  and that cannot read or corrupt the benchmark driver's memory. Limits are
  configurable via `RDAB_SANDBOX_TIMEOUT` and `RDAB_SANDBOX_CPU`.
- **What is still NOT enforced:** network and filesystem isolation, and a hard
  memory cap. The subprocess can still open sockets and read/write files with
  the privileges of the user running the benchmark.
- Setting `RDAB_SANDBOX=inprocess` opts out of the subprocess and runs agent
  code in the driver process — faster, but with no isolation. Use only for
  local runs against trusted providers.

**Safe usage for untrusted models:** run the whole benchmark inside a container
with no network and a read-only filesystem, e.g.
`docker run --rm --network none --read-only --memory 512m ...`. This is the only
configuration that closes the network/filesystem/memory gaps above, and is the
approach SWE-bench-style harnesses use. The built-in subprocess isolation raises
the bar against runaway and memory-corruption, but is not a substitute for a
container when running adversarial or unknown model output.
