#!/usr/bin/env python3
from __future__ import annotations

import aws_cdk as cdk

from infra_cdk.backend_service_stack import BackendServiceStack


app = cdk.App()

account = app.node.try_get_context("account")
region = app.node.try_get_context("region")
env = cdk.Environment(account=account, region=region) if (account or region) else None

stack_name = app.node.try_get_context("stackName") or "CircuitBackendStack"
BackendServiceStack(
    app,
    stack_name,
    env=env,
    synthesizer=cdk.BootstraplessSynthesizer(),
)

app.synth()
