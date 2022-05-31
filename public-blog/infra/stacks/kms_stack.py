from aws_cdk import aws_kms as kms
from aws_cdk import aws_ssm as ssm
from aws_cdk import Stack
from constructs import Construct


class KMSStack(Stack):
    def __init__(self, scope: Construct, id: str, env_name: str, **kwargs) -> None:
        super().__init__(scope=scope, id=id, **kwargs)

        project_name = self.node.try_get_context("project_name")
        # env_name = self.node.try_get_context("env")

        # Create a kms key

        self.kms_rds = kms.Key(
            self,
            "rdskey",
            description=f"{project_name}-rds-kms-key",
            enable_key_rotation=True,
        )

        self.kms_rds.add_alias(alias_name=f"alias/{project_name}-rds-kms-key")

        # Store KMS in Parameter Store

        ssm.StringParameter(
            self,
            "rds-kms-key",
            parameter_name=f"/{env_name}/{project_name}-rds-kms-key",
            string_value=self.kms_rds.key_id,
            description="RDS KMS Key",
        )
