from aws_cdk import (
    # Duration,
    BundlingOptions,
    Stack,
    aws_events as eb,
    aws_events_targets as eb_targets,
    aws_sns as sns,
    aws_iam as iam,
    aws_lambda as _lambda,
    Duration,
)
from constructs import Construct


class S3MpuCdkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define the Lambda resource
        # Lambda function is inside lmabda directory
        # It will be built using Docker to bundle the requirements file

        s3_incomplete_mpu_lambda = _lambda.Function(
            self,
            "S3IncompleteMPULambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset(
                "lambda",
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_9.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output",
                    ],
                ),
            ),
            handler="s3-incomplete-mpu.handler",
        )

        # Allow Lambda to apply the lifecycle configuration to S3 buckets

        s3_incomplete_mpu_lambda.role.add_to_principal_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:PutLifecycleConfiguration"],
                resources=["*"],
            )
        )

        # Create a new EventBridge rule to monitor CloudTrail for a specific S3 CreateBucket API call

        create_bucket_rule = eb.Rule(
            self,
            "CloudTrailS3CreateBucket",
            description="Rule to trigger when CloudTrail detects an S3 CreateBucket API call.",
            event_bus=eb.EventBus.from_event_bus_name(
                self, "EventBusName", event_bus_name="default"
            ),
            rule_name="s3-bucket-created",
            event_pattern=eb.EventPattern(
                source=["aws.s3"],
                detail_type=["AWS API Call via CloudTrail"],
                detail={
                    "eventSource": ["s3.amazonaws.com"],
                    "eventName": ["CreateBucket"],
                },
            ),
            targets=[
                eb_targets.LambdaFunction(
                    s3_incomplete_mpu_lambda,
                    max_event_age=Duration.hours(2),
                    retry_attempts=2,
                )
            ],
        )

        # Allow Lambda to be invoked by EventBridge rule

        s3_incomplete_mpu_lambda.grant_invoke(
            iam.ServicePrincipal(
                service="events.amazonaws.com",
                conditions={"ArnLike": {"AWS:SourceArn": create_bucket_rule.rule_arn}},
            )
        )
