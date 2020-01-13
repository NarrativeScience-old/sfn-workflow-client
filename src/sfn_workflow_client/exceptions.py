"""Workflow client exception classes"""
from typing import Any, Dict, Set

from .enums import ExecutionStatus


class WorkflowClientError(Exception):
    """Base class for workflow client errors"""

    pass


class WorkflowDoesNotExist(WorkflowClientError):
    """Raised when a workflow does not exist in AWS Step Functions"""

    def __init__(self, workflow_name: str) -> None:
        """
        Args:
            workflow_name: Workflow name

        """
        self.workflow_name = workflow_name
        super().__init__(f"Workflow {workflow_name} does not exist")


class ExecutionDoesNotExist(WorkflowClientError):
    """Raised when a execution does not exist in AWS Step Functions"""

    def __init__(self, workflow_name: str, execution_id: str) -> None:
        """
        Args:
            workflow_name: Workflow name
            execution_id: Execution ID

        """
        self.workflow_name = workflow_name
        self.execution_id = execution_id
        super().__init__(
            f"Execution {execution_id} does not exist for workflow {workflow_name}"
        )


class InvalidExecutionInputData(WorkflowClientError):
    """Raised when the input data passed to a new execution is not JSON-serializable"""

    def __init__(self, input_data: Any) -> None:
        """
        Args:
            input_data: Input data passed to the new execution

        """
        self.input_data = input_data
        super().__init__(f"Input data must be JSON-serializable: {input_data}")


class PollForExecutionStatusTimedOut(WorkflowClientError):
    """Raised when the max_time is exceeded while polling for execution status"""

    def __init__(self, details: Dict, statuses: Set[ExecutionStatus]) -> None:
        """
        Args:
            details: Details about the time out. See https://github.com/litl/backoff#event-handlers
            statuses: Set of statuses that were being checked during polling

        """
        self.details = details
        execution, = details["args"]
        super().__init__(
            f"{execution} failed to converge to {statuses}"
            f" after {details['elapsed']} seconds"
        )


class PollForExecutionStatusFailed(WorkflowClientError):
    """Raised when an execution completes but the final status was not expected"""

    def __init__(
        self,
        execution: "execution.Execution",  # noqa: F821
        statuses: Set[ExecutionStatus],
    ) -> None:
        """
        Args:
            execution: Execution instance
            statuses: Set of statuses that were being checked during polling

        """
        self.execution = execution
        super().__init__(f"{execution} failed to converge to {statuses}")
