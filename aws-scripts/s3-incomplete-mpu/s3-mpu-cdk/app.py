#!/usr/bin/env python3
import os

import aws_cdk as cdk

from stacks.s3_mpu_cdk_stack import S3MpuCdkStack


app = cdk.App()
S3MpuCdkStack(
    app,
    "S3MpuCdkStack",
)

app.synth()
