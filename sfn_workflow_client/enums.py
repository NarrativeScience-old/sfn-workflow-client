"""Contains enums related to workflows and executions"""
from aenum import UniqueEnum


class ExecutionStatus(UniqueEnum):
    """Workflow execution statuses"""

    aborted = "ABORTED"
    failed = "FAILED"
    running = "RUNNING"
    succeeded = "SUCCEEDED"
    timed_out = "TIMED_OUT"


# Set of statuses that indicate an execution completed
COMPLETED_STATUSES = {
    ExecutionStatus.aborted,
    ExecutionStatus.failed,
    ExecutionStatus.succeeded,
    ExecutionStatus.timed_out,
}


class ExecutionEventType(UniqueEnum):
    """Execution history event type."""

    choice_state_entered = "ChoiceStateEntered"
    choice_state_exited = "ChoiceStateExited"
    execution_aborted = "ExecutionAborted"
    execution_failed = "ExecutionFailed"
    execution_started = "ExecutionStarted"
    execution_succeeded = "ExecutionSucceeded"
    execution_timed_out = "ExecutionTimedOut"
    fail_state_entered = "FailStateEntered"
    lambda_function_failed = "LambdaFunctionFailed"
    lambda_function_schedule_failed = "LambdaFunctionScheduleFailed"
    lambda_function_scheduled = "LambdaFunctionScheduled"
    lambda_function_start_failed = "LambdaFunctionStartFailed"
    lambda_function_started = "LambdaFunctionStarted"
    lambda_function_succeeded = "LambdaFunctionSucceeded"
    lambda_function_timed_out = "LambdaFunctionTimedOut"
    parallel_state_aborted = "ParallelStateAborted"
    parallel_state_entered = "ParallelStateEntered"
    parallel_state_exited = "ParallelStateExited"
    parallel_state_failed = "ParallelStateFailed"
    parallel_state_started = "ParallelStateStarted"
    parallel_state_succeeded = "ParallelStateSucceeded"
    pass_state_entered = "PassStateEntered"
    pass_state_exited = "PassStateExited"
    succeed_state_entered = "SucceedStateEntered"
    succeed_state_exited = "SucceedStateExited"
    task_failed = "TaskFailed"
    task_scheduled = "TaskScheduled"
    task_start_failed = "TaskStartFailed"
    task_started = "TaskStarted"
    task_state_aborted = "TaskStateAborted"
    task_state_entered = "TaskStateEntered"
    task_state_exited = "TaskStateExited"
    task_submit_failed = "TaskSubmitFailed"
    task_submitted = "TaskSubmitted"
    task_succeeded = "TaskSucceeded"
    task_timed_out = "TaskTimedOut"
    wait_state_aborted = "WaitStateAborted"
    wait_state_entered = "WaitStateEntered"
    wait_state_exited = "WaitStateExited"
