"""
Minimal SigV4 helper for calling Mantle HTTP surfaces without the OpenAI SDK.

The OpenAI SDK only supports Bearer-token auth, so SigV4 is the path used when
you want a pure-IAM pipeline (no bearer tokens, no extra rotation).

Service name stays ``bedrock`` even though the IAM prefix is ``bedrock-mantle`` —
this matches the ``--service-name bedrock.amazonaws.com`` documented for
long-term Bedrock API key creation.
"""

from __future__ import annotations

import json
from typing import Any

import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


_SIGV4_SERVICE = "bedrock"


def sigv4_post(
    region: str,
    path: str,
    payload: dict[str, Any],
    extra_headers: dict[str, str] | None = None,
    timeout: int = 60,
    stream: bool = False,
) -> requests.Response:
    """
    POST a JSON payload to ``https://bedrock-mantle.{region}.api.aws{path}``
    with SigV4 signing. Returns the ``requests.Response`` (call ``.json()`` or
    iterate ``iter_lines()`` for SSE).
    """
    url = f"https://bedrock-mantle.{region}.api.aws{path}"
    body = json.dumps(payload).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)

    aws_req = AWSRequest(method="POST", url=url, data=body, headers=headers)
    creds = boto3.Session().get_credentials().get_frozen_credentials()
    SigV4Auth(creds, _SIGV4_SERVICE, region).add_auth(aws_req)

    return requests.post(
        url,
        data=body,
        headers=dict(aws_req.headers.items()),
        timeout=timeout,
        stream=stream,
    )
