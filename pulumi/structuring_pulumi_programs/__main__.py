"""An AWS Python Pulumi program"""

import pulumi
from vpc.vpc import VPCComponent
from compute.ec2 import EC2Component

config = pulumi.Config()
base_tags = config.require_object("tags")

# Create a DEV VPC

dev_vpc = VPCComponent(
    "dev-vpc",
    cidr_block="10.1.0.0/16",
    project_name="dev-app",
    subnet_number=3,
    base_tags=base_tags,
)


# Create a DEV EC2 Instance inside the DEV VPC application subnet
dev_instance = EC2Component(
    "dev-instance",
    project_name="dev-app",
    base_tags=base_tags,
    subnet=dev_vpc.application_subnets[0],
    security_group=dev_vpc.application_sg,
)
