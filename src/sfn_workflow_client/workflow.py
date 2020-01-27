"""Contains a client for interacting with a workflow"""

from .clients import stepfunctions
from .config import AWS_ACCOUNT_ID
from .execution import ExecutionCollection


class Workflow:
    """Client wrapper around boto3's Step Functions interface.

    This class is mostly a conduit for working with executions. Common interactions
    include::

        # Initialize a workflow client
        workflow = Workflow("my-state-machine")
        # Fetch all executions
        collection = await workflow.executions.fetch()
        # Fetch currently running executions
        collection = await workflow.executions.fetch(status=ExecutionStatus.running)
        # Start a new execution
        execution = await workflow.executions.create().start()
        # Start a new execution and wait until it completes (useful for tests)
        execution = await workflow.executions.start_sync()
        # Find an execution by trace ID (for tests)
        execution = await workflow.executions.fetch().find_by_trace_id("abc")
        # Fetch the event history of an execution
        events = await execution.events.fetch()

    """

    def __init__(self, name: str) -> None:
        """
        Args:
            name: Workflow (state machine) name to be used to query AWS Step Functions.

        """
        self.name = name
        self.executions = ExecutionCollection([self])
        self.state_machine_arn = (
            f"arn:aws:states:{stepfunctions.meta.region_name}:{AWS_ACCOUNT_ID}"
            f":stateMachine:{self.name}"
        )
