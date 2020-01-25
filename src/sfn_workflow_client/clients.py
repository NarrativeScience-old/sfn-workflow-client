"""Contains shared clients used by the library"""

import boto3

from .config import STEPFUNCTIONS_ENDPOINT_URL

stepfunctions = boto3.client("stepfunctions", endpoint_url=STEPFUNCTIONS_ENDPOINT_URL)
