"""Constants and configuration for the workflow client"""
import os

AWS_ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID")

# URL for making requests to the Step Functions API. You would most likely only set
# this in order to hit the local py2sfn mock server.
# "The complete URL to use for the constructed client. Normally, botocore will
# automatically construct the appropriate URL to use when communicating with a service."
# See: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/core/session.html#boto3.session.Session.client
STEPFUNCTIONS_ENDPOINT_URL = os.environ.get("STEPFUNCTIONS_ENDPOINT_URL")
