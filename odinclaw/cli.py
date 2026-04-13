"""OdinClaw CLI — launch and interact with the governing substrate.

Commands
--------
odinclaw start          Start an interactive session (default data dir: ~/.odinclaw)
odinclaw start --data <path>   Start with a custom data directory
odinclaw status         Print current extension state and exit
odinclaw status --data <path>  Status for a specific data dir
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_DATA_DIR = Path.home() / ".odinclaw"


def _resolve_data_dir(raw: str | None) -> Path:
    d = Path(raw) if raw else _DEFAULT_DATA_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _print_state(state) -> None:
    """Pretty-print the ShellExtensionState."""
    sep = "-" * 52
    lines = [
        "",
        "=" * 52,
        "  OdinClaw Extension State",
        sep,
        f"  startup_ready    : {state.startup_ready}",
        f"  accepting_actions: {state.accepting_actions}",
        f"  degraded_mode    : {state.degraded_mode}",
        sep,
        "  [Burden]",
        f"  level           : {state.burden.level}",
        f"  score           : {state.burden.score}",
        f"  reasons         : {', '.join(state.burden.reasons) or '(none)'}",
        sep,
        "  [Stability]",
        f"  status          : {state.stability.status}",
        f"  signals         : {', '.join(state.stability.signals) or '(none)'}",
        sep,
        "  [Overload]",
        f"  triggered       : {state.overload.triggered}",
        f"  level           : {state.overload.level}",
        f"  concurrent_holds: {state.overload.concurrent_holds} / {state.overload.concurrent_hold_cap}",
        sep,
        "  [Governance]",
        f"  pending_holds   : {state.governance.pending_holds}",
        f"  approvals req'd : {state.governance.approvals_required}",
        sep,
        "  [Memory]",
        f"  durable_records : {state.memory.durable_records}",
        f"  dirty           : {state.memory.dirty}",
        sep,
        "  [Audit]",
        f"  receipts        : {state.audit.receipt_count}",
        f"  continuity_links: {state.audit.continuity_links}",
        sep,
        "  [Trust]",
        f"  blocked_sources : {state.trust.blocked_sources}",
        f"  ambiguous       : {state.trust.ambiguous_sources}",
        f"  active_conflicts: {state.trust.active_conflicts}",
        "=" * 52,
        "",
    ]
    print("\n".join(lines))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> int:
    from odinclaw.shell.hooks import attach_odinclaw_shell

    data_dir = _resolve_data_dir(args.data)
    print(f"[odinclaw] data dir: {data_dir}")

    bridge = attach_odinclaw_shell(data_dir, "cli-status")
    state = bridge.launch()
    _print_state(state)
    bridge.shutdown()
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    from odinclaw.contracts.action_classes import ActionClass
    from odinclaw.contracts.governance import ActionRequest, GovernanceOutcome
    from odinclaw.contracts.provenance import ProvenanceRecord
    from odinclaw.contracts.trust import TrustClass
    from odinclaw.shell.hooks import attach_odinclaw_shell

    data_dir = _resolve_data_dir(args.data)
    session_name = args.session or "cli-session"

    print(f"\n[odinclaw] starting session '{session_name}'")
    print(f"[odinclaw] data dir : {data_dir}")

    bridge = attach_odinclaw_shell(data_dir, session_name)
    state = bridge.launch()
    _print_state(state)

    operator_prov = ProvenanceRecord(
        source_type="operator",
        source_label="cli",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )

    print("OdinClaw session open. Type 'help' for commands, 'quit' to exit.\n")

    while True:
        try:
            raw = input("odinclaw> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue

        if raw in {"quit", "exit", "q"}:
            break

        if raw in {"help", "?"}:
            print(
                "\n"
                "  status          — show current extension state\n"
                "  preflight <cls> — run a governance preflight (action classes:\n"
                "                    NAVIGATION_ONLY, READ_ONLY_EXTERNAL, DESTRUCTIVE_ACTION,\n"
                "                    DURABLE_INTERNAL_STATE_MUTATION, CREDENTIALED_ACTION)\n"
                "  memory          — show memory snapshot\n"
                "  degraded        — enter degraded mode\n"
                "  recover         — exit degraded mode\n"
                "  quit            — shutdown and exit\n"
            )
            continue

        if raw == "status":
            _print_state(bridge.extension_state())
            continue

        if raw == "memory":
            snap = bridge.lifecycle.services.memory_authority.snapshot()
            print(f"  durable records : {len(snap.records)}")
            print(f"  dirty           : {snap.dirty}")
            for rec in list(snap.records)[:10]:
                print(f"  [{rec.kind.value}] {rec.topic}: {rec.content[:60]}")
            continue

        if raw == "degraded":
            r = bridge.lifecycle.enter_degraded_mode(reason="cli-requested")
            print(f"  [repair] entered degraded mode — receipt {r.trace_ids.action_id[:8]}")
            _print_state(bridge.extension_state())
            continue

        if raw == "recover":
            r = bridge.lifecycle.exit_degraded_mode(reason="cli-recovery")
            print(f"  [repair] exited degraded mode — receipt {r.trace_ids.action_id[:8]}")
            _print_state(bridge.extension_state())
            continue

        if raw.startswith("preflight"):
            parts = raw.split()
            cls_name = parts[1].upper() if len(parts) > 1 else "NAVIGATION_ONLY"
            try:
                action_class = ActionClass[cls_name]
            except KeyError:
                print(f"  unknown action class '{cls_name}'")
                print(f"  valid: {', '.join(c.name for c in ActionClass)}")
                continue
            request = ActionRequest(
                action_name=f"cli_{cls_name.lower()}",
                action_class=action_class,
                provenance=operator_prov,
            )
            decision = bridge.preflight_action(request)
            marker = "[ALLOW]" if decision.outcome == GovernanceOutcome.ALLOW else "[HOLD/DENY]"
            print(f"  {marker} outcome : {decision.outcome.value}")
            print(f"    reason  : {decision.reason}")
            if decision.risk_notes:
                print(f"    notes   : {', '.join(decision.risk_notes)}")
            continue

        print(f"  unknown command '{raw}' — type 'help' for commands")

    print("\n[odinclaw] shutting down…")
    shutdown_state = bridge.shutdown()
    print(f"[odinclaw] shutdown complete — receipts: {shutdown_state.audit.receipt_count}")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="odinclaw",
        description="OdinClaw — governed AI substrate CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # start
    p_start = sub.add_parser("start", help="Open an interactive OdinClaw session")
    p_start.add_argument("--data", metavar="PATH", help="Data directory (default: ~/.odinclaw)")
    p_start.add_argument("--session", metavar="NAME", help="Session name (default: cli-session)")

    # status
    p_status = sub.add_parser("status", help="Print extension state and exit")
    p_status.add_argument("--data", metavar="PATH", help="Data directory (default: ~/.odinclaw)")

    args = parser.parse_args(argv)

    if args.command == "start":
        sys.exit(cmd_start(args))
    elif args.command == "status":
        sys.exit(cmd_status(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
