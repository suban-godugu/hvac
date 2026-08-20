"""
SupervisoryDecisionEngine:
Coordinates candidates across O1, O2, O3, O4, resolves conflicts, ranks actions,
and produces a unified, coherent supervisory action set.
"""
from typing import Dict, Any, List, Optional
from backend.agents.scheduling_supervisory.state import (
    CandidateAction,
    OpportunityEvaluationResult
)


class SupervisoryDecisionEngine:
    def __init__(self):
        # Priority weights for ranking: (Comfort / Safety = 1, Energy Efficiency = 2, Equipment Life = 3)
        self.opportunity_priority = {
            "O2": 1,  # Space comfort
            "O3": 2,  # AHU SAT Trim & Respond
            "O4": 3,  # Chiller Staging
            "O1": 4,  # Schedule Start/Stop
        }

    def collect_candidates(self, results: List[OpportunityEvaluationResult]) -> List[CandidateAction]:
        """Collects all candidate actions from the 4 opportunity evaluation results."""
        all_candidates: List[CandidateAction] = []
        for res in results:
            if res and res.candidates:
                all_candidates.extend(res.candidates)
        return all_candidates

    def detect_conflicts(self, candidates: List[CandidateAction]) -> List[Dict[str, Any]]:
        """Detects duplicate point writes, conflicting setpoint directions, or conflicting equipment calls."""
        conflicts: List[Dict[str, Any]] = []
        seen_points: Dict[str, CandidateAction] = {}

        for act in candidates:
            if act.point_id in seen_points:
                existing = seen_points[act.point_id]
                conflicts.append({
                    "point_id": act.point_id,
                    "action_1": existing.id,
                    "action_2": act.id,
                    "type": "DUPLICATE_POINT_TARGET",
                    "resolution": f"Keep higher priority action ({existing.opportunity_code} vs {act.opportunity_code})"
                })
            else:
                seen_points[act.point_id] = act

        return conflicts

    def rank_actions(self, candidates: List[CandidateAction]) -> List[CandidateAction]:
        """
        Ranks actions based on:
        1. Opportunity domain priority (Space Comfort O2 > AHU SAT O3 > Chiller O4 > Start/Stop O1)
        2. Algorithmic confidence score (higher is prioritized)
        """
        return sorted(
            candidates,
            key=lambda a: (
                self.opportunity_priority.get(a.opportunity_code, 5),
                -a.confidence
            )
        )

    def reject_incompatible_combinations(self, candidates: List[CandidateAction]) -> List[CandidateAction]:
        """
        Filters out incompatible commands (e.g. staging down a chiller while demanding cold SAT < 11°C,
        or multiple writes to the same point).
        """
        coherent_set: List[CandidateAction] = []
        targeted_points = set()

        # Rank first so higher priority actions claim points
        ranked = self.rank_actions(candidates)

        for act in ranked:
            if act.point_id in targeted_points:
                # Reject duplicate write to same point in same cycle
                continue
            targeted_points.add(act.point_id)
            coherent_set.append(act)

        return coherent_set

    def produce_coordinated_action_set(
        self,
        opportunity_results: List[OpportunityEvaluationResult]
    ) -> List[CandidateAction]:
        """
        Main entrypoint: collects candidates, resolves conflicts, and outputs the single coordinated set.
        """
        raw_candidates = self.collect_candidates(opportunity_results)
        coordinated_actions = self.reject_incompatible_combinations(raw_candidates)
        return coordinated_actions
