import json

import pulumi
import pulumi_aws as aws


# Create a Pulumi RDS Component Resource

config = pulumi.Config()


class RDSComponent(pulumi.ComponentResource):
    def __init__(
        self,
        name,
        vpc_id,
        project_name,
        kms_key_id,
        security_group_id,
        db_subnets: list,
        db_qty: int,
        instance_type: str,
        base_tags,
        opts=None,
    ):
        super().__init__("devopsinthecloud:utils:database", name, None, opts)

        self.vpc_id = vpc_id
        self.project_name = project_name
        self.kms_key_id = kms_key_id
        self.base_tags = base_tags
        self.security_group_id = security_group_id
        self.db_subnets = db_subnets
        self.db_qty = db_qty
        self.instance_type = instance_type

        # Create a Secret to store RDS username and password

        json_template = {"username": "admin"}

        # Create an Aurora MySQL Cluster

        self.rds_aurora_cluster = aws.rds.Cluster(
            f"{self.project_name}-rds-aurora-cluster",
            engine="aurora-mysql",
            engine_version="8.0.mysql_aurora.3.04.1",
            cluster_identifier=f"{self.project_name}-rds-aurora-cluster",
            db_cluster_parameter_group_name="default.aurora-mysql8.0",
            database_name="devopsblogprod",
            storage_encrypted=True,
            kms_key_id=self.kms_key_id,
            db_subnet_group_name=aws.rds.SubnetGroup(
                f"{self.project_name}-rds-aurora-cluster-subnet-group",
                subnet_ids=[subnet.id for subnet in self.db_subnets],
                opts=pulumi.ResourceOptions(parent=self),
                name=f"{self.project_name}-rds-aurora-cluster-subnet-group",
            ),
            master_username="admin",
            manage_master_user_password=True,
            master_user_secret_kms_key_id=self.kms_key_id,
            backup_retention_period=7,
            backtrack_window=24,
            vpc_security_group_ids=[self.security_group_id],
            skip_final_snapshot=True,
            opts=pulumi.ResourceOptions(parent=self),
            # tags=[aws_native.TagArgs(key="auto-delete", value="never"), aws_native.TagArgs(key="Name", value=f"{self.project_name}-aurora-cluster")],
            tags={**self.base_tags, "Name": f"{self.project_name}-rds-aurora-cluster"},
        )

        # AWS Aurora Cluster Instances

        for qty in range(self.db_qty):
            aws.rds.ClusterInstance(
                f"{self.project_name}-rds-aurora-cluster-instance-{qty}",
                cluster_identifier=self.rds_aurora_cluster.id,
                identifier=f"{self.project_name}-rds-aurora-cluster-instance-{qty}",
                db_subnet_group_name=self.rds_aurora_cluster.db_subnet_group_name,
                instance_class=self.instance_type,
                auto_minor_version_upgrade=True,
                engine="aurora-mysql",
                engine_version="8.0.mysql_aurora.3.04.1",
                tags={
                    **self.base_tags,
                    "Name": f"{self.project_name}-rds-aurora-cluster-instance-{qty}",
                },
                opts=pulumi.ResourceOptions(parent=self),
            )

        rds_hostname_ssm = aws.ssm.Parameter(
            f"{self.project_name}-rds-hostname-ssm-parameter",
            type="String",
            name=f"/prod/{self.project_name}/db-hostname",
            value=self.rds_aurora_cluster.endpoint,
            opts=pulumi.ResourceOptions(parent=self),
            tags={
                **self.base_tags,
                "Name": f"{self.project_name}-rds-aurora-cluster-hostname",
            },
        )

        self.register_outputs(
            {
                "rds-aurora-cluster-endpoint": self.rds_aurora_cluster.endpoint,
                "rds-aurora-cluster-master_user_secret_arn": self.rds_aurora_cluster.master_user_secrets[
                    0
                ][
                    "secret_arn"
                ],
            }
        )

        pulumi.export(
            "rds-aurora-cluster-user-pass",
            self.rds_aurora_cluster.master_user_secrets[0]["secret_arn"],
        )
