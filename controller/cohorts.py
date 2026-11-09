"""Unified Cohort Object and Matcher (C2).

Shared across detection, experiments, proposals, and supervisor views.
A lead belongs to the first cohort it matches, otherwise to 'default'.
Each 'where' clause is an AND across features and an OR within a feature's list.
"""
from typing import Any, Dict, List, Optional


class CohortDefinition:
    def __init__(self, cohort_id: str, where: Dict[str, List[str]], description: str = ""):
        self.id = cohort_id
        self.where = where
        self.description = description or f"Cohort matching {where}"

    def matches(self, features: Dict[str, str]) -> bool:
        """AND across features, OR within feature value list."""
        for feat, allowed_vals in self.where.items():
            val = features.get(feat)
            if val is None or val not in allowed_vals:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "where": self.where}


class CohortEngine:
    """Manages cohort definitions and assignment for a workflow."""

    def __init__(self, cohorts: Optional[List[Dict[str, Any]]] = None):
        self.cohorts: List[CohortDefinition] = []
        if cohorts:
            for c in cohorts:
                self.cohorts.append(CohortDefinition(c["id"], c.get("where", {})))

    def assign(self, features: Dict[str, str]) -> str:
        """Evaluates cohorts in order; first match wins, otherwise 'default'."""
        for c in self.cohorts:
            if c.matches(features):
                return c.id
        return "default"

    def get_cohort_ids(self) -> List[str]:
        return ["default"] + [c.id for c in self.cohorts]

    def to_config_list(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self.cohorts]

    @classmethod
    def create_standard_cohorts(cls, workflow_meta: Dict[str, Any]) -> "CohortEngine":
        """
        Creates standard, high-signal, non-fragmenting cohorts based on workflow options and mixes.
        Keeps cohort count between 2 and 5 to ensure adequate sample size per cohort.
        """
        cohort_list: List[Dict[str, Any]] = []
        languages = workflow_meta.get("languages", [])

        # 1. Senior cohort (60+)
        cohort_list.append({
            "id": "senior",
            "where": {"age_band": ["60+"]}
        })

        # 2. Young cohort (18-30)
        cohort_list.append({
            "id": "young",
            "where": {"age_band": ["18-30"]}
        })

        # 3. Specific language cohorts for regional languages (e.g. Tamil 'ta', Kannada 'kn')
        for lang in languages:
            if lang in ("ta", "kn") and len(cohort_list) < 4:
                cohort_list.append({
                    "id": f"lang_{lang}",
                    "where": {"lang": [lang]}
                })

        # 4. Metro / Tier 1 cohort
        if len(cohort_list) < 4:
            cohort_list.append({
                "id": "metro_tier1",
                "where": {"city_tier": ["1"]}
            })

        return cls(cohort_list)
