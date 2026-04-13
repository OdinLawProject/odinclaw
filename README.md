# OdinClaw

**OdinClaw** is the governed AI substrate for the ODIN architecture — a
constitutional, organismic AI framework where governance is never bypassed,
memory authority is never split, and every meaningful action leaves a durable
receipt.

OdinClaw is designed to be the ODIN governance layer woven into an OpenClaw-compatible
interaction shell. The substrate is complete and tested. Shell integration is the
active work.

---

## Architecture

OdinClaw separates two concerns with a strict typed contract boundary:

| Layer | Responsibility |
|-------|----------------|
| **Shell** | Interaction surface, tool execution, plugin host, chat |
| **Substrate** | Governance, durable memory, trust classification, audit receipts, repair, state |

The shell owns the user experience. The substrate owns every decision about
whether an action is allowed to proceed.

### Governance Pipeline (per action)

```
action request
  -> overload check      (is the system too burdened to accept new work?)
  -> preflight           (ALLOW / HOLD / ESCALATE / DENY)
  -> execution           (shell executes only on ALLOW)
  -> receipt             (durable, append-only audit record)
```

### Build Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Shared scaffold — trace IDs, events, receipts, ownership rules | Complete |
| 1 | Receipt and provenance bridge | Complete |
| 2 | ODIN context engine | Complete |
| 3 | Durable memory authority | Complete |
| 4 | Governance preflight — allow / hold / escalate / deny | Complete |
| 5 | Trust and immune bridge | Complete |
| 6 | Repair and rollback | Complete |
| 7 | State and burden signals, overload, pacing | Complete |
| 8 | Shell integration (OpenClaw fork) | Active |
| 9 | Federation (multi-node) | Planned |

---

## Quick Start

### Install

```bash
# Windows (Git Bash)
bash setup.sh

# Windows (Command Prompt)
setup.bat
```

### Run

```bash
# Activate the environment
source .venv/Scripts/activate   # Windows Git Bash
.venv\Scripts\activate          # Windows CMD

# Check substrate state
odinclaw status

# Open interactive session
odinclaw start
```

See [QUICKSTART.md](QUICKSTART.md) for full install and usage documentation.

---

## Project Structure

```
odinclaw/
  cli.py              Entry point -- odinclaw start / status
  contracts/          Typed contracts between shell and substrate
  odin/               ODIN substrate
    context/          Context engine
    governance/       Preflight decision engine
    memory/           Durable memory authority
    trust/            Trust classification and immune bridge
    repair/           Degraded mode, rollback, repair receipts
    state/            Burden signals, overload, pacing
    orchestration/    Lifecycle and service wiring
  shell/              Shell hooks and extension bridge
docs/
  ODIN_WHITEPAPER.md  Formal academic whitepaper
  ODIN_THESIS.md      Full academic thesis
tests/                79 passing tests across all phases
```

---

## Design Principles

- **Law before power.** Constitutional governance is established before any
  capability is granted.
- **Receipts are non-optional.** Every meaningful action produces a durable,
  tamper-evident receipt. No exceptions.
- **Shell and substrate are separated.** The shell cannot bypass governance.
  Governance cannot reach into the shell's execution surface directly.
- **Memory authority is singular.** There is one memory authority. Forks of
  memory state are not permitted.
- **Burden is real.** System state (overload, degraded mode, concurrent holds)
  gates action admission. The substrate is not infinitely available.

---

## Research

The theoretical foundation for OdinClaw and the ODIN architecture is documented
in:

- [ODIN Whitepaper](docs/ODIN_WHITEPAPER.md) — Organismic Intelligence Hypothesis,
  36-layer architecture, formal claims, economic implications
- [ODIN Thesis](docs/ODIN_THESIS.md) — Full academic treatment, 12 chapters,
  bibliography, appendices

**Central claim:** True general intelligence requires governance, memory,
identity continuity, state regulation, developmental staging, and ecological
embeddedness -- not just a powerful model.

---

## License

Apache License 2.0 -- see [LICENSE](LICENSE)
