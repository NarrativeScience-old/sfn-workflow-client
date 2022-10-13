"""Contains functional tests for workflow executions"""

import asyncio
from copy import deepcopy
import json
import logging
import os
import unittest
import uuid

import arrow
from test_utils import async_test

from sfn_workflow_client.enums import ExecutionEventType, ExecutionStatus
from sfn_workflow_client.exceptions import (
    ExecutionDoesNotExist,
    PollForExecutionStatusFailed,
    PollForExecutionStatusTimedOut,
    WorkflowDoesNotExist,
)
from sfn_workflow_client.workflow import Workflow

ROLE_ARN = os.environ["AWS_IAM_ROLE_ARN"]


def without_trace(data):
    """Test helper to remove trace metadata from an input/output dict"""
    result = deepcopy(data)
    try:
        del result["__trace"]
    except Exception:
        pass
    return result


class WorkflowClientFunctionalTestCase(unittest.TestCase):
    """Base class for WorkflowClient functional tests.

    It creates a new state machine, sets up a client, and tears down the state machine
    upon completion.
    """

    #: Child classes must define a state machine definition
    STATE_MACHINE_DEFINITION = {}

    @classmethod
    def setUpClass(cls):
        """Test case setup

        This creates a new state machine.
        """
        cls.workflow = Workflow(f"test-{uuid.uuid4()}")
        response = cls.workflow.stepfunctions.create_state_machine(
            name=cls.workflow.name,
            definition=json.dumps(cls.STATE_MACHINE_DEFINITION),
            roleArn=ROLE_ARN,
            tags=[{"key": "Environment", "value": "test"}],
        )
        logging.debug(response)

    @classmethod
    def tearDownClass(cls):
        """Clean up after test cases finish"""
        response = cls.workflow.stepfunctions.delete_state_machine(
            stateMachineArn=cls.workflow.state_machine_arn
        )
        logging.debug(response)


class FunctionalTestsWorkflowClient(WorkflowClientFunctionalTestCase):
    """Functional tests for common methods of the WorkflowClient class"""

    # This state machine can be parameterized to fail or succeed via the ``$.fail``
    # path. This key is required in the input data.
    STATE_MACHINE_DEFINITION = {
        "StartAt": "Choice",
        "States": {
            "Choice": {
                "Type": "Choice",
                "Choices": [
                    {"Variable": "$.fail", "BooleanEquals": True, "Next": "Fail"}
                ],
                "Default": "Pass",
            },
            "Fail": {"Type": "Fail", "Error": "Bad", "Cause": "Everything"},
            "Pass": {
                "Type": "Pass",
                "ResultPath": "$.foo",
                "Result": "bar",
                "End": True,
            },
        },
    }

    @async_test
    async def test_01_describe_execution__missing_workflow(self):
        """Should raise when workflow does not exist"""
        workflow = Workflow("test-nope")
        execution = workflow.executions.create("abc-123")
        with self.assertRaises(ExecutionDoesNotExist):
            await execution.fetch()

    @async_test
    async def test_02_describe_execution__missing_execution(self):
        """Should raise when execution does not exist"""
        execution = self.workflow.executions.create("abc-123")
        with self.assertRaises(ExecutionDoesNotExist):
            await execution.fetch()

    @async_test
    async def test_03_get_execution_history__missing_execution(self):
        """Should raise when execution does not exist"""
        execution = self.workflow.executions.create("abc-123")
        with self.assertRaises(ExecutionDoesNotExist):
            await execution.events.fetch()

    @async_test
    async def test_04_start_execution__missing_workflow(self):
        """Should raise when workflow does not exist"""
        execution = Workflow("test-nope").executions.create()
        with self.assertRaises(WorkflowDoesNotExist):
            await execution.start()

    @async_test
    async def test_05_start_execution__with_data(self):
        """Should start an execution with input data"""
        execution = self.workflow.executions.create("test-success")
        await execution.start(input_data={"hello": "world", "fail": False})
        # Give Step Functions a second (it's eventually consistent)
        await asyncio.sleep(1)
        await execution.fetch()
        self.assertEqual(execution.execution_id, "test-success")
        self.assertEqual(execution.status, ExecutionStatus.succeeded)
        self.assertTrue(execution.started_at < execution.stopped_at)
        self.assertTrue(execution.stopped_at < arrow.get())
        self.assertIsNotNone(execution.input_data["__trace"]["id"])
        self.assertEqual(execution.input_data["__trace"]["source"], "manual")
        self.assertEqual(execution.input_data["hello"], "world")
        self.assertEqual(execution.input_data["fail"], False)
        self.assertEqual(
            without_trace(execution.output_data),
            {"hello": "world", "fail": False, "foo": "bar"},
        )

    @async_test
    async def test_06_start_execution__with_trace_info(self):
        """Should start an execution with trace info"""
        execution = self.workflow.executions.create("test-trace")
        await execution.start(
            input_data={"hello": "world", "fail": False},
            trace_id="abc",
            trace_source="the-alphabet",
        )
        # Give Step Functions a second (it's eventually consistent)
        await asyncio.sleep(1)
        await execution.fetch()
        self.assertEqual(execution.execution_id, "test-trace")
        self.assertEqual(execution.status, ExecutionStatus.succeeded)
        self.assertTrue(execution.started_at < execution.stopped_at)
        self.assertTrue(execution.stopped_at < arrow.get())
        self.assertEqual(execution.input_data["__trace"]["id"], "abc")
        self.assertEqual(execution.input_data["__trace"]["source"], "the-alphabet")
        self.assertEqual(execution.input_data["hello"], "world")
        self.assertEqual(execution.input_data["fail"], False)
        self.assertEqual(
            without_trace(execution.output_data),
            {"hello": "world", "fail": False, "foo": "bar"},
        )

    @async_test
    async def test_07_start_execution__failure(self):
        """Should start an execution that will fail"""
        execution = self.workflow.executions.create("test-failure")
        await execution.start(input_data={"fail": True})
        # Give Step Functions a second (it's eventually consistent)
        await asyncio.sleep(1)
        await execution.fetch()
        self.assertEqual(execution.execution_id, "test-failure")
        self.assertEqual(execution.status, ExecutionStatus.failed)
        self.assertTrue(execution.started_at < execution.stopped_at)
        self.assertTrue(execution.stopped_at < arrow.get())
        self.assertIsNotNone(execution.input_data["__trace"]["id"])
        self.assertEqual(execution.input_data["__trace"]["source"], "manual")
        self.assertEqual(execution.input_data["fail"], True)
        self.assertEqual(execution.output_data, None)

    @async_test
    async def test_08_list_executions__missing_workflow(self):
        """Should raise when workflow does not exist"""
        with self.assertRaises(WorkflowDoesNotExist):
            await Workflow("test-nope").executions.fetch()

    @async_test
    async def test_09_list_executions__all(self):
        """Should list all executions for a workflow"""
        executions = await self.workflow.executions.fetch()
        ids = [e.execution_id for e in executions]
        self.assertEqual(ids, ["test-failure", "test-trace", "test-success"])

    @async_test
    async def test_10_list_executions__failed(self):
        """Should list all executions for a workflow"""
        executions = await self.workflow.executions.fetch(
            status_filter=ExecutionStatus.failed
        )
        ids = [e.execution_id for e in executions]
        self.assertEqual(ids, ["test-failure"])

    @async_test
    async def test_11_get_execution_history(self):
        """Should get execution history for an execution"""
        history = await self.workflow.executions.create("test-failure").events.fetch()
        last_event = history[-1]
        self.assertTrue(last_event.timestamp < arrow.get())
        self.assertEqual(last_event.event_type, ExecutionEventType.execution_failed)
        self.assertEqual(last_event.details["error"], "Bad")
        self.assertEqual(last_event.details["cause"], "Everything")


class FunctionalTestsWorkflowClientPolling(WorkflowClientFunctionalTestCase):
    """Functional tests for the polling behavior of the WorkflowClient class"""

    # This waits for a few seconds then succeeds
    STATE_MACHINE_DEFINITION = {
        "StartAt": "Wait",
        "States": {"Wait": {"Type": "Wait", "Seconds": 3, "End": True}},
    }

    @async_test
    async def test_poll_for_execution_status__succeeded(self):
        """Should wait until execution status changes to succeed"""
        execution = self.workflow.executions.create("test-polling-success")
        await execution.start()
        await execution.fetch()
        self.assertEqual(execution.status, ExecutionStatus.running)
        await execution.poll_for_status()
        self.assertEqual(execution.status, ExecutionStatus.succeeded)

    @async_test
    async def test_poll_for_execution_status__timeout(self):
        """Should raise when the execution fails to reach the given status"""
        execution = self.workflow.executions.create("test-polling-timeout")
        await execution.start()
        with self.assertRaises(PollForExecutionStatusTimedOut) as cm:
            await execution.poll_for_status(
                statuses={ExecutionStatus.failed}, max_time=1, interval=1
            )
        self.assertIn("test-polling-timeout", str(cm.exception))
        self.assertIn("failed to converge", str(cm.exception))

    @async_test
    async def test_poll_for_execution_status__failed(self):
        """Should raise when the execution completes with an unexpected status"""
        execution = self.workflow.executions.create("test-polling-failed")
        await execution.start()
        with self.assertRaises(PollForExecutionStatusFailed) as cm:
            await execution.poll_for_status(
                statuses={ExecutionStatus.failed}, max_time=5, interval=1
            )
        self.assertIn("test-polling-failed", str(cm.exception))
        self.assertIn("failed to converge", str(cm.exception))

    @async_test
    async def test_stop(self):
        """Should stop a running execution"""
        execution = self.workflow.executions.create("test-stop")
        await execution.start()
        await execution.stop()
        self.assertEqual(execution.status, ExecutionStatus.aborted)


if __name__ == "__main__":
    unittest.main()
