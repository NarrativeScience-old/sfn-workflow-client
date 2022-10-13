"""Contains unit tests for the Execution class"""

import unittest
from unittest.mock import patch

import arrow

from sfn_workflow_client.enums import ExecutionStatus
from sfn_workflow_client.exceptions import InvalidExecutionInputData
from sfn_workflow_client.workflow import Workflow
from ..test_utils import async_test, create_future_method


class ExecutionUnitTests(unittest.TestCase):
    """Unit tests for the Execution class"""

    def setUp(self):
        """Test setup"""
        self.workflow = Workflow("test")

    def test_trace_id__set(self):
        """Should return trace id"""
        execution = self.workflow.executions.create(
            execution_id="abc",
            status=ExecutionStatus.running,
            started_at=arrow.get(),
            input_data={"__trace": {"id": "def"}},
        )
        self.assertEqual(execution.trace_id, "def")

    def test_trace_id__unset(self):
        """Should return none if no trace id"""
        execution = self.workflow.executions.create(
            execution_id="abc", status=ExecutionStatus.running, started_at=arrow.get()
        )
        self.assertEqual(execution.trace_id, None)

    def test_trace_source__set(self):
        """Should return trace source"""
        execution = self.workflow.executions.create(
            execution_id="abc",
            status=ExecutionStatus.running,
            started_at=arrow.get(),
            input_data={"__trace": {"source": "def"}},
        )
        self.assertEqual(execution.trace_source, "def")

    def test_trace_source__unset(self):
        """Should return none if no trace source"""
        execution = self.workflow.executions.create(
            execution_id="abc", status=ExecutionStatus.running, started_at=arrow.get()
        )
        self.assertEqual(execution.trace_source, None)

    @async_test
    async def test_start_execution__invalid_input(self):
        """Should raise on invalid input data"""
        execution = self.workflow.executions.create()
        with self.assertRaises(InvalidExecutionInputData):
            await execution.start(input_data=range(1))
        with self.assertRaises(InvalidExecutionInputData):
            await execution.start(input_data=True)


class ExecutionCollectionUnitTests(unittest.TestCase):
    """Unit tests for the ExecutionCollection class"""

    def setUp(self):
        """Test setup"""
        self.workflow = Workflow("test")
        items = [
            {"execution_id": "b", "input_data": {"__trace": {"id": "b"}}},
            {"execution_id": "c", "input_data": {"__trace": {"id": "c"}}},
            {"execution_id": "a", "input_data": {"__trace": {"id": "a"}}},
        ]
        self.workflow.executions._items = [
            self.workflow.executions.create(**item) for item in items
        ]

    @patch("sfn_workflow_client.execution.Execution.fetch")
    @async_test
    async def test_find_by_trace_id__found(self, mock_fetch):
        """Should return the execution"""
        create_future_method(mock_fetch)
        execution = await self.workflow.executions.find_by_trace_id("b")
        self.assertEqual(execution.execution_id, "b")

    @patch("sfn_workflow_client.execution.Execution.fetch")
    @async_test
    async def test_find_by_trace_id__missing(self, mock_fetch):
        """Should return none"""
        create_future_method(mock_fetch)
        self.assertIsNone(await self.workflow.executions.find_by_trace_id("f"))


if __name__ == "__main__":
    unittest.main()
