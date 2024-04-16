import pulumi
import pulumi_aws as aws


# Create a Pulumi VPC Component Resource


class VPCComponent(pulumi.ComponentResource):
    def __init__(
        self, name, cidr_block, project_name, subnet_number, base_tags, opts=None
    ):
        super().__init__("devopsinthecloud:utils:vpc", name, None, opts)

        self.cidr_block = cidr_block
        self.project_name = project_name
        self.subnet_number = subnet_number
        self.base_tags = base_tags

        """Create a VPC with thre subnets
        The VPC CIDR is 10.1.0.0/16
        The Subnet CIDRs are:
        Public: 10.1.0.0/22
        Application: 10.1.4.0/22
        Database: 10.1.8.0/22
        Spare: 10.1.12.0/22
        """

        self.vpc = aws.ec2.Vpc(
            f"{self.project_name}-main-vpc",
            cidr_block=self.cidr_block,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            tags={**self.base_tags, "Name": f"{self.project_name}-main-vpc"},
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.public_subnets = []
        self.application_subnets = []
        self.database_subnets = []
        availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

        for subnet in range(self.subnet_number):
            self.public_subnets.append(
                aws.ec2.Subnet(
                    f"{project_name}-public-subnet-{subnet}",
                    vpc_id=self.vpc.id,
                    cidr_block=f"10.1.{subnet}.0/24",
                    availability_zone=availability_zones[subnet],
                    tags={
                        **self.base_tags,
                        "Name": f"{self.project_name}-public-subnet-{subnet}",
                    },
                    opts=pulumi.ResourceOptions(parent=self),
                )
            )

            self.application_subnets.append(
                aws.ec2.Subnet(
                    f"{self.project_name}-application-subnet-{subnet}",
                    vpc_id=self.vpc.id,
                    cidr_block=f"10.1.{subnet + 4}.0/24",
                    availability_zone=availability_zones[subnet],
                    tags={
                        **self.base_tags,
                        "Name": f"{self.project_name}-application-subnet-{subnet}",
                    },
                    opts=pulumi.ResourceOptions(parent=self),
                )
            )

            self.database_subnets.append(
                aws.ec2.Subnet(
                    f"{self.project_name}-database-subnet-{subnet}",
                    vpc_id=self.vpc.id,
                    cidr_block=f"10.1.{subnet + 8}.0/24",
                    availability_zone=availability_zones[subnet],
                    tags={
                        **self.base_tags,
                        "Name": f"{self.project_name}-database-subnet-{subnet}",
                    },
                    opts=pulumi.ResourceOptions(parent=self),
                )
            )

        """Create a NAT Gateway and associate it with the public subnet"""

        # Create an Internet Gateway and attach it to the VPC
        self.igw = aws.ec2.InternetGateway(
            f"{self.project_name}-igw",
            vpc_id=self.vpc.id,
            tags={**self.base_tags, "Name": f"{self.project_name}-igw"},
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.eip = aws.ec2.Eip(
            f"{self.project_name}-eip",
            vpc=True,
            tags={**self.base_tags, "Name": f"{self.project_name}-eip"},
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Create a NAT Gateway and associate it with the public subnet

        self.nat_gw = aws.ec2.NatGateway(
            f"{self.project_name}-nat-gw",
            allocation_id=self.eip.id,
            subnet_id=self.public_subnets[0].id,
            tags={**self.base_tags, "Name": f"{self.project_name}-nat-gw"},
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.public_route_table = aws.ec2.RouteTable(
            f"{self.project_name}-public-route-table",
            vpc_id=self.vpc.id,
            routes=[
                aws.ec2.RouteTableRouteArgs(
                    cidr_block="0.0.0.0/0", gateway_id=self.igw.id
                )
            ],
            tags={**self.base_tags, "Name": f"{self.project_name}-public-route-table"},
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.private_route_table = aws.ec2.RouteTable(
            f"{self.project_name}-private-route-table",
            vpc_id=self.vpc.id,
            routes=[
                aws.ec2.RouteTableRouteArgs(
                    cidr_block="0.0.0.0/0", nat_gateway_id=self.nat_gw.id
                )
            ],
            tags={**self.base_tags, "Name": f"{self.project_name}-private-route-table"},
            opts=pulumi.ResourceOptions(parent=self),
        )

        for association in range(self.subnet_number):

            aws.ec2.RouteTableAssociation(
                f"{self.project_name}-public-route-table-association-{association}",
                route_table_id=self.public_route_table.id,
                subnet_id=self.public_subnets[association].id,
                opts=pulumi.ResourceOptions(parent=self),
            )

            aws.ec2.RouteTableAssociation(
                f"{self.project_name}-private-route-table-association-{association}",
                route_table_id=self.private_route_table.id,
                subnet_id=self.application_subnets[association].id,
                opts=pulumi.ResourceOptions(parent=self),
            )

        self.register_outputs(
            {
                "vpc_id": self.vpc.id,
                "public_subnets": self.public_subnets,
                "application_subnets": self.application_subnets,
                "database_subnets": self.database_subnets,
                "nat_gw": self.nat_gw.id,
                "eip": self.eip.id,
                "igw": self.igw.id,
                "public_route_table": self.public_route_table.id,
                "private_route_table": self.private_route_table.id,
                "availability_zones": availability_zones,
                "cidr_block": self.cidr_block,
                "project_name": self.project_name,
                "subnet_number": self.subnet_number,
                "base_tags": self.base_tags,
            }
        )

        # pulumi.export("application_subnets", self.application_subnets)
