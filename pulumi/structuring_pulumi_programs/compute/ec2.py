import pulumi
import pulumi_aws as aws


# Create an EC2 Component Resource


class EC2Component(pulumi.ComponentResource):
    def __init__(
        self,
        name,
        project_name,
        base_tags,
        subnet,
        security_group,
        instance_type="t3.micro",
        ami=None,
        opts=None,
    ):
        super().__init__("devopsinthecloud:utils:ec2Instance", name, None, opts)

        self.name = name
        self.project_name = project_name
        self.base_tags = base_tags
        self.subnet = subnet
        self.security_group = security_group
        self.instance_type = instance_type
        self.ami = ami

        if not self.ami:
            self.ami = aws.ec2.get_ami(
                most_recent=True,
                owners=["amazon"],
                filters=[
                    aws.ec2.GetAmiFilterArgs(
                        name="name",
                        values=["amzn2-ami-hvm-*-x86_64-gp2"],
                    ),
                ],
            )

        # Create an EC2 instance resource, and save the instance ID for later use.
        self.instance = aws.ec2.Instance(
            f"{self.project_name}-ec2-instance",
            instance_type=self.instance_type,
            ami=self.ami.id,
            subnet_id=self.subnet.id,
            tags={**self.base_tags, "Name": f"{self.project_name}-ec2-instance"},
            vpc_security_group_ids=[self.security_group.id],
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.id = self.instance.id

        pulumi.export(f"{self.project_name}-ec2-instance-id", self.id)

        self.register_outputs(
            {
                "instance_id": self.id,
            }
        )
