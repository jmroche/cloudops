"""
Entry point for Stack deployments. Here we define the stack constructs and orchestrate the deployment.
"""
from aws_cdk import Stack
from aws_cdk import Tags
from constructs import Construct
from constructs import Node

from .addons.external_dns import ExternalDNSStack
from .bastion_stack import BastionStack
from .ecr_stack import ECRStack
from .eks_stack import EKSStack
from .kms_stack import KMSStack
from .rds_stack import RDSStack
from .security_stack import SecurityStack
from .vpc_stack import VPCStack


class InfraStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        project_name = self.node.try_get_context("project_name")

        test_env = self.node.try_get_context("test")
        test_env_name = test_env["env_name"]

        prod_env = self.node.try_get_context("production")
        prod_env_name = prod_env["env_name"]

        kms_stack = KMSStack(self, "KMSStack", env_name=test_env_name)
        vpc_stack = VPCStack(self, "VPCStack")
        security_stack = SecurityStack(self, "SecurityStack", vpc=vpc_stack.vpc)
        ecr_stack = ECRStack(self, "ECRStack")
        dev_rds_stack = RDSStack(
            self,
            "TestRDSStack",
            vpc=vpc_stack.vpc,
            env_name=test_env_name,
            project_name=project_name,
            kmskey=kms_stack.kms_rds,
            security_group=security_stack.rds_sg,
        )
        test_creds_secret_arn = dev_rds_stack.db_creds_secret_arn
        test_db_hostname_arn = dev_rds_stack.rds_hostname_ssm_arn

        prod_rds_stack = RDSStack(
            self,
            "ProdRDSStack",
            vpc=vpc_stack.vpc,
            env_name=prod_env_name,
            project_name=project_name,
            kmskey=kms_stack.kms_rds,
            security_group=security_stack.rds_sg,
        )

        prod_creds_secret_arn = prod_rds_stack.db_creds_secret_arn
        prod_db_hostname_arn = prod_rds_stack.rds_hostname_ssm_arn

        eks_stack = EKSStack(
            self,
            "EKSStack",
            vpc=vpc_stack.vpc,
            pod_sg=security_stack.pod_sg,
            rds_sg=security_stack.rds_sg,
            bastion_sg=security_stack.bastion_sg,
            ecr_repo=ecr_stack.ecr_repo,
            kmskey=kms_stack.kms_rds,
            test_creds_secret_arn=test_creds_secret_arn,
            test_db_hostname_arn=test_db_hostname_arn,
            prod_creds_secret_arn=prod_creds_secret_arn,
            prod_db_hostname_arn=prod_db_hostname_arn,
        )
        # eks_stack.tags.set_tag("auto-delete", "never")
        Tags.of(eks_stack).add("auto-delete", "never")

        external_dns_stack = ExternalDNSStack(
            self, "ExternalDNSStack", cluster=eks_stack.eks_cluster
        )

        external_dns_stack.node.add_dependency(eks_stack)

        bastion_stack = BastionStack(
            self,
            "BastionStack",
            cluster=eks_stack.eks_cluster,
            vpc=vpc_stack.vpc,
            bastion_sg=security_stack.bastion_sg,
        )

        bastion_stack.add_dependency(eks_stack)  # ensure EKS Stack is built first

        Tags.of(bastion_stack).add("auto-delete", "never")
