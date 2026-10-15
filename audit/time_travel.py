"""Bonus Challenge 1 — Time-Travel with LangGraph Checkpointer.

Usage:
    uv run python -m audit.time_travel --thread <thread_id>
    uv run python -m audit.time_travel --thread <thread_id> --resume <approve|reject|edit>

Lists every checkpoint state in a session using `aget_state_history()`,
and allows branching/resuming from an earlier checkpoint with a different decision.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from rich.console import Console
from rich.table import Table

from common.db import db_path
from exercises.exercise_4_audit import build_graph


load_dotenv()
console = Console()


async def list_history(thread_id: str) -> list:
    cfg = {"configurable": {"thread_id": thread_id}}
    history = []
    async with AsyncSqliteSaver.from_conn_string(db_path()) as cp:
        await cp.setup()
        app = build_graph(cp)
        async for state in app.aget_state_history(cfg):
            history.append(state)
    return history


def display_history(thread_id: str, history: list) -> None:
    console.rule(f"[bold cyan]Time-Travel: State History for {thread_id}[/bold cyan]")
    table = Table(title=f"Checkpoints ({len(history)} total, newest first)")
    table.add_column("Checkpoint ID", style="dim")
    table.add_column("Next Node", style="cyan")
    table.add_column("Decision / Action", style="magenta")
    table.add_column("State Summary")

    for st in history:
        cid = st.config["configurable"].get("checkpoint_id", "")[:12] + "..."
        next_nodes = ", ".join(st.next) if st.next else "(END)"
        vals = st.values
        action = vals.get("final_action") or vals.get("decision") or "-"
        analysis = vals.get("analysis")
        conf = f"{analysis.confidence:.0%}" if analysis else "-"
        summary = f"conf={conf}, title={str(vals.get('pr_title', ''))[:30]}"
        table.add_row(cid, next_nodes, action, summary)

    console.print(table)


async def time_travel_resume(thread_id: str, new_choice: str, feedback: str = "") -> None:
    history = await list_history(thread_id)
    if not history:
        console.print(f"[red]No checkpoints found for thread {thread_id}[/red]")
        return

    display_history(thread_id, history)

    # Find the interrupted checkpoint where human approval was pending
    target_state = None
    for st in history:
        if st.tasks and any(t.interrupts for t in st.tasks):
            target_state = st
            break
        if "human_approval" in st.next:
            target_state = st
            break

    if not target_state:
        # Default to the earliest state with next actions
        candidates = [s for s in history if s.next]
        target_state = candidates[0] if candidates else history[0]

    target_cid = target_state.config["configurable"].get("checkpoint_id")
    console.print(f"\n[green]Resuming from checkpoint:[/green] [dim]{target_cid}[/dim]")
    console.print(f"[cyan]Applying new reviewer choice:[/cyan] [bold]{new_choice}[/bold]\n")

    cfg = target_state.config

    async with AsyncSqliteSaver.from_conn_string(db_path()) as cp:
        await cp.setup()
        app = build_graph(cp)
        # Update state at target checkpoint with new reviewer decision
        updated_cfg = await app.aupdate_state(
            cfg,
            {
                "human_choice": new_choice,
                "human_feedback": feedback or f"Time-travel alternative decision: {new_choice}",
            },
            as_node="human_approval",
        )
        result = await app.ainvoke(None, updated_cfg)
        console.rule("[bold green]Time-Travel Outcome[/bold green]")
        console.print(f"Final Action: [bold magenta]{result.get('final_action')}[/bold magenta]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bonus 1: Time-travel through checkpoint history")
    parser.add_argument("--thread", required=True, help="Session thread ID")
    parser.add_argument("--resume", choices=["approve", "reject", "edit"], help="Resume from checkpoint with alternative choice")
    parser.add_argument("--feedback", default="", help="Optional feedback note")
    args = parser.parse_args()

    if args.resume:
        asyncio.run(time_travel_resume(args.thread, args.resume, args.feedback))
    else:
        history = asyncio.run(list_history(args.thread))
        display_history(args.thread, history)


if __name__ == "__main__":
    main()
