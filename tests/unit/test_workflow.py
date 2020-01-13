"""Contains unit tests for the Workflow class"""

import os
import unittest

from sfn_workflow_client.workflow import Workflow


class WorkflowUnitTests(unittest.TestCase):
    """Unit tests for the Workflow class"""

    def test_init(self):
        """Should set initial attributes"""
        workflow = Workflow("test")
        self.assertEqual(workflow.name, "test")
        self.assertEqual(
            workflow.state_machine_arn,
            f"arn:aws:states:{os.environ.get('AWS_DEFAULT_REGION')}:{os.environ.get('AWS_ACCOUNT_NUMBER')}:stateMachine:test",
        )
        self.assertEqual(len(workflow.executions), 0)


if __name__ == "__main__":
    unittest.main()
