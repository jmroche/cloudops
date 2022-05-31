"""
Stack to create a configure Security Groups and Roles that will be sued in other stacks.
"""
import json
import os

from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_eks as eks
from aws_cdk import aws_iam as iam
from aws_cdk import CfnOutput
from aws_cdk import Stack
from constructs import Construct
from constructs import Node

from .addons.flux2_stack import FluxStack

# from rds_stack import RDSStack
# from vpc_stack import VPCStack


class SecurityStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, vpc: ec2.Vpc, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a Security Group for the PODS that will run on the Node Group
        self.pod_sg = ec2.SecurityGroup(
            self,
            "POD-SG",
            vpc=vpc,
            description="Security Group for PODS",
            security_group_name="POD_SG",
            allow_all_outbound=True,
        )

        # Add inbound rule to port 5000 to all IPv4 address.

        self.pod_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(5000),
            description="Allow TCP port 5000 from anywhere to access the flask-blog app.",
        )

        self.rds_sg = ec2.SecurityGroup(
            self,
            "RDS-SG",
            vpc=vpc,
            description="RDS Security Group",
            security_group_name="RDS_SG",
        )

        self.rds_sg.add_ingress_rule(
            peer=self.pod_sg,
            connection=ec2.Port.tcp(3306),
            description="Allow POD_SG to access RDS_SG on port 3306",
        )

        # Create SecurityGroup for bastion
        self.bastion_sg = ec2.SecurityGroup(
            self, "Bastion-SG", vpc=vpc, allow_all_outbound=True
        )

        # Create IAM Role to be used for the EKS Cluster and Bastion host

        cluster_admin_role = iam.Role(
            self,
            "ClusterAdminRole",
            assumed_by=iam.CompositePrincipal(
                iam.AccountRootPrincipal(), iam.ServicePrincipal("ec2.amazonaws.com")
            ),
        )

        cluster_admin_policy_statement_json_1 = {
            "Effect": "Allow",
            "Action": ["eks:DescribeCluster"],
            "Resource": "*",
        }

        cluster_admin_role.add_to_policy(
            iam.PolicyStatement.from_json(cluster_admin_policy_statement_json_1)
        )

        cluster_admin_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKSClusterPolicy")
        )

        cluster_admin_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonEKSVPCResourceController"
            )
        )

        cluster_admin_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore"
            )
        )

        cluster_admin_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore"
            )
        )

        # Export the Role ARN for EKS and Bastion stacks to consume
        CfnOutput(
            self,
            "cluster_role_role",
            value=cluster_admin_role.role_arn,
            description="EKS and Bastion Admin Role",
            export_name="eks-bastion-role",
        )

        # Export POD_SG Security Group Id to be used by other stacks
        # EKS Stack consumes this outout

        CfnOutput(
            self,
            "podsg-id-export",
            value=self.pod_sg.security_group_id,
            description="POD_SG security group id export.",
            export_name="podsg-id",
        )
