"""
Stack that creates the Elastic Container Registry (ECR) to
push images from GitHub Actions and deploy them to EKS via GitOps.
"""
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ssm as ssm
from aws_cdk import CfnOutput
from aws_cdk import RemovalPolicy
from aws_cdk import Stack
from constructs import Construct


class ECRStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        project_name = self.node.try_get_context("project_name")

        self.ecr_repo = ecr.Repository(
            self,
            "flask-blog-ecr-repo",
            image_scan_on_push=True,
            repository_name=f"{project_name}-image-repo",
            removal_policy=RemovalPolicy.DESTROY,
            empty_on_delete=True,
        )

        self.cfn_output_ecr_uri = CfnOutput(
            self,
            "ecr-repo-uri",
            description="ECR Repository URI",
            export_name="ecr-repo-uri",
            value=self.ecr_repo.repository_uri,
        )

        ssm.StringParameter(
            self,
            "ecr-repo-arn",
            parameter_name=f"/{project_name}/ecrrepository-arn",
            string_value=self.ecr_repo.repository_arn,
        )
