from abc import ABC, abstractmethod
from typing import List
from domain.models import TimelineEvent, Violation

class BaseRule(ABC):
    @abstractmethod
    def evaluate(self, timeline: List[TimelineEvent]) -> List[Violation]:
        pass
