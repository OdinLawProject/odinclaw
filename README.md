# OdinClaw

**OdinClaw** is the governed AI substrate for the ODIN architecture — a
constitutional, organismic AI framework where governance is never bypassed,
memory authority is never split, and every meaningful action leaves a durable
receipt.

OdinClaw is designed to be the ODIN governance layer woven into an OpenClaw-compatible
interaction shell. The substrate is complete and tested. Shell integration is the
active work.

The governance and memory substrate runs entirely on **CPU** — no GPU required for
safety, auditing, or state regulation. The model is a swappable consumer inside the
substrate, not the owner of the rules that constrain it.

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
| 6 | Codex of Humanity | Complete |
| 7 | State and burden signals, overload, pacing | Complete |
| 7b | Repair and rollback | Complete |
| 8 | Federation — readiness gate, contract validator, sync safety, node identity | Complete |
| 9 | Shell integration (OpenClaw fork) | Active |
| 10–36 | Full 36-layer organismic architecture | Planned |

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

## Why Not Just Scale Up?

The standard bet in AI development is: *more compute → bigger model → better behavior.*
That bet has paid off for capability. It has not paid off for governance.

When safety rules live inside model weights, the model is the governor and the
governed simultaneously. A jailbreak, prompt injection, or simply a weaker model
removes both the capability and the safety guarantee at the same time.

ODIN's governance substrate runs on **CPU** and enforces constraints *before* the
model sees the request. The model is a consumer, not the owner of its own rules.

| Property | GPU-heavy inference | ODIN architecture-first |
|---|---|---|
| Governance lives | Inside model weights | Separate CPU substrate |
| Safety survives jailbreak? | No | Yes — preflight is pre-model |
| Audit trail | Optional, external | Built-in, HMAC-chained |
| Session memory | Context window | Tiered durable store |
| Model portability | Fixed to training | Any model, swappable |

**→ [Full technical contrast: GPU-Heavy Inference vs Architecture-First on CPU](docs/GPU_vs_ARCHITECTURE.md)**

---

## Research

The theoretical foundation for OdinClaw and the ODIN architecture is documented
in:

- [GPU vs Architecture contrast](docs/GPU_vs_ARCHITECTURE.md) — Technical post
  comparing GPU-heavy inference with architecture-first CPU governance
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
