"""
ODIN CLI — Governed AI substrate interface.
Norse-themed, Rich-rendered, fully wired to the governance substrate.

Entry point: odinclaw start | odinclaw status | odinclaw chat
"""

from __future__ import annotations

import sys
import os
import io
import json
import subprocess
import traceback
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

# Force UTF-8 on Windows before Rich loads
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Rich UI ────────────────────────────────────────────────────────────────
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.rule import Rule
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich import box

console = Console(highlight=False)

from odinclaw.config import get as _cfg

_DEFAULT_DATA_DIR = Path(os.environ.get("ODIN_DATA_DIR") or _cfg("data_dir", str(Path.home() / ".odinclaw")))
_SESSION_LOG_DIR  = _DEFAULT_DATA_DIR / "sessions"
_MODEL_DEFAULT    = os.environ.get("ODIN_MODEL")       or _cfg("model",    "qwen2.5:7b-instruct-q8_0")
_OLLAMA_BASE      = os.environ.get("ODIN_OLLAMA_BASE") or _cfg("api_base", "http://localhost:11434")

# ── Norse Banner ────────────────────────────────────────────────────────────

BANNER = r"""
   ___  ___  ___ ___  __
  / _ \|   \|_ _| _ \/ /
 | (_) | |) || ||  _/ _ \
  \___/|___/|___|_|/_/ \_\
"""

RUNE_DIVIDER = "- = [ ODIN GOVERNANCE SUBSTRATE ] = -"

SLASH_COMMANDS = {
    "/help":               "Show this command reference",
    "/status":             "Show full substrate state (governance, memory, trust, audit)",
    "/receipts [n]":       "Show last n receipts from the audit chain (default 10)",
    "/memory [topic]":     "Show durable memory records, optionally filtered by topic",
    "/holds":              "Show pending governance holds awaiting approval",
    "/approve <id>":       "Approve a held action by approval ID",
    "/deny <id>":          "Deny a held action by approval ID",
    "/preflight <class>":  "Run a governance preflight on an action class",
    "/trust <source>":     "Check trust classification for a source label",
    "/degraded":           "Enter degraded mode (reduced capability, repair state)",
    "/recover":            "Exit degraded mode and resume normal operation",
    "/session":            "Show current session ID, run ID, and continuity links",
    "/clear":              "Clear conversation history (substrate state preserved)",
    "/model [name]":       "Show or switch the active Ollama model",
    "/quit":               "Shutdown cleanly and exit",
}

ACTION_CLASSES = [
    "READ_ONLY_LOCAL",
    "READ_ONLY_EXTERNAL",
    "NAVIGATION_ONLY",
    "NON_DESTRUCTIVE_TOOL_USE",
    "DURABLE_INTERNAL_STATE_MUTATION",
    "EXTERNAL_STATE_MUTATION",
    "CREDENTIALED_ACTION",
    "DESTRUCTIVE_ACTION",
]

# ── UI Helpers ──────────────────────────────────────────────────────────────

def _banner() -> None:
    console.print(Text(BANNER, style="bold cyan"), justify="center")
    console.print(Text(RUNE_DIVIDER, style="dim cyan"), justify="center")
    console.print()


def _print_help() -> None:
    table = Table(
        title="⚡ ODIN Commands",
        border_style="cyan",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Command", style="bold green", min_width=24)
    table.add_column("Description", style="white")
    for cmd, desc in SLASH_COMMANDS.items():
        table.add_row(cmd, desc)
    console.print(table)
    console.print()
    console.print(Panel(
        "[dim]Any other input is sent to the ODIN model as a governed chat message.[/dim]\n"
        "[dim]Every action passes through governance preflight. HOLD actions require /approve.[/dim]",
        border_style="dim cyan",
        box=box.SIMPLE,
    ))


def _outcome_style(outcome_val: str) -> str:
    return {
        "allow":    "bold green",
        "hold":     "bold yellow",
        "deny":     "bold red",
        "escalate": "bold magenta",
    }.get(outcome_val.lower(), "white")


def _print_decision(decision) -> None:
    style = _outcome_style(decision.outcome.value)
    icon  = {"allow": "✓", "hold": "⚠", "deny": "✗", "escalate": "↑"}.get(
        decision.outcome.value.lower(), "?"
    )
    console.print(Panel(
        f"[{style}]{icon}  {decision.outcome.value.upper()}[/{style}]\n"
        f"[dim]reason:[/dim] {decision.reason}" +
        (f"\n[dim]notes:[/dim]  {', '.join(decision.risk_notes)}" if decision.risk_notes else ""),
        title="[bold]Governance Decision[/bold]",
        border_style=style.split()[-1],
        box=box.ROUNDED,
    ))


def _print_state(state) -> None:
    b = state.burden
    s = state.stability
    o = state.overload
    g = state.governance
    m = state.memory
    a = state.audit
    t = state.trust

    # Stability colour
    stab_colour = "green" if s.status == "stable" else ("yellow" if s.status == "degraded" else "red")

    burden_table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    burden_table.add_column("k", style="dim", width=20)
    burden_table.add_column("v", style="white")
    burden_table.add_row("level",   b.level)
    burden_table.add_row("score",   str(b.score))
    burden_table.add_row("reasons", ", ".join(b.reasons) or "(none)")

    gov_table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    gov_table.add_column("k", style="dim", width=20)
    gov_table.add_column("v", style="white")
    gov_table.add_row("pending holds",    str(g.pending_holds))
    gov_table.add_row("approvals req'd",  str(g.approvals_required))

    mem_table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    mem_table.add_column("k", style="dim", width=20)
    mem_table.add_column("v", style="white")
    mem_table.add_row("durable records", str(m.durable_records))
    mem_table.add_row("dirty",           str(m.dirty))

    audit_table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    audit_table.add_column("k", style="dim", width=20)
    audit_table.add_column("v", style="white")
    audit_table.add_row("receipts",         str(a.receipt_count))
    audit_table.add_row("continuity links", str(a.continuity_links))

    trust_table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    trust_table.add_column("k", style="dim", width=20)
    trust_table.add_column("v", style="white")
    trust_table.add_row("blocked sources", str(t.blocked_sources))
    trust_table.add_row("ambiguous",       str(t.ambiguous_sources))
    trust_table.add_row("active conflicts",str(t.active_conflicts))

    console.print()
    console.print(Rule("[bold cyan]⚡ ODIN Substrate State[/bold cyan]", style="cyan"))

    # Top row: stability + overload
    stab_panel = Panel(
        f"[{stab_colour}]{s.status.upper()}[/{stab_colour}]\n"
        f"[dim]signals:[/dim] {', '.join(s.signals) or '(none)'}",
        title="[bold]Stability[/bold]",
        border_style=stab_colour,
        box=box.ROUNDED,
    )
    overload_colour = "red" if o.triggered else "green"
    overload_panel = Panel(
        f"[{overload_colour}]{'TRIGGERED' if o.triggered else 'NORMAL'}[/{overload_colour}]\n"
        f"[dim]level:[/dim] {o.level}\n"
        f"[dim]holds:[/dim] {o.concurrent_holds} / {o.concurrent_hold_cap}",
        title="[bold]Overload[/bold]",
        border_style=overload_colour,
        box=box.ROUNDED,
    )
    mode_colour = "yellow" if state.degraded_mode else "green"
    mode_panel = Panel(
        f"[{mode_colour}]{'DEGRADED' if state.degraded_mode else 'NORMAL'}[/{mode_colour}]\n"
        f"[dim]accepting:[/dim] {'yes' if state.accepting_actions else 'no'}\n"
        f"[dim]ready:[/dim]     {'yes' if state.startup_ready else 'no'}",
        title="[bold]Mode[/bold]",
        border_style=mode_colour,
        box=box.ROUNDED,
    )
    console.print(Columns([stab_panel, overload_panel, mode_panel], equal=True))

    # Bottom row: subsystem panels
    console.print(Columns([
        Panel(burden_table, title="[bold]Burden[/bold]",     border_style="yellow", box=box.ROUNDED),
        Panel(gov_table,    title="[bold]Governance[/bold]", border_style="blue",   box=box.ROUNDED),
        Panel(mem_table,    title="[bold]Memory[/bold]",     border_style="magenta",box=box.ROUNDED),
        Panel(audit_table,  title="[bold]Audit[/bold]",      border_style="green",  box=box.ROUNDED),
        Panel(trust_table,  title="[bold]Trust[/bold]",      border_style="cyan",   box=box.ROUNDED),
    ], equal=True))
    console.print()


def _print_receipts(bridge, n: int = 10) -> None:
    try:
        receipts = list(bridge.lifecycle.services.receipt_chain.iter_receipts())[-n:]
    except Exception as e:
        console.print(f"[red]Could not read receipts: {e}[/red]")
        return

    if not receipts:
        console.print("[dim]No receipts yet.[/dim]")
        return

    table = Table(
        title=f"⚡ Last {len(receipts)} Receipts",
        border_style="green",
        box=box.ROUNDED,
        show_lines=False,
    )
    table.add_column("ID",      style="dim",        width=10)
    table.add_column("Type",    style="cyan",        width=22)
    table.add_column("Action",  style="white",       width=28)
    table.add_column("Source",  style="dim",         width=16)
    table.add_column("At",      style="dim",         width=20)

    for r in receipts:
        short_id = r.receipt_id[:8] if r.receipt_id else "?"
        source   = r.provenance.source_label if r.provenance else "?"
        ts       = str(r.created_at)[:19] if r.created_at else "?"
        table.add_row(short_id, r.receipt_type, r.action_name, source, ts)

    console.print(table)


def _print_memory(bridge, topic: str | None = None) -> None:
    try:
        snap = bridge.lifecycle.services.memory_authority.snapshot()
    except Exception as e:
        console.print(f"[red]Could not read memory: {e}[/red]")
        return

    records = snap.records
    if topic:
        low = topic.lower()
        records = tuple(r for r in records if low in r.topic.lower() or low in r.content.lower())

    if not records:
        console.print(f"[dim]No memory records{' for topic: ' + topic if topic else ''}.[/dim]")
        return

    table = Table(
        title=f"⚡ Memory ({len(records)} records{' — ' + topic if topic else ''})",
        border_style="magenta",
        box=box.ROUNDED,
    )
    table.add_column("Tier",    style="bold",  width=12)
    table.add_column("Kind",    style="cyan",  width=14)
    table.add_column("Topic",   style="white", width=24)
    table.add_column("Content", style="dim",   width=44)

    tier_styles = {"canon": "green", "provisional": "yellow", "conflict": "red"}
    for r in records[:40]:
        tier_s = tier_styles.get(r.tier.value, "white")
        table.add_row(
            f"[{tier_s}]{r.tier.value}[/{tier_s}]",
            r.kind.value,
            r.topic[:24],
            r.content[:44],
        )

    console.print(table)
    console.print(f"[dim]dirty: {snap.dirty}[/dim]")


def _print_holds(bridge) -> None:
    try:
        approvals = bridge.lifecycle.services.approvals._requests
    except Exception as e:
        console.print(f"[red]Could not read approval store: {e}[/red]")
        return

    pending = {aid: req for aid, req in approvals.items()
               if req.status.value == "pending"}

    if not pending:
        console.print("[dim green]No pending holds.[/dim green]")
        return

    table = Table(
        title=f"⚠  {len(pending)} Pending Hold(s)",
        border_style="yellow",
        box=box.ROUNDED,
    )
    table.add_column("Approval ID", style="dim",   width=14)
    table.add_column("Subject",     style="cyan",  width=16)
    table.add_column("Action",      style="white", width=24)
    table.add_column("Reason",      style="dim",   width=30)
    table.add_column("Requested By",style="dim",   width=16)

    for aid, req in pending.items():
        table.add_row(
            aid[:12],
            req.subject_type,
            req.requested_action,
            req.reason[:30],
            req.requested_by.source_label if req.requested_by else "?",
        )

    console.print(table)
    console.print("[dim]Use /approve <id> or /deny <id> with the full approval ID.[/dim]")


def _print_session(bridge, runtime) -> None:
    console.print(Panel(
        f"[bold]Session ID:[/bold]  {runtime.session_id}\n"
        f"[bold]Run ID:[/bold]      {runtime.current_run.run_id}\n"
        f"[bold]Session Name:[/bold] {runtime.session_name}\n"
        f"[bold]Phase:[/bold]       {runtime.current_run.phase.value}\n"
        f"[bold]Actions:[/bold]     {len(runtime.actions)}",
        title="[bold cyan]⚡ Session[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
    ))


# ── Ollama Chat ─────────────────────────────────────────────────────────────

ODIN_SYSTEM = """\
You are ODIN, a governed local AI assistant. You run entirely locally.
Every action you take passes through the ODIN governance substrate before execution.
Destructive, credentialed, or external-mutation actions require operator approval.
You are not the governance layer — you operate inside it.
Prefer safe, reversible, explainable operations.
When you intend to run code, describe what it will do before proposing it.
"""


def _stream_ollama(messages: list[dict], model: str) -> str:
    """Stream from Ollama and return full response text."""
    try:
        import ollama
        client = ollama.Client(host=_OLLAMA_BASE)
        full = ""
        console.print()
        console.print("[bold cyan]ODIN[/bold cyan] ", end="")

        for chunk in client.chat(model=model, messages=messages, stream=True):
            delta = chunk.message.content or ""
            full += delta
            console.print(delta, end="", highlight=False)

        console.print()  # newline after stream
        return full

    except ImportError:
        console.print("[red]ollama package not installed. Run: pip install ollama[/red]")
        return ""
    except Exception as e:
        console.print(f"\n[red]Ollama error: {e}[/red]")
        console.print("[dim]Is Ollama running? Try: ollama serve[/dim]")
        return ""


def _govern_message(user_input: str, bridge) -> bool:
    """
    Run governance preflight on the user message.
    Returns True if the action is allowed to proceed.
    Prints the decision if it is not ALLOW.
    """
    from odinclaw.contracts.action_classes import ActionClass
    from odinclaw.contracts.governance import ActionRequest, GovernanceOutcome
    from odinclaw.contracts.provenance import ProvenanceRecord
    from odinclaw.contracts.trust import TrustClass

    # Classify the message content
    lower = user_input.lower()
    if any(w in lower for w in ("delete", "remove", "destroy", "wipe", "rm ", "format")):
        action_class = ActionClass.DESTRUCTIVE_ACTION
    elif any(w in lower for w in ("password", "token", "secret", "credential", "api key")):
        action_class = ActionClass.CREDENTIALED_ACTION
    elif any(w in lower for w in ("post", "submit", "upload", "send", "publish")):
        action_class = ActionClass.EXTERNAL_STATE_MUTATION
    elif any(w in lower for w in ("remember", "save", "store", "write to memory")):
        action_class = ActionClass.DURABLE_INTERNAL_STATE_MUTATION
    elif any(w in lower for w in ("http", "browse", "fetch", "navigate", "open url")):
        action_class = ActionClass.NAVIGATION_ONLY
    else:
        action_class = ActionClass.READ_ONLY_LOCAL

    request = ActionRequest(
        action_name="chat_message",
        action_class=action_class,
        provenance=ProvenanceRecord(
            source_type="user",
            source_label="cli-operator",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        payload={"content": user_input[:120]},
    )

    try:
        decision = bridge.preflight_action(request)
    except Exception as e:
        console.print(f"[yellow]⚠ Governance check failed ({e}), proceeding with caution.[/yellow]")
        return True

    if decision.outcome.value == "allow":
        return True

    _print_decision(decision)

    # Keep tray badge in sync after any hold/deny
    try:
        from odinclaw.tray import write_tray_state
        write_tray_state(bridge.extension_state())
    except Exception:
        pass

    if decision.outcome.value == "hold":
        go = Prompt.ask(
            "  [yellow]Proceed anyway?[/yellow]",
            choices=["y", "n"],
            default="n",
        )
        return go == "y"

    return False  # deny or escalate


# ── Command Handlers ────────────────────────────────────────────────────────

def _handle_approve(arg: str, bridge, runtime) -> None:
    if not arg:
        console.print("[red]Usage: /approve <approval_id>[/red]")
        return
    from odinclaw.contracts.provenance import ProvenanceRecord
    from odinclaw.contracts.trust import TrustClass
    approver = ProvenanceRecord(
        source_type="operator",
        source_label="cli-operator",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    try:
        result = bridge.approve_canon_promotion(
            approval_id=arg.strip(),
            approver=approver,
        )
        console.print(f"[green]✓ Approved:[/green] {result.memory_id}")
    except Exception as e:
        # Try raw approval store for non-memory holds
        try:
            bridge.lifecycle.services.approvals.approve(arg.strip())
            console.print(f"[green]✓ Approved:[/green] {arg.strip()[:16]}")
        except Exception as e2:
            console.print(f"[red]Approval failed: {e2}[/red]")


def _handle_deny(arg: str, bridge, runtime) -> None:
    if not arg:
        console.print("[red]Usage: /deny <approval_id>[/red]")
        return
    from odinclaw.contracts.provenance import ProvenanceRecord
    from odinclaw.contracts.trust import TrustClass
    rejector = ProvenanceRecord(
        source_type="operator",
        source_label="cli-operator",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    try:
        bridge.lifecycle.services.approvals.reject(arg.strip())
        console.print(f"[red]✗ Denied:[/red] {arg.strip()[:16]}")
    except Exception as e:
        console.print(f"[red]Denial failed: {e}[/red]")


def _handle_preflight(arg: str, bridge) -> None:
    from odinclaw.contracts.action_classes import ActionClass
    from odinclaw.contracts.governance import ActionRequest
    from odinclaw.contracts.provenance import ProvenanceRecord
    from odinclaw.contracts.trust import TrustClass

    cls_name = arg.upper().strip() if arg else ""
    if not cls_name:
        console.print(f"[dim]Valid classes: {', '.join(ACTION_CLASSES)}[/dim]")
        return

    try:
        action_class = ActionClass[cls_name]
    except KeyError:
        console.print(f"[red]Unknown class '{cls_name}'[/red]")
        console.print(f"[dim]Valid: {', '.join(ACTION_CLASSES)}[/dim]")
        return

    request = ActionRequest(
        action_name=f"manual_{cls_name.lower()}",
        action_class=action_class,
        provenance=ProvenanceRecord(
            source_type="operator",
            source_label="cli-operator",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
    )
    decision = bridge.preflight_action(request)
    _print_decision(decision)


def _handle_trust(arg: str, bridge) -> None:
    from odinclaw.contracts.trust import TrustClass
    from odinclaw.odin.trust.classification import classify_source

    source = arg.strip() if arg else "unknown"
    try:
        trust_class = classify_source(source)
    except Exception:
        trust_class = None

    # Check conflict store for this source
    conflicts = 0
    try:
        store = bridge.lifecycle.services.conflict_store
        conflicts = sum(1 for _ in store.iter_conflicts() if source in str(_))
    except Exception:
        pass

    colour = {
        "trusted_self": "green",
        "trusted_operator": "green",
        "trusted_internal_knowledge": "green",
        "ambiguous_external": "yellow",
        "untrusted_external": "red",
        "known_bad_or_blocked": "bold red",
    }.get(trust_class.value if trust_class else "", "white")

    console.print(Panel(
        f"[bold]Source:[/bold]   {source}\n"
        f"[bold]Trust:[/bold]    [{colour}]{trust_class.value if trust_class else 'unknown'}[/{colour}]\n"
        f"[bold]Conflicts:[/bold] {conflicts}",
        title="[bold cyan]Trust Classification[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
    ))


# ── Main REPL ───────────────────────────────────────────────────────────────

def cmd_start(data_dir: Path, session_name: str, model: str) -> int:
    from odinclaw.shell.hooks import attach_odinclaw_shell

    # ── Startup ──
    _banner()

    console.print(Panel(
        f"[bold white]ODIN[/bold white] — Governed Local AI\n"
        f"[dim]model:    {model}[/dim]\n"
        f"[dim]data:     {data_dir}[/dim]\n"
        f"[dim]session:  {session_name}[/dim]\n"
        f"[dim]Type /help for commands. Every message passes through governance.[/dim]",
        border_style="cyan",
        box=box.ROUNDED,
    ))
    console.print()

    # Attach substrate
    try:
        bridge = attach_odinclaw_shell(data_dir, session_name)
        state  = bridge.launch()
    except Exception as e:
        console.print(f"[red]Failed to start ODIN substrate: {e}[/red]")
        traceback.print_exc()
        return 1

    runtime = bridge.runtime

    # Write initial tray state sidecar
    try:
        from odinclaw.tray import write_tray_state
        write_tray_state(state)
    except Exception:
        pass

    # Launch tray icon in the background (optional — silently skip if unavailable)
    _tray_proc = None
    try:
        _tray_proc = subprocess.Popen(
            [sys.executable, "-m", "odinclaw.tray",
             "--parent-pid", str(os.getpid()),
             "--data", str(data_dir)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        console.print("[dim]Tray icon started. Right-click the taskbar icon to control ODIN.[/dim]")
    except Exception:
        pass  # Tray is non-critical — carry on without it

    # Show startup state
    _print_state(state)

    # Verify Ollama
    try:
        import ollama
        client = ollama.Client(host=_OLLAMA_BASE)
        available = [m.model for m in client.list().models]
        if model not in available:
            console.print(f"[yellow]⚠ Model '{model}' not found in Ollama.[/yellow]")
            console.print(f"[dim]Available: {', '.join(available[:5])}[/dim]")
            console.print(f"[dim]Run: ollama pull {model}[/dim]")
            # Don't exit — allow substrate-only mode
        else:
            console.print(f"[dim green]✓ Model '{model}' ready.[/dim green]")
    except ImportError:
        console.print("[yellow]⚠ ollama package not installed. Chat disabled. Substrate tools available.[/yellow]")
    except Exception as e:
        console.print(f"[yellow]⚠ Ollama unreachable ({e}). Chat disabled. Substrate tools available.[/yellow]")

    console.print()

    # Conversation history for the model
    messages: list[dict] = [{"role": "system", "content": ODIN_SYSTEM}]
    current_model = model

    # ── REPL Loop ──
    while True:
        try:
            console.print()
            user_input = Prompt.ask(
                "[bold bright_blue]Operator[/bold bright_blue]"
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print()
            break

        if not user_input:
            continue

        # ── Slash command dispatch ──
        if user_input.startswith("/"):
            parts  = user_input[1:].split(maxsplit=1)
            cmd    = parts[0].lower()
            arg    = parts[1] if len(parts) > 1 else ""

            if cmd in ("quit", "exit", "q"):
                break

            elif cmd == "help":
                _print_help()

            elif cmd == "status":
                _print_state(bridge.extension_state())

            elif cmd == "receipts":
                n = int(arg) if arg.isdigit() else 10
                _print_receipts(bridge, n)

            elif cmd == "memory":
                _print_memory(bridge, arg or None)

            elif cmd == "holds":
                _print_holds(bridge)

            elif cmd == "approve":
                _handle_approve(arg, bridge, runtime)

            elif cmd == "deny":
                _handle_deny(arg, bridge, runtime)

            elif cmd == "preflight":
                _handle_preflight(arg, bridge)

            elif cmd == "trust":
                _handle_trust(arg, bridge)

            elif cmd == "degraded":
                try:
                    r = bridge.lifecycle.enter_degraded_mode(reason="operator-requested")
                    console.print(Panel(
                        f"[yellow]Entered degraded mode[/yellow]\n"
                        f"[dim]receipt: {r.trace_ids.action_id[:16]}[/dim]",
                        border_style="yellow", box=box.ROUNDED,
                    ))
                    _print_state(bridge.extension_state())
                except Exception as e:
                    console.print(f"[red]{e}[/red]")

            elif cmd == "recover":
                try:
                    r = bridge.lifecycle.exit_degraded_mode(reason="operator-recovery")
                    console.print(Panel(
                        f"[green]Exited degraded mode — normal operation resumed[/green]\n"
                        f"[dim]receipt: {r.trace_ids.action_id[:16]}[/dim]",
                        border_style="green", box=box.ROUNDED,
                    ))
                    _print_state(bridge.extension_state())
                except Exception as e:
                    console.print(f"[red]{e}[/red]")

            elif cmd == "session":
                _print_session(bridge, runtime)

            elif cmd == "clear":
                messages = [{"role": "system", "content": ODIN_SYSTEM}]
                console.clear()
                _banner()
                console.print("[dim]Conversation cleared. Substrate state preserved.[/dim]")

            elif cmd == "model":
                if arg:
                    current_model = arg.strip()
                    console.print(f"[dim]Model switched to: {current_model}[/dim]")
                else:
                    console.print(f"[dim]Active model: {current_model}[/dim]")

            else:
                console.print(f"[dim]Unknown command: /{cmd}. Type /help.[/dim]")

            continue

        # ── Chat message — run through governance first ──
        allowed = _govern_message(user_input, bridge)
        if not allowed:
            console.print("[dim]Message blocked by governance.[/dim]")
            continue

        # Record the action in the session runtime
        try:
            from odinclaw.contracts.action_classes import ActionClass
            from odinclaw.contracts.provenance import ProvenanceRecord
            from odinclaw.contracts.trust import TrustClass
            runtime.record_action(
                action_name="chat_message",
                action_class=ActionClass.READ_ONLY_LOCAL,
                provenance=ProvenanceRecord(
                    source_type="user",
                    source_label="cli-operator",
                    trust_class=TrustClass.TRUSTED_OPERATOR,
                ),
                payload={"content": user_input[:120]},
                meaningful=True,
            )
        except Exception:
            pass  # Runtime logging failure never blocks the user

        # Add to conversation and stream response
        messages.append({"role": "user", "content": user_input})
        response = _stream_ollama(messages, current_model)

        if response:
            messages.append({"role": "assistant", "content": response})

            # Record assistant response in runtime
            try:
                from odinclaw.contracts.action_classes import ActionClass
                from odinclaw.contracts.provenance import ProvenanceRecord
                from odinclaw.contracts.trust import TrustClass
                runtime.record_action(
                    action_name="model_response",
                    action_class=ActionClass.READ_ONLY_LOCAL,
                    provenance=ProvenanceRecord(
                        source_type="model",
                        source_label=current_model,
                        trust_class=TrustClass.UNTRUSTED_EXTERNAL,
                    ),
                    payload={"length": len(response)},
                    meaningful=True,
                )
            except Exception:
                pass

    # ── Shutdown ──
    console.print()
    console.print(Rule("[dim cyan]Shutting down ODIN[/dim cyan]", style="dim cyan"))

    # Close tray icon if it is still running
    if _tray_proc is not None and _tray_proc.poll() is None:
        _tray_proc.terminate()

    try:
        shutdown_state = bridge.shutdown()
        console.print(Panel(
            f"[green]✓ Clean shutdown[/green]\n"
            f"[dim]receipts written:  {shutdown_state.audit.receipt_count}[/dim]\n"
            f"[dim]continuity links:  {shutdown_state.audit.continuity_links}[/dim]\n"
            f"[dim]memory records:    {shutdown_state.memory.durable_records}[/dim]",
            title="[bold]Session Complete[/bold]",
            border_style="green",
            box=box.ROUNDED,
        ))
    except Exception as e:
        console.print(f"[yellow]Shutdown warning: {e}[/yellow]")

    console.print(Text(RUNE_DIVIDER, style="dim cyan"), justify="center")
    return 0


def cmd_status(data_dir: Path) -> int:
    from odinclaw.shell.hooks import attach_odinclaw_shell

    _banner()
    console.print(f"[dim]Data dir: {data_dir}[/dim]")

    try:
        bridge = attach_odinclaw_shell(data_dir, "cli-status")
        state  = bridge.launch()
        _print_state(state)
        _print_receipts(bridge, 5)
        bridge.shutdown()
    except Exception as e:
        console.print(f"[red]Failed to read substrate state: {e}[/red]")
        traceback.print_exc()
        return 1

    return 0


# ── Entry Point ─────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="odinclaw",
        description="ODIN — Governed Local AI",
    )
    sub = parser.add_subparsers(dest="command")

    p_start = sub.add_parser("start", help="Start an interactive ODIN session")
    p_start.add_argument("--data",    metavar="PATH",  default=str(_DEFAULT_DATA_DIR),
                         help=f"Data directory (default: {_DEFAULT_DATA_DIR})")
    p_start.add_argument("--session", metavar="NAME",  default="odin-session",
                         help="Session name (default: odin-session)")
    p_start.add_argument("--model",   metavar="MODEL", default=_MODEL_DEFAULT,
                         help=f"Ollama model (default: {_MODEL_DEFAULT})")

    p_status = sub.add_parser("status", help="Print substrate state and exit")
    p_status.add_argument("--data", metavar="PATH", default=str(_DEFAULT_DATA_DIR),
                          help=f"Data directory (default: {_DEFAULT_DATA_DIR})")

    # Alias: bare `odinclaw` with no subcommand → start
    args = parser.parse_args(argv)

    if args.command == "start":
        sys.exit(cmd_start(
            Path(args.data),
            args.session,
            args.model,
        ))
    elif args.command == "status":
        sys.exit(cmd_status(Path(args.data)))
    else:
        # No subcommand: drop straight into interactive session
        sys.exit(cmd_start(
            _DEFAULT_DATA_DIR,
            "odin-session",
            _MODEL_DEFAULT,
        ))


if __name__ == "__main__":
    main()
