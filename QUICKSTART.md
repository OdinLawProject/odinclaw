# OdinClaw Quick Start

Get OdinClaw running in under 5 minutes.

---

## Prerequisites

- **Python 3.12+** — `python --version` to check
- No other external dependencies required. OdinClaw core is stdlib-only.

---

## 1. Install

### Windows (Command Prompt or PowerShell)

```bat
cd OdinClaw-main
setup.bat
```

### Windows (Git Bash), Linux, or macOS

```bash
cd OdinClaw-main
bash setup.sh
```

### Manual (any platform)

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows Git Bash / Linux / macOS)
source .venv/Scripts/activate   # Windows
# source .venv/bin/activate     # Linux / macOS

# Install with dev dependencies
pip install -e ".[dev]"

# Confirm tests pass
pytest -q
```

Expected output: `79 passed in X.XXs`

---

## 2. Activate the environment

**Windows (Command Prompt):**
```bat
.venv\Scripts\activate
```

**Windows (Git Bash), Linux, macOS:**
```bash
source .venv/Scripts/activate   # Windows Git Bash
source .venv/bin/activate       # Linux / macOS
```

---

## 3. Run OdinClaw

### Check status

```bash
odinclaw status
```

Shows the current extension state: burden, stability, overload, governance, memory, audit, and trust panels.

### Start an interactive session

```bash
odinclaw start
```

Opens a session with the ODIN governing substrate. Available commands inside the session:

| Command | Description |
|---------|-------------|
| `status` | Show current extension state |
| `preflight <CLASS>` | Run a governance preflight check |
| `memory` | Show durable memory snapshot |
| `degraded` | Enter degraded mode (simulates overload) |
| `recover` | Exit degraded mode |
| `help` | Show all commands |
| `quit` | Shutdown and exit |

**Preflight action classes:**
- `NAVIGATION_ONLY` — read-only navigation, always allowed for trusted operators
- `READ_ONLY_EXTERNAL` — read from external source
- `DURABLE_INTERNAL_STATE_MUTATION` — held for approval
- `CREDENTIALED_ACTION` — held for approval
- `DESTRUCTIVE_ACTION` — held for approval (highest scrutiny)

### Custom data directory

```bash
odinclaw start --data /path/to/my/data
odinclaw status --data /path/to/my/data
```

Default data directory: `~/.odinclaw`

---

## 4. Run Tests

```bash
pytest -q
```

Or with coverage:

```bash
pytest -q --cov=odinclaw --cov-report=term-missing
```

---

## 5. What OdinClaw Stores

OdinClaw persists data in the data directory (default `~/.odinclaw`):

| File | Contents |
|------|----------|
| `receipts.jsonl` | Append-only action receipt chain |
| `continuity.jsonl` | Session continuity links across runs |
| `memory.json` | Durable memory authority (canon + provisional) |
| `canon_history.jsonl` | Canon promotion history |

---

## 6. Build Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Shared scaffold (trace IDs, events, receipts, ownership rules) | Complete |
| 1 | Receipt and provenance bridge | Complete |
| 2 | ODIN context engine | Complete |
| 3 | Durable memory authority | Complete |
| 4 | Governance preflight (allow / hold / escalate / deny) | Complete |
| 5 | Trust and immune bridge | Complete |
| 6 | Repair and rollback | Complete |
| 7 | State and burden signals, overload, pacing | Complete |
| 8 | Federation (multi-node) | Planned — after single-node is stable |

---

## 7. Architecture in One Sentence

OdinClaw is a **governing substrate** (ODIN) behind an **interaction shell** (OpenClaw-compatible),
connected through typed contracts — so governance is never bypassed, memory authority is never
split, and every meaningful action leaves a durable receipt.

---

## Troubleshooting

**`odinclaw` command not found:**
Make sure the virtual environment is activated and the package is installed (`pip install -e ".[dev]"`).

**`UnicodeEncodeError` on Windows:**
The CLI uses ASCII-safe output. If you see encoding errors from other parts, set:
```bat
set PYTHONIOENCODING=utf-8
```

**Tests fail on import:**
Run `pip install -e ".[dev]"` again — the editable install may not have registered yet.

**Data directory issues:**
OdinClaw creates the data directory automatically. If you get permission errors, specify a writable path:
```bash
odinclaw start --data C:\Users\YourName\odinclaw-data
```
