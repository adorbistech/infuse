"""Workload Classification service boundary."""

from abc import ABC, abstractmethod
from typing import Optional

from infuse.classifier.interfaces import IWorkloadClassifier
from infuse.classifier.models import WorkloadClassification
from infuse.classifier.rule_based import RuleBasedWorkloadClassifier
from infuse.context.models import ExecutionContextRecord


class IWorkloadClassificationService(ABC):
    """Abstract service boundary for classifying execution workloads."""

    @abstractmethod
    def classify(self, context: ExecutionContextRecord) -> WorkloadClassification:
        """Classify execution context."""
        raise NotImplementedError


class WorkloadClassificationService(IWorkloadClassificationService):
    """Default service implementation managing workload classification."""

    def __init__(self, classifier: Optional[IWorkloadClassifier] = None) -> None:
        self.classifier = classifier or RuleBasedWorkloadClassifier()

    def classify(self, context: ExecutionContextRecord) -> WorkloadClassification:
        """Classify the given execution context record."""
        return self.classifier.classify(context)
