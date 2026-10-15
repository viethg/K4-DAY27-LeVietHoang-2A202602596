"""Bonus Challenge 2 — Confidence Calibration Analysis.

Usage:
    uv run python -m audit.calibrate

Queries `audit_events` to compute average model confidence versus human
approval outcomes, determining if the LLM is over- or under-confident.
"""

from __future__ import annotations

import asyncio
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from common.db import db_conn


async def compute_calibration() -> dict:
    async with db_conn() as conn:
        # Total sessions
        async with conn.execute("SELECT COUNT(DISTINCT thread_id) FROM audit_events") as cur:
            total_sessions = (await cur.fetchone())[0]

        # Total events
        async with conn.execute("SELECT COUNT(*) FROM audit_events") as cur:
            total_events = (await cur.fetchone())[0]

        # Overall average confidence across analyze events
        async with conn.execute(
            "SELECT AVG(confidence) FROM audit_events WHERE action IN ('analyze', 'synthesize')"
        ) as cur:
            row = await cur.fetchone()
            avg_conf = row[0] if row and row[0] is not None else 0.0

        # Confidence by routing decision
        async with conn.execute(
            """
            SELECT decision, AVG(confidence), COUNT(*)
              FROM audit_events
             WHERE action = 'route'
             GROUP BY decision
            """
        ) as cur:
            route_stats = await cur.fetchall()

        # Human approvals vs rejections
        async with conn.execute(
            """
            SELECT decision, COUNT(*), AVG(confidence)
              FROM audit_events
             WHERE action = 'human_approval' AND reviewer_id IS NOT NULL
             GROUP BY decision
            """
        ) as cur:
            human_stats = await cur.fetchall()

    human_dict = {r[0]: {"count": r[1], "avg_conf": r[2]} for r in human_stats}
    total_human_decisions = sum(v["count"] for v in human_dict.values())
    approved_count = human_dict.get("approve", {}).get("count", 0)
    approval_rate = (approved_count / total_human_decisions) if total_human_decisions > 0 else 0.0

    return {
        "total_sessions": total_sessions,
        "total_events": total_events,
        "avg_confidence": avg_conf,
        "route_stats": route_stats,
        "human_stats": human_dict,
        "total_human": total_human_decisions,
        "approved_count": approved_count,
        "approval_rate": approval_rate,
    }


def render_report(stats: dict) -> None:
    console = Console()
    console.rule("[bold cyan]Bonus 2 — Confidence Calibration Report[/bold cyan]")
    console.print(f"Total sessions: [bold]{stats['total_sessions']}[/bold]  |  Total audit events: [bold]{stats['total_events']}[/bold]\n")

    # Routing breakdown
    t_route = Table(title="Routing Breakdown & Average Confidence")
    t_route.add_column("Route Decision", style="cyan")
    t_route.add_column("Count", justify="right")
    t_route.add_column("Avg Confidence", justify="right")
    for r in stats["route_stats"]:
        t_route.add_row(str(r[0]), str(r[2]), f"{r[1]:.1%}" if r[1] is not None else "N/A")
    console.print(t_route)
    console.print()

    # Human Decisions breakdown
    t_human = Table(title="Human Decisions Breakdown")
    t_human.add_column("Decision", style="magenta")
    t_human.add_column("Count", justify="right")
    t_human.add_column("Avg Confidence", justify="right")
    for dec, v in stats["human_stats"].items():
        t_human.add_row(dec, str(v["count"]), f"{v['avg_conf']:.1%}" if v["avg_conf"] is not None else "N/A")
    console.print(t_human)
    console.print()

    # Calibration Evaluation
    avg_conf = stats["avg_confidence"]
    app_rate = stats["approval_rate"]
    diff = avg_conf - app_rate

    if stats["total_human"] == 0:
        verdict = "[yellow]Insufficient human reviews to calibrate yet.[/yellow]"
    elif diff > 0.10:
        verdict = (
            f"[bold red]OVER-CONFIDENT[/bold red]\n"
            f"The model's average confidence ({avg_conf:.1%}) is significantly higher than the human approval rate ({app_rate:.1%}). "
            f"The agent tends to trust PR changes more than human reviewers do."
        )
    elif diff < -0.10:
        verdict = (
            f"[bold yellow]UNDER-CONFIDENT[/bold yellow]\n"
            f"The model's average confidence ({avg_conf:.1%}) is lower than the human approval rate ({app_rate:.1%}). "
            f"The agent is overly cautious and requests human review or escalation more often than necessary."
        )
    else:
        verdict = (
            f"[bold green]WELL-CALIBRATED[/bold green]\n"
            f"The model's average confidence ({avg_conf:.1%}) closely matches the human approval rate ({app_rate:.1%}). "
            f"Its self-assessed certainty aligns well with human judgment."
        )

    console.print(Panel(verdict, title="Calibration Verdict", border_style="cyan"))


def main() -> None:
    stats = asyncio.run(compute_calibration())
    render_report(stats)


if __name__ == "__main__":
    main()
