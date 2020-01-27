# sfn_workflow_client

[![](https://img.shields.io/pypi/v/sfn_workflow_client.svg)](https://pypi.org/pypi/sfn_workflow_client/) [![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

Enhanced, asyncio-compatible client for AWS Step Functions.

Features:

- Trigger new executions
- Query for state machine execution status
- Wait for an execution to complete
- Fetch execution history

Table of Contents:

- [Installation](#installation)
- [Guide](#guide)
- [Development](#development)

## Installation

sfn_workflow_client requires Python 3.6 or above.

```bash
pip install sfn_workflow_client
```

## Guide

```python
from sfn_workflow_client.enums import ExecutionStatus
from sfn_workflow_client.workflow import Workflow

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
```

## Development

To develop sfn_workflow_client, install dependencies and enable the pre-commit hook:

```bash
pip install pre-commit tox
pre-commit install
```

To run functional tests, you need to create an AWS IAM role with permissions to:

- Create/update/delete state machines
- Start/stop executions

Set the following environment variables:

- `AWS_ACCOUNT_ID`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`
- `AWS_IAM_ROLE_ARN`

To run tests:

```bash
tox
```
