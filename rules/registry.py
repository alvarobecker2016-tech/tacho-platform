from typing import List
from domain.models import TimelineEvent, Violation
from rules.base import BaseRule

class RuleRegistry:
    def __init__(self):
        self._rules: List[BaseRule] = []

    def register(self, rule: BaseRule):
        self._rules.append(rule)

    def evaluate_all(self, timeline: List[TimelineEvent]) -> List[Violation]:
        all_violations = []
        for rule in self._rules:
            all_violations.extend(rule.evaluate(timeline))
        return all_violations
