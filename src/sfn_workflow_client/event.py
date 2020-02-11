"""Contains classes related to workflow execution events"""
import json
import re
from typing import Any, Dict, List, Optional

import arrow
from botocore.exceptions import ClientError

from .enums import ExecutionEventType
from .exceptions import ExecutionDoesNotExist
from .util import call_async, Collection

EVENT_DETAILS_KEY_PATTERN = re.compile(r"EventDetails$")


class ExecutionEvent:
    """Data class for a history event in a workflow execution

    See: https://docs.aws.amazon.com/step-functions/latest/apireference/API_HistoryEvent.html

    """

    def __init__(
        self,
        parents: List[Any],
        timestamp: arrow.Arrow = None,
        event_type: ExecutionEventType = None,
        event_id: int = None,
        previous_event_id: Optional[int] = None,
        details: Optional[Dict] = None,
    ) -> None:
        """
        Args:
            parents: List of parent objects. This list should contain
                [<workflow>, <execution collection>, <execution>, <event collection>].
            timestamp: Timestamp of the event
            event_type: Event type
            event_id: Internal event ID
            previous_event_id: Internal ID of the previous event in the execution (if
                applicable)
            details: Details about the event specific to the type

        """
        self.parents = parents
        self.timestamp = timestamp
        self.event_type = event_type
        self.event_id = event_id
        self.previous_event_id = previous_event_id
        self.details = details

    def parse_response(self, response: Dict) -> "ExecutionEvent":
        """Parse a Step Functions API response and update attributes

        Args:
            response: Step Functions API response for a single execution event

        Returns:
            event object with updated metadata

        """
        self.timestamp = arrow.get(response["timestamp"])
        self.event_type = ExecutionEventType(response["type"])
        self.event_id = response["id"]
        self.previous_event_id = response["previousEventId"]
        self.details = self._get_event_details(response)
        return self

    def _get_event_details(self, response: Dict) -> Optional[Dict]:
        """Get event details from the response.

        The response contains a key with details that depends on the event type. This
        method iterates through the response keys (there are only a handful) and
        returns the value for the first key that ends with "EventDetails".

        Args:
            response: Step Functions API response for a single execution event

        Returns:
            event details or None if the details key could not be found

        """
        for key in response:
            if re.search(EVENT_DETAILS_KEY_PATTERN, key) is not None:
                return response[key]

        return None


class ExecutionEventCollection(Collection):
    """Represents a collection of execution events"""

    CHILD_CLASS = ExecutionEvent

    @property
    def execution(self) -> "execution.Execution":
        """Returns the execution instance from the list of parents"""
        return self.parents[-1]

    @property
    def workflow(self) -> "workflow.Workflow":
        """Returns the workflow instance"""
        return self.execution.workflow

    async def fetch(self) -> "ExecutionEventCollection":
        """Fetch a list of execution history events

        Events will be sorted by timestamp, oldest to newest.

        Returns:
            list of execution event objects with metadata

        Raises:
            :py:exc:`.ExecutionDoesNotExist` if the execution could not be found

        """
        # Create a paginator (iterator) then page through all the pages by wrapping it
        # in a list function.
        # See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/paginators.html
        paginator = self.workflow.stepfunctions.get_paginator("get_execution_history")
        try:
            responses = await call_async(
                list, paginator.paginate(executionArn=self.execution.execution_arn)
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ExecutionDoesNotExist":
                raise ExecutionDoesNotExist(
                    self.workflow.name, self.execution.execution_id
                )
            raise

        self._items = [
            self.create().parse_response(event_details)
            for response in responses
            for event_details in response["events"]
        ]
        return self

    def find_nested_execution_id(self, task_name: str) -> Optional[str]:
        """Helper for finding the ID for a nested state machine execution.

        Note that this will return the **first** matching task it finds.

        Args:
            task_name: Name of the task that submitted the nested execution

        Returns:
            execution ID or None if nothing was found

        """
        for event in self._items:
            if event.event_type == ExecutionEventType.task_submitted:
                output = json.loads(event.details["output"])
                parts = output["ExecutionArn"].split(":")
                nested_execution_id = parts[-1]
                parsed_task_name = parts[-2].split("-")[-1]
                if parsed_task_name == task_name:
                    return nested_execution_id

        return None
