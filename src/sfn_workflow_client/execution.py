"""Contains classes related to workflow executions"""
import json
import re
from typing import Any, Dict, List, Optional, Set
import uuid

import arrow
import backoff
from botocore.exceptions import ClientError

from .config import AWS_ACCOUNT_ID
from .enums import COMPLETED_STATUSES, ExecutionStatus
from .event import ExecutionEventCollection
from .exceptions import (
    ExecutionDoesNotExist,
    InvalidExecutionInputData,
    PollForExecutionStatusFailed,
    PollForExecutionStatusTimedOut,
    WorkflowDoesNotExist,
)
from .util import call_async, Collection

EVENT_DETAILS_KEY_PATTERN = re.compile(r"EventDetails$")


class Execution:
    """Represents a workflow execution"""

    def __init__(
        self,
        parents: List[Any],
        execution_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        started_at: Optional[arrow.Arrow] = None,
        stopped_at: Optional[arrow.Arrow] = None,
        input_data: Optional[Dict] = None,
        output_data: Optional[Dict] = None,
    ) -> None:
        """
        Args:
            parents: List of parent objects. This list should contain
                [<workflow>, <execution collection>].
            execution_id: Optional execution ID to give to the new execution. If not
                provided, a uuid will be generated
            status: Execution status
            started_at: Timestamp indicating when the execution started
            stopped_at: Timestamp indicating when the execution stopped (if applicable
                based on the status)
            input_data: Data provided to the execution when it was started
            output_data: Final output data from the execution if it succeeded

        """
        self.parents = parents
        self.events = ExecutionEventCollection(self.parents + [self])
        self.execution_id = str(uuid.uuid4()) if execution_id is None else execution_id
        self.status = status
        self.started_at = started_at
        self.stopped_at = stopped_at
        self.input_data = input_data
        self.output_data = output_data

    @property
    def workflow(self) -> "workflow.Workflow":
        """Returns the workflow instance from the list of parents"""
        return self.parents[-1].workflow

    @property
    def execution_arn(self) -> str:
        """Returns the execution ARN"""
        return (
            f"arn:aws:states:{self.workflow.stepfunctions.meta.region_name}"
            f":{AWS_ACCOUNT_ID}:execution:{self.workflow.name}:{self.execution_id}"
        )

    def __str__(self) -> str:
        """Returns string representation of the execution"""
        return f"Execution(execution_id={self.execution_id} status={self.status.name})"

    def parse_response(self, response: Dict) -> "Execution":
        """Parse a Step Functions API response and update attributes

        Args:
            response: Step Functions API response for a single execution

        Returns:
            execution object with updated metadata

        """
        self.execution_id = response["name"]
        self.status = ExecutionStatus(response["status"])
        self.started_at = arrow.get(response["startDate"])
        self.stopped_at = (
            None
            if response.get("stopDate") is None
            else arrow.get(response["stopDate"])
        )
        self.input_data = (
            None if response.get("input") is None else json.loads(response["input"])
        )
        self.output_data = (
            None if response.get("output") is None else json.loads(response["output"])
        )
        return self

    @property
    def trace_id(self) -> Optional[str]:
        """Returns trace ID if it exists on the input data"""
        input_data = self.input_data or {}
        return input_data.get("__trace", {}).get("id")

    @property
    def trace_source(self) -> Optional[str]:
        """Returns trace source if it exists on the input data"""
        input_data = self.input_data or {}
        return input_data.get("__trace", {}).get("source")

    async def fetch(self) -> "Execution":
        """Fetch details about the execution.

        Returns:
            execution object with metadata

        Raises:
            :py:exc:`.ExecutionDoesNotExist` if the execution could not be found

        """
        try:
            response = await call_async(
                self.workflow.stepfunctions.describe_execution,
                executionArn=self.execution_arn,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ExecutionDoesNotExist":
                raise ExecutionDoesNotExist(self.workflow.name, self.execution_id)
            raise

        self.parse_response(response)
        return self

    async def start(
        self,
        input_data: Optional[Dict] = None,
        trace_id: Optional[str] = None,
        trace_source: Optional[str] = "manual",
    ) -> "Execution":
        """Start a workflow execution.

        Args:
            input_data: Optional dict of input data to pass to the execution
            trace_id: Optional trace ID for correlating events across the application.
                If not provided, we'll generate a new one. The value is arbitrary.
            trace_source: Optional, arbitrary string that indicates what originated
                the need to start an execution. e.g. "aws.events", "manual"

        Returns:
            execution object with metadata

        Raises:
            :py:exc:`.WorkflowDoesNotExist` if the workflow could not be found

        """
        options = {}
        options["name"] = self.execution_id
        try:
            input_ = {}
            if input_data is not None:
                input_.update(input_data)
            # Insert tracing metadata
            input_["__trace"] = {
                "id": str(uuid.uuid4()) if trace_id is None else trace_id,
                "source": trace_source,
            }
            options["input"] = json.dumps(input_)
        except Exception:
            raise InvalidExecutionInputData(input_data)
        try:
            await call_async(
                self.workflow.stepfunctions.start_execution,
                stateMachineArn=self.workflow.state_machine_arn,
                **options,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "StateMachineDoesNotExist":
                raise WorkflowDoesNotExist(self.workflow.name)
            raise
        execution = await self.fetch()
        return execution

    async def stop(self, error: str = None, cause: str = None) -> "Execution":
        """Stop/cancel/abort a workflow execution.

        The error/cause metadata is optional. It shows up in the console.

        Args:
            error: The error code of why the execution should be stopped
            cause: A more detailed explanation of the cause of the stop

        Returns:
            execution object with metadata

        Raises:
            :py:exc:`.WorkflowDoesNotExist` if the workflow could not be found

        """
        await self.fetch()
        if self.status in COMPLETED_STATUSES:
            # It's already stopped
            return self

        options = {}
        if error is not None:
            options["error"] = error
        if cause is not None:
            options["cause"] = cause
        try:
            await call_async(
                self.workflow.stepfunctions.stop_execution,
                executionArn=self.execution_arn,
                **options,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ExecutionDoesNotExist":
                raise ExecutionDoesNotExist(self.workflow.name, self.execution_id)
            raise
        await self.poll_for_status(statuses={ExecutionStatus.aborted})
        return self

    async def poll_for_status(
        self,
        statuses: Set[ExecutionStatus] = None,
        max_time: int = 120,
        interval: int = 2,
    ) -> "Execution":
        """Poll until the execution reports one of the provided statuses.

        Args:
            statuses: Set of statuses to check
            max_time: Maximum number of seconds to poll
            interval: Polling interval in seconds

        Returns:
            execution object with metadata after polling finishes

        Raises:
            :py:exc:`.PollForExecutionStatusTimedOut` if the ``max_time`` is reached
                before the execution status converges to one of the ``statuses``

        """
        if statuses is None:
            # Default to the set of "completed" statuses
            statuses = COMPLETED_STATUSES

        def _on_giveup(details: Dict):
            """Event handler that triggers when the poller times out.

            Args:
                details: Details about the time out. See https://github.com/litl/backoff#event-handlers

            Raises:
                :py:exc:`.PollForExecutionStatusTimedOut`

            """
            raise PollForExecutionStatusTimedOut(details, statuses)

        def _keep_polling(execution):
            """Predicate that returns True to keep polling.

            Raises:
                :py:exc:`.PollForExecutionStatusFailed` if the execution completed but
                    its final status was not expected

            """
            if execution.status in statuses:
                return False
            elif execution.status in COMPLETED_STATUSES:
                raise PollForExecutionStatusFailed(execution, statuses)

            return True

        @backoff.on_predicate(
            backoff.constant,
            _keep_polling,
            max_time=int(max_time),
            interval=int(interval),
            on_giveup=_on_giveup,
        )
        async def _poll(execution: Execution):
            return await self.fetch()

        # NB: only reason for passing the execution is so we have access to its
        # attributes if an exception arises in the backoff handler.
        return await _poll(self)


class ExecutionCollection(Collection):
    """Represents a collection of workflow executions"""

    CHILD_CLASS = Execution

    @property
    def workflow(self) -> "workflow.Workflow":
        """Returns the workflow instance from the list of parents"""
        return self.parents[-1]

    async def fetch(
        self, status_filter: Optional[ExecutionStatus] = None
    ) -> "ExecutionCollection":
        """Get list of executions for a specific workflow.

        Executions will be sorted by start date, newest to oldest.

        Args:
            status_filter: Optional execution status to filter the list

        Returns:
            collection object with list of execution event objects with metadata

        Raises:
            :py:exc:`.WorkflowDoesNotExist` if the workflow could not be found

        """
        options = {}
        if status_filter is not None:
            options["statusFilter"] = status_filter.value
        # Create a paginator (iterator) then page through all the pages by wrapping it
        # in a list function.
        # See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/paginators.html
        paginator = self.workflow.stepfunctions.get_paginator("list_executions")
        try:
            responses = await call_async(
                list,
                paginator.paginate(
                    stateMachineArn=self.workflow.state_machine_arn, **options
                ),
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "StateMachineDoesNotExist":
                raise WorkflowDoesNotExist(self.workflow.name)
            raise

        self._items = sorted(
            [
                self.create().parse_response(execution_details)
                for response in responses
                for execution_details in response["executions"]
            ],
            key=lambda e: e.started_at,
            reverse=True,
        )
        return self

    async def find_by_trace_id(self, trace_id: str) -> Optional[Execution]:
        """Find an execution by trace ID

        Notes:
        * The ``.fetch`` method should have been previously called.
        * This method is slow because it has to fetch details about each individual
          execution in order to parse the trace ID. Since executions are sorted newest
          to oldest, this method shouldn't be used to search for an old execution.

        Args:
            trace_id: Trace ID, probably a UUID

        Returns:
            execution or None

        """
        for execution in self._items:
            await execution.fetch()
            if execution.trace_id == trace_id:
                return execution

    async def start_sync(
        self,
        execution_id: str = None,
        input_data: Optional[Dict] = None,
        trace_id: Optional[str] = None,
        trace_source: Optional[str] = "manual",
        statuses: Set[ExecutionStatus] = None,
        max_time: int = 120,
        interval: int = 2,
    ) -> Execution:
        """Helper method for starting a new execution and waiting until it completes.

        This is mostly useful in E2E tests.

        See docstrings for ``Execution.create``, ``Execution.start``, and
        ``Execution.poll_for_status`` for details.

        Returns:
            completed execution

        """
        execution = self.create(execution_id=execution_id)
        await execution.start(
            input_data=input_data, trace_id=trace_id, trace_source=trace_source
        )
        await execution.poll_for_status(
            statuses=statuses, max_time=max_time, interval=interval
        )
        return execution
