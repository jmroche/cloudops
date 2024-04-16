"""An AWS Python Pulumi program"""
import pulumi
from compute.eks import EKSComponent
from pulumi_aws import s3
from security.kms import KMSComponent
from security.security import SecurityComponent
from storage.ecr import ECRComponent
from storage.rds import RDSComponent
from vpc.vpc import VPCComponent

config = pulumi.Config()
base_tags = config.require_object("tags")
project_name = config.require("projectName")
aurora_instances_qty = config.require_object("aurora_instance_number")
aurora_instance_type = config.require("aurora_instance_type")
aurora_instance_storage = str(config.require_object("aurora_instance_storage"))


# Create a DEV VPC

pro_vpc = VPCComponent(
    "dev-vpc",
    cidr_block="10.1.0.0/16",
    project_name=project_name,
    subnet_number=3,
    base_tags=base_tags,
)

prod_security = SecurityComponent(
    "security-components",
    vpc_id=pro_vpc.vpc.id,
    base_tags=base_tags,
    project_name=project_name,
)

prod_kms_key = KMSComponent(
    "kms-rds-key",
    base_tags=base_tags,
    project_name=project_name,
)

prod_rds_cluster = RDSComponent(
    "aurora-mysql-cluster",
    vpc_id=pro_vpc.vpc.id,
    kms_key_id=prod_kms_key.kms_rds.arn,
    db_subnets=pro_vpc.database_subnets,
    project_name=project_name,
    base_tags=base_tags,
    security_group_id=prod_security.rds_sg.id,
    db_qty=aurora_instances_qty,
    instance_type=aurora_instance_type,
)

prod_ecr_repo = ECRComponent(
    "prod-ecr-repo",
    project_name=project_name,
    base_tags=base_tags,
)


eks_cluster_props = {
    "name": config.require("eks_cluster_name"),
    "version": config.require("eks_cluster_version"),
    "instance_type": config.require("eks_cluster_node_type"),
    "eks_cluster_min_node_number": config.require("eks_cluster_min_node_number"),
    "eks_cluster_max_node_number": config.require("eks_cluster_max_node_number"),
    "node_root_volume_size": config.require("node_root_volume_size"),
    "cluster_role": prod_security.eks_cluster_admin_role,
    "worker_role": prod_security.eks_worker_admin_role,
}


prod_eks_cluster = EKSComponent(
    "prod-eks-cluster",
    project_name=project_name,
    base_tags=base_tags,
    # cluster_subnets=pro_vpc.application_subnets,
    pods_sg_id=prod_security.pod_sg.id,
    vpc_id=pro_vpc.vpc.id,
    eks_cluster_props=eks_cluster_props,
    application_subnets=pro_vpc.application_subnets,
)
