"""O18 training — role-level records only, never invent employees."""
from __future__ import annotations

from typing import Any, Dict, List

from backend.agents.official_opportunities._common import agent_envelope


def evaluate_training(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    programs: List[Dict[str, Any]] = snapshot.get("programs") or []
    completions: List[Dict[str, Any]] = snapshot.get("completions") or []
    if not programs and not completions:
        return agent_envelope(
            "O18",
            False,
            recommendation=None,
            reason="No training program records are persisted.",
        )
    required = [p for p in programs if p.get("required")]
    latest = completions[0] if completions else None
    pct = latest.get("completion_pct") if latest else None
    recs = []
    for p in required:
        if p.get("status") != "COMPLETED":
            recs.append(f"Complete required program: {p.get('program_name') or p.get('topic')}")
    return agent_envelope(
        "O18",
        True,
        current_state={
            "training_status": latest.get("status") if latest else "OPEN",
            "training_completion_pct": pct,
            "required_training_count": len(required),
            "program_count": len(programs),
            "latest_role_label": latest.get("role_label") if latest else None,
        },
        optimized_state={"target_completion_pct": 100.0},
        recommendation="ASSIGN_REQUIRED_TRAINING" if recs else "MAINTAIN",
        reason="; ".join(recs) if recs else "Required training programs are current.",
        confidence=0.7,
        extra={"programs": programs, "completions": completions, "action_items": recs, "current_value": pct, "optimized_value": 100.0},
    )
