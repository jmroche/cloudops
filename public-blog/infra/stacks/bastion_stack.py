"""
Stack to create a bastion instance in order to interact with the EKS Cluster. This is instance will be placed in the Private (Application) Subnet
and will have the same role as the EKS cluster to enable the access. Kubectl, Helm, Kubeconfig and security patches are installed configured
using user data.
"""
import os
from platform import machine
from turtle import clear

import aws_cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_eks as eks
from aws_cdk import aws_iam as iam
from aws_cdk import Stack
from constructs import Construct


class BastionStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        cluster: eks.Cluster,
        bastion_sg: ec2.SecurityGroup,
        vpc=ec2.Vpc,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        project_name = self.node.try_get_context("project_name")
        # Set the region to be used
        region = self.node.try_get_context("region")

        flux_env_context = self.node.try_get_context("flux")
        github_token_sm_arn = flux_env_context[
            "github_token_secret_arn"
        ]  # Get ARN for Secrets MAnager holding the github token

        # Get Role ARN from security stack exports

        bastion_role_arn = aws_cdk.Fn.import_value("eks-bastion-role")

        bastion_role = iam.Role.from_role_arn(
            self, "bastion-role", role_arn=bastion_role_arn
        )

        # Add a policy to allow the bastion host to access the secrets management secrets
        bastion_role.add_to_principal_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret",
                ],
                resources=[github_token_sm_arn],
            )
        )
        # bastion_role.add_to_policy(
        #     iam.PolicyStatement(
        #         effect=iam.Effect.ALLOW,
        #         actions=[
        #             "secretsmanager:GetSecretValue",
        #             "secretsmanager:DescribeSecret",
        #         ],
        #         resources=[github_token_sm_arn],
        #     )
        # )

        # Get the latest Amazon Linux 2 machine image

        amzn_linux = ec2.AmazonLinuxImage(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=ec2.AmazonLinuxEdition.STANDARD,
            virtualization=ec2.AmazonLinuxVirt.HVM,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE,
        )

        # Create the instance
        bastion_instance = ec2.Instance(
            self,
            "BastionInstance",
            instance_name="k8s-bastion",
            vpc=vpc,
            machine_image=amzn_linux,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE2, ec2.InstanceSize.LARGE
            ),
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=25,
                        encrypted=True,
                        delete_on_termination=True,
                        volume_type=ec2.EbsDeviceVolumeType.GP2,
                    ),
                )
            ],
            vpc_subnets=ec2.SubnetType.PRIVATE_WITH_NAT,
            security_group=bastion_sg,
            role=bastion_role,
        )

        # Read the get_secrets.py file into a variable in order to copy it over to the bastion host to be executed

        basedir = os.getcwd()
        get_secrets_file = os.path.abspath(
            os.path.join(basedir, "stacks", "get_secrets.py")
        )
        get_bash_script = os.path.abspath(
            os.path.join(basedir, "stacks", "set_env_vars.sh")
        )

        with open(get_secrets_file, "r") as f:
            secrets_file = f.read()

        with open(get_bash_script, "r") as f:
            bash_script_file = f.read()

        # set the export var to set global flux and help path

        export = "export PATH='/usr/local/bin:$PATH' >> /home/ec2-user/.bashrc"
        # Commands to create bash script to run on the bastion and bootstrap the EKS cluster
        commands = [
            "#!/bin/bash",
            "systemctl enable amazon-ssm-agent",
            "systemctl start amazon-ssm-agent",
            "curl -o kubectl https://amazon-eks.s3.us-west-2.amazonaws.com/1.21.2/2021-07-05/bin/linux/amd64/kubectl",
            "chmod +x ./kubectl",
            "mv ./kubectl /usr/bin",
            "curl -s https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash -",
            "curl -s https://fluxcd.io/install.sh | bash -",
            f"aws eks update-kubeconfig --name {cluster.cluster_name} --region {region} --kubeconfig '/home/ec2-user/.kube/config'",
            "chown ec2-user:ec2-user /home/ec2-user/.kube/config",
            "yum update -y",
            f"cat << EOF > /home/ec2-user/get_secrets.py {secrets_file}\nEOF\n",
            "pip3 install boto3",
            f"cat << 'EOF' > /home/ec2-user/set_env_vars.sh\n{bash_script_file}\nEOF\n",
            "chmod +x /home/ec2-user/set_env_vars.sh",
            "chown ec2-user:ec2-user /home/ec2-user/set_env_vars.sh",
            "chown ec2-user:ec2-user /home/ec2-user/get_secrets.py",
            "runuser -l ec2-user -c 'cp /home/ec2-user/.bashrc /home/ec2-user/.bashrc_bkp'",
            "runuser -l ec2-user -c 'eval `sh /home/ec2-user/set_env_vars.sh`'",
            f"echo {export}",
        ]

        with open("user_data.sh", "w") as f:
            for command in commands:
                f.write(f"{command}\n")

        with open("user_data.sh", "r") as f:
            user_data_file = f.read()

        bastion_instance.add_user_data(user_data_file)