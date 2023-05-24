"""
Using AWS Boto3 create the following:
An SNS topic with to notify the user of a change in the AWS EKS Parameter
An SNS subscription for the topic with the email address "XXXXXXXXXXXXXXXXXXXXXXXXXX"
Read the value of the official AWS EKS Parameter "image_id"
Create an EventBridge rule using the default event bus.
Create an EventBridge target to the SNS topic to inform the recipients that new AMI has been released
for the specified Kubernetes version.
"""


import boto3
import json
from botocore.config import Config
from botocore.exceptions import ClientError
from datetime import datetime
import logging
import sys


logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s: %(message)s",
)
logger = logging.getLogger()


AWS_EKS_VERSION = "1.26"
REGION = "us-east-1"
PARAMETER_NAME = f"/aws/service/eks/optimized-ami/{AWS_EKS_VERSION}/amazon-linux-2/recommended/image_id"
RUN_LOCAL = True
SNS_EMAIL_ENDPOINT = "test@email.com"  # Add email address to send notifications to.

######## Setup Localstack ########

endpoint_url = "http://localhost.localstack.cloud:4566"

# localstack_config = Config(
#     region_name=REGION,
#     signature_version="v4",
#     endpoint_url=endpoint_url,
#     retries={"max_attempts": 10, "mode": "standard"},
# )
##################################


# SNS Input message

# sns_target_message_template = {
#     "default": {
#         "message": "New EKS AMI has been released!",
#         "subject": "New EKS AMI Released",
#         "iamge_id": "",
#         "release_date": ""
#     }
# }


def create_boto3_client_session(service_name: str, run_local=RUN_LOCAL):
    """Cheks if we are running locally using localstack or in AWS.
        If we are running locally we set the endpoint to point to localstack endpoint.

    Args:
            service_name (str): Servie name to create the client for (e.g. ec2, s3, sns, etc.)
            run_local (bool, optional): Run locally? Defaults to False.

    Returns:
            boto3.client: A boto3 client for the service requested.

    """

    if run_local:
        logger.info(f"Creating boto3 client for {service_name} in localstack")
        return boto3.client(service_name, endpoint_url=endpoint_url)
    else:
        logger.info(f"Creating boto3 client for {service_name} in AWS")
        return boto3.client(service_name)


# SNS TOPIC


def create_sns_topic(name: str) -> dict:
    """Create an SNS topic for eventBridge to publish to.

    Returns:
        dict: SNS topic ARN.
    """
    sns_client = create_boto3_client_session(service_name="sns")

    try:
        topic = sns_client.create_topic(Name=name)
        logger.info(f"Created SNS topic {topic}")
        topic_arn = topic["TopicArn"]
    except ClientError:
        logger.exception("Failed to create SNS topic {topic}")
        raise
    else:
        return topic


def create_sns_subscription(topic_arn: str, endpoint: str):
    """Create an SNS subscription for the topic.

    Args:
        topic_arn (str): SNS topic ARN.
        endpoint (str): SNS subscription endpoint.

    Returns:
        dict: SNS subscription dictionary.
    """
    sns_client = create_boto3_client_session(service_name="sns")

    try:
        subscription = sns_client.subscribe(
            TopicArn=topic_arn, Protocol="email", Endpoint=endpoint
        )
        logger.info(f"Created SNS subscription {subscription}")
    except ClientError:
        logger.exception("Failed to create SNS subscription")
        raise
    else:
        return subscription


# Update SNS Topic Policy to allow eventBridge to publish to SNS topic
# https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html#eb-sns-permissions


def get_sns_topic_attributes(topic_arn: str) -> dict:
    """Get the SNS topic attributes.

    Args:
        topic_arn (str): SNS topic ARN.

    Returns:
        dict: SNS topic attributes dictionary.
    """
    sns_client = create_boto3_client_session(service_name="sns")

    try:
        topic_attributes = sns_client.get_topic_attributes(TopicArn=topic_arn)
        logger.info(f"Got SNS topic attributes {topic_attributes}")
    except ClientError:
        logger.exception("Failed to get SNS topic attributes")
        raise
    else:
        return topic_attributes


# Set topic policy to allow eventBridge to publish to SNS topict_attributes


def set_sns_topic_attributes(topic_arn: str, topic_attributes: dict):
    """Set the SNS topic attributes.

    Args:
        topic_arn (str): SNS topic ARN.
        topic_attributes (dict): New SNS topic policy.
    """

    sns_publish_policy = {
        "Sid": "PublishEventsToMyTopic",
        "Effect": "Allow",
        "Principal": {"Service": "events.amazonaws.com"},
        "Action": "sns:Publish",
        "Resource": topic_arn,
    }
    topic_policy = json.loads(topic_attributes["Attributes"]["Policy"])
    new_topic_policy = topic_policy
    current_policy_statements = new_topic_policy["Statement"]
    current_policy_statements.append(sns_publish_policy)
    new_topic_policy["Statement"] = current_policy_statements
    new_topic_policy["Id"] = "EBS_SNS_Policy"

    if new_topic_policy["Id"] == topic_policy["Id"]:
        logger.info(f"SNS topic policy is the same as the current policy")
        return None

    sns_client = create_boto3_client_session(service_name="sns")

    try:
        topic_attributes = sns_client.set_topic_attributes(
            TopicArn=topic_arn,
            AttributeName="Policy",
            AttributeValue=f"{json.dumps(new_topic_policy)}",
        )
        logger.info(f"Set SNS topic attributes {topic_attributes}")
    except ClientError:
        logger.exception("Failed to set SNS topic attributes")
        raise
    else:
        return topic_attributes


# IAM role to allow eventBridge to publish to SNS topic
# https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-iam-roles.html

# iam_client = create_boto3_client_session(service_name="iam")
# iam_role = iam_client.create_role(
#     RoleName="EventBridgePublish",
#     AssumeRolePolicyDocument=json.dumps(
#         {
#             "Version": "2012-10-17",
#             "Statement": [
#                 {
#                     "Effect": "Allow",
#                     "Principal": {"Service": "events.amazonaws.com"},
#                     "Action": "sts:AssumeRole",
#                 },
#             ],
#         }
#     ),
# )

# iam_role_arn = iam_role["Role"]["Arn"]


# GET the SSM paramter and update EventBridge Rules and Targets


def get_eks_node_ami_version_parameter():
    """Get the EKS Managed Node AMI version parameter.

    Returns:
        dict: SSM parameter dictionary.
    """
    ssm_client = create_boto3_client_session(service_name="ssm", run_local=False)

    try:
        eks_node_ami_version_parameter = ssm_client.get_parameter(
            Name=PARAMETER_NAME, WithDecryption=True
        )
        logger.info(
            f"Got SSM parameter for Newest AMI for EKS v{AWS_EKS_VERSION}: {eks_node_ami_version_parameter['Parameter']['Value']}, released on: {eks_node_ami_version_parameter['Parameter']['LastModifiedDate'].strftime('%Y-%m-%d %H:%M:%S')}"
        )
    except ClientError:
        logger.exception("Failed to get SSM parameter")
        raise
    else:
        return eks_node_ami_version_parameter


# https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-cwe.html


def create_eventbridge_rule(name: str, description: str, event_pattern: str) -> dict:
    """Create the EventBridge rule.

    Returns:
        dict: EventBridge rule dictionary.
    """
    eventbridge_client = create_boto3_client_session(service_name="events")

    try:
        eventbridge_rule = eventbridge_client.put_rule(
            Name=name,
            Description=description,
            EventPattern=event_pattern,
        )
        logger.info(f"Created EventBridge rule {eventbridge_rule}")
    except ClientError:
        logger.exception("Failed to create EventBridge rule")
        raise
    else:
        return eventbridge_rule


def create_eventbridge_target(rule_name: str, topic_arn: str, input=None) -> dict:
    """Create the EventBridge target.

    Returns:
        dict: EventBridge target dictionary.
    """
    eventbridge_client = create_boto3_client_session(service_name="events")

    try:
        eventbridge_target = eventbridge_client.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    "Id": "EBS_SNS_Target",
                    "Arn": topic_arn,
                    # "Input": input,
                }
            ],
        )
        logger.info(f"Created EventBridge target {eventbridge_target}")
    except ClientError:
        logger.exception("Failed to create EventBridge target")
        raise
    else:
        return


if __name__ == "__main__":
    sns_topic = create_sns_topic(
        name=f"AWSEKSAMI-SSMParameterChangeDetection-v{AWS_EKS_VERSION.replace('.', '-')}"
    )
    sns_subscription = create_sns_subscription(
        topic_arn=sns_topic["TopicArn"], endpoint=SNS_EMAIL_ENDPOINT
    )
    sns_topic_attributes = get_sns_topic_attributes(topic_arn=sns_topic["TopicArn"])
    sns_topic_set_attributes = set_sns_topic_attributes(
        topic_arn=sns_topic["TopicArn"], topic_attributes=sns_topic_attributes
    )
    eks_node_ami_parameter = get_eks_node_ami_version_parameter()
    sns_target_message = {
        "default": {
            "message": "New EKS AMI has been released!",
            "subject": "New EKS AMI Released",
            "iamge_id": eks_node_ami_parameter["Parameter"]["Value"],
            "release_date": eks_node_ami_parameter["Parameter"][
                "LastModifiedDate"
            ].strftime("%Y-%m-%d %H:%M:%S"),
        }
    }

    event_bridge_rule_name = f"parameterChangeDetectionEKSManagedAMI-v{AWS_EKS_VERSION}"

    event_bridge_rule = create_eventbridge_rule(
        name=event_bridge_rule_name,
        description=f"Check for new versions of EKS Managed Node AMIs for v{AWS_EKS_VERSION}",
        event_pattern=json.dumps(
            {
                "source": ["aws.ssm"],
                "detail-type": ["Parameter Store Change"],
                "detail": {
                    "name": [PARAMETER_NAME],
                    "operation": [
                        "Create",
                        "Update",
                        "Delete",
                        "LabelParameterVersion",
                    ],
                },
            }
        ),
    )

    event_bridge_target = create_eventbridge_target(
        rule_name=event_bridge_rule_name,
        topic_arn=sns_topic["TopicArn"],
        # input=json.dumps(sns_target_message),
    )
