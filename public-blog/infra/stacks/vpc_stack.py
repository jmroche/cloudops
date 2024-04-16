"""
Stack that creates the VPCs for the needed envioronments.
"""
from aws_cdk import aws_ec2 as ec2
from aws_cdk import CfnOutput
from aws_cdk import Stack
from constructs import Construct


class VPCStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        project_name = self.node.try_get_context("project_name")

        self.vpc = ec2.Vpc(
            self,
            "blog-vpc",
            cidr="10.29.0.0/16",
            max_azs=3,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    cidr_mask=24, name="Public", subnet_type=ec2.SubnetType.PUBLIC
                ),
                ec2.SubnetConfiguration(
                    cidr_mask=24,
                    name="Application",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                ),
                ec2.SubnetConfiguration(
                    cidr_mask=24, name="DB", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                ),
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True,
            vpc_name=f"{project_name}-vpc"
            # nat_gateway_subnets=ec2.SubnetSelection(ec2.SubnetType.PUBLIC),
        )

        self.cfn_output_vpc_id = CfnOutput(
            self,
            "vpcid",
            description="VPC Id for the blog app",
            export_name="vpcid",
            value=self.vpc.vpc_id,
        )
