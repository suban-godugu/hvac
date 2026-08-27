"""Safe-RL recommend orchestrator — advisory only, never writes setpoints."""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.ai.safe_rl.mapper import map_to_commands
from backend.ai.safe_rl.persist import save_decision
from backend.ai.safe_rl.scorer import rank_candidates
from backend.ai.safe_rl.state import build_decision_state
from backend.services.hvac_safety_contract import is_safe_mode


def recommend(
    zone_id: str = "ZONE-01",
    *,
    building_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run NB2 Optimizer: score actions, persist SAFE_RL decision, map O* PROPOSED commands."""
    try:
        from backend.workers.watchdog import beat

        beat(note="recommend", service="safe_rl")
    except Exception:
        pass
    state = build_decision_state(zone_id, building_id=building_id)

    if is_safe_mode() or state.get("safe_mode"):
        result = save_decision(
            zone_id=zone_id,
            building_id=state.get("building_id"),
            status="BLOCKED",
            winner=None,
            rejected_actions=[{"action_id": "*", "reason": "SAFE_MODE", "score": -999.0}],
            constraints=["SAFE_MODE"],
            state_snapshot=state,
            mapped_commands=[],
            confidence=0.0,
        )
        return {**result, "code": "SAFE_MODE", "wrote_setpoints": False}

    if not state.get("telemetry_ok"):
        result = save_decision(
            zone_id=zone_id,
            building_id=state.get("building_id"),
            status="BLOCKED",
            winner=None,
            rejected_actions=[{"action_id": "*", "reason": "TELEMETRY_MISSING", "score": -999.0}],
            constraints=["telemetry_ok"],
            state_snapshot=state,
            mapped_commands=[],
            confidence=0.0,
        )
        return {**result, "code": "INPUTS_MISSING", "wrote_setpoints": False}

    ranking = rank_candidates(state)
    winner = ranking.get("winner")
    all_rejected = ranking.get("all_rejected")

    if all_rejected or winner is None:
        result = save_decision(
            zone_id=zone_id,
            building_id=state.get("building_id"),
            status="BLOCKED",
            winner=None,
            rejected_actions=ranking.get("rejected_actions") or [],
            constraints=ranking.get("constraints") or [],
            state_snapshot=state,
            mapped_commands=[],
            confidence=0.0,
        )
        return {**result, "code": "ALL_REJECTED", "wrote_setpoints": False}

    from backend.ai.safe_rl.persist import new_decision_id
    from backend.rules.engine import evaluate as rule_engine_evaluate

    decision_id = new_decision_id()
    mapped: list = []
    rule_verdict = None

    if winner.get("action_id") != "hold":
        rule_verdict = rule_engine_evaluate(
            {
                "action": "RECOMMEND",
                "point_id": winner.get("point_id"),
                "old_value": winner.get("old_value"),
                "new_value": winner.get("new_value"),
                "target_value": winner.get("new_value"),
                "opportunity_id": winner.get("mapped_opportunity") or "SAFE_RL",
                "zone_id": zone_id,
                "building_id": state.get("building_id"),
                "normalized": state.get("normalized"),
                "confidence": ranking.get("confidence"),
                "decision": "OPTIMIZE",
                "safety": {"status": "PASS", "passed": True},
            }
        )
        if rule_verdict.get("verdict") != "APPROVED":
            constraints = list(ranking.get("constraints") or [])
            constraints.append(str(rule_verdict.get("code") or "RULE_ENGINE"))
            result = save_decision(
                decision_id=decision_id,
                zone_id=zone_id,
                building_id=state.get("building_id"),
                status="BLOCKED",
                winner={
                    **winner,
                    "confidence": ranking.get("confidence"),
                    "rule_engine": {
                        "verdict": rule_verdict.get("verdict"),
                        "code": rule_verdict.get("code"),
                        "reason": rule_verdict.get("reason"),
                    },
                },
                rejected_actions=ranking.get("rejected_actions") or [],
                constraints=constraints,
                state_snapshot={**state, "rule_engine": rule_verdict},
                mapped_commands=[],
                confidence=float(ranking.get("confidence") or 0.0),
            )
            return {
                **result,
                "code": "RULE_ENGINE_REJECTED",
                "rule_engine": rule_verdict,
                "wrote_setpoints": False,
            }
        mapped = map_to_commands(winner, zone_id=zone_id, decision_id=decision_id)

    winner_out = {**winner, "confidence": ranking.get("confidence")}
    if rule_verdict:
        winner_out["rule_engine"] = {
            "verdict": rule_verdict.get("verdict"),
            "code": rule_verdict.get("code"),
            "reason": rule_verdict.get("reason"),
        }

    result = save_decision(
        decision_id=decision_id,
        zone_id=zone_id,
        building_id=state.get("building_id"),
        status="PROPOSED",
        winner=winner_out,
        rejected_actions=ranking.get("rejected_actions") or [],
        constraints=ranking.get("constraints") or [],
        state_snapshot={**state, "rule_engine": rule_verdict} if rule_verdict else state,
        mapped_commands=mapped,
        confidence=float(ranking.get("confidence") or 0.0),
    )

    return {**result, "code": "OK", "rule_engine": rule_verdict, "wrote_setpoints": False}
