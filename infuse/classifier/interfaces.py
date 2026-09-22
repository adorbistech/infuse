"""Workload Classifier interface definitions."""

from abc import ABC, abstractmethod

from infuse.classifier.models import WorkloadClassification
from infuse.context.models import ExecutionContextRecord


class IWorkloadClassifier(ABC):
    """Abstract classifier interface for interpreting Execution Context."""

    @abstractmethod
    def classify(self, context: ExecutionContextRecord) -> WorkloadClassification:
        """Derive canonical WorkloadClassification from an immutable ExecutionContextRecord.

        Must be deterministic, explainable, and independent of provider/model selection,
        routing, and Governor enforcement.
        """
        raise NotImplementedError
