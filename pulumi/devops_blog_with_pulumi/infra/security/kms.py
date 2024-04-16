import pulumi
import pulumi_aws as aws


class KMSComponent(pulumi.ComponentResource):
    def __init__(self, name, project_name, base_tags, opts=None):
        super().__init__("devopsinthecloud:utils:kms", name, None, opts)

        self.base_tags = base_tags
        self.project_name = project_name

        self.kms_rds = aws.kms.Key(
            f"{self.project_name}-kms-rds-key",
            description="KMS key for RDS",
            enable_key_rotation=True,
            tags={**self.base_tags, "Name": f"{self.project_name}-kms-rds-key"},
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.kms_rds_alias = aws.kms.Alias(
            f"{self.project_name}-kms-rds-key-alias",
            name=f"alias/{project_name}-rds-kms-key",
            target_key_id=self.kms_rds.id,
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Add the Key to SSM Parameter Store

        aws.ssm.Parameter(
            f"{self.project_name}-kms-rds-key",
            type="String",
            name=f"/prod/{self.project_name}-kms-rds-key",
            value=self.kms_rds.id,
            description="KMS key for RDS",
            opts=pulumi.ResourceOptions(parent=self),
            tags={**self.base_tags, "Name": f"{self.project_name}-kms-rds-key"},
        )

        self.register_outputs({"kms-rds-key": self.kms_rds.id})
