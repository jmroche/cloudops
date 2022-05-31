"""
Stack to create an Aurora MySQL Database Cluster for the Test and Production environments.
"""
import json

from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_rds as rds
from aws_cdk import aws_secretsmanager as sm
from aws_cdk import aws_ssm as ssm
from aws_cdk import Duration
from aws_cdk import RemovalPolicy
from aws_cdk import Stack
from constructs import Construct


class RDSStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.Vpc,
        env_name: str,
        project_name: str,
        kmskey: kms.Key,
        security_group: ec2.SecurityGroup,
        **kwargs,
    ) -> None:

        super().__init__(scope=scope, id=id, **kwargs)

        # project_name = self.node.try_get_context("project_name")
        # env_name = self.node.try_get_context("env")

        # Create a templte for secrets manager to use as the base to create a secret
        json_template = {"username": "admin"}

        env_settings = self.node.try_get_context(env_name)

        self.db_creds = sm.Secret(
            self,
            "rds_secret",
            description="RDS Password",
            encryption_key=kmskey,
            secret_name=f"{env_name}-rds-secret",
            generate_secret_string=(
                sm.SecretStringGenerator(
                    include_space=False,
                    password_length=12,
                    generate_string_key="password",
                    exclude_punctuation=True,
                    secret_string_template=json.dumps(json_template),
                )
            ),
        )

        self.db_creds_secret_arn = self.db_creds.secret_arn

        if env_name == "test":
            rds_removal_policy = RemovalPolicy.DESTROY
            rds_backtrack_window = None

        else:
            rds_removal_policy = RemovalPolicy.DESTROY
            rds_backtrack_window = Duration.minutes(
                env_settings["rds"]["backtrack_window"]
            )

        # Create Aurora MysQL Cluster
        db_aurora_mysql = rds.DatabaseCluster(
            self,
            "auroramysql",
            default_database_name=f"{project_name}{env_name}",
            engine=rds.DatabaseClusterEngine.aurora_mysql(
                version=rds.AuroraMysqlEngineVersion.VER_2_10_1
            ),
            instances=1,
            storage_encrypted=True,
            storage_encryption_key=kmskey,
            # credentials=rds.Credentials.from_generated_secret(
            #     username="admin", encryption_key=kmskey
            # ),
            credentials=rds.Credentials.from_secret(self.db_creds),
            instance_props=rds.InstanceProps(
                vpc=vpc,
                vpc_subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                ),
                instance_type=ec2.InstanceType.of(
                    ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MEDIUM
                ),
                parameter_group=rds.ParameterGroup.from_parameter_group_name(
                    self,
                    f"pg-{env_name}",
                    parameter_group_name="default.aurora-mysql5.7",
                ),
                security_groups=[security_group],
            ),
            backup=rds.BackupProps(
                retention=Duration.days(env_settings["rds"]["backup"])
            ),
            backtrack_window=rds_backtrack_window,
            removal_policy=rds_removal_policy,
        )

        # db_aurora_mysql.connections.allow_default_port_from(
        #     lambdasg, description="Access from Lambda functions"
        # )
        # db_aurora_mysql.connections.allow_default_port_from(
        #     bastionsg, description="Allow access from Bastion"
        # )

        # Create an RDS Security Group in order to later allow Pod SG and RDS SG to talk

        # self.rds_sg = ec2.SecurityGroup(
        #     self,
        #     "RDS-SG",
        #     vpc=vpc,
        #     description="RDS Security Group",
        #     security_group_name="RDS_SG",
        # )

        # Strore db cluster hostname in parameter store
        rds_hostname_ssm = ssm.StringParameter(
            self,
            "rds-parameter",
            parameter_name=f"/{project_name}/{env_name}/db-hostname",
            string_value=db_aurora_mysql.cluster_endpoint.hostname,
        )

        self.rds_hostname_ssm_arn = rds_hostname_ssm.parameter_arn
