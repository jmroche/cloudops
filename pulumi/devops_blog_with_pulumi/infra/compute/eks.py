"""
Component that creates the Elastic Kubernetes Service (EKS) to
run our applications.
"""
import pulumi
import pulumi_aws as aws
import pulumi_eks as eks
import pulumi_kubernetes as k8s
import pulumi_command as command
import datetime
import json


class EKSComponent(pulumi.ComponentResource):
    def __init__(self, name, project_name, base_tags, pods_sg_id: str, application_subnets: list, vpc_id: str, eks_cluster_props: dict, opts=None):
        super().__init__("devopsinthecloud:utils:eks", name, None, opts)

        self.project_name = project_name
        self.base_tags = base_tags
        self.application_subnets = application_subnets
        self.pods_sg_id = pods_sg_id
        self.vpc_id = vpc_id
        self.eks_cluster_props = eks_cluster_props

        # Security Group for the EKS Cluster and Managed Node Groups

        self.eks_cluster_sg = aws.ec2.SecurityGroup(
            "EKS-Cluster-SG",
            description="EKS Cluster Security Group",
            vpc_id=self.vpc_id,
            ingress=[
                aws.ec2.SecurityGroupIngressArgs(
                    from_port=0,
                    to_port=0,
                    protocol="-1",
                    self=True,
                    description="Allow any traffic from within the same security group",
                )
            ],
            egress=[
                aws.ec2.SecurityGroupEgressArgs(
                    from_port=0,
                    to_port=0,
                    protocol="-1",
                    cidr_blocks=["0.0.0.0/0"],
                    description="Allow all outbound traffic",
                )
            ],
            tags={**self.base_tags,
                    "Name": f"eks-cluster-sg-{eks_cluster_props["name"]}-{datetime.datetime.now().strftime("%Y%m%d")}",
                    f"kubernetes.io/cluster/{eks_cluster_props["name"]}": "owned",
                    "aws:eks:cluster-name": f"{eks_cluster_props["name"]}"

                    },
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Allow PODS Security Group access the cluster on DNS ports

        
        aws.ec2.SecurityGroupRule(
            f"{project_name}-eks-cluster-pod-dns-tcp-access-sg-rule",
            type="ingress",
            from_port=53,
            to_port=53,
            protocol=aws.ec2.ProtocolType.TCP,
            source_security_group_id=self.pods_sg_id,
            security_group_id=self.eks_cluster_sg.id,
            description="Allow POD_SG Access tp TCP 53",
            opts=pulumi.ResourceOptions(parent=self)        
            )
        
        aws.ec2.SecurityGroupRule(
            f"{project_name}-eks-cluster-pod-dns-udp-access-sg-rule",
            type="ingress",
            from_port=53,
            to_port=53,
            protocol=aws.ec2.ProtocolType.UDP,
            source_security_group_id=self.pods_sg_id,
            security_group_id=self.eks_cluster_sg.id,
            description="Allow POD_SG Access tp UDP 53",
            opts=pulumi.ResourceOptions(parent=self) 
        )


        # Create the AWS EKS cluster using the Pulumi AWS Provider

        self.eks_cluster = aws.eks.Cluster(
            f"{project_name}-eks-cluster",
            name=eks_cluster_props["name"],
            role_arn=eks_cluster_props["cluster_role"].arn,
            version=eks_cluster_props["version"],
            vpc_config=aws.eks.ClusterVpcConfigArgs(
                subnet_ids=[subnet.id for subnet in self.application_subnets],
                endpoint_private_access=True,
                endpoint_public_access=False,
                security_group_ids=[self.eks_cluster_sg.id],
                # vpc_id=self.vpc_id,
            ),
            tags={**self.base_tags, "Name": f"{project_name}-eks-cluster"},
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.eks_node_group = aws.eks.NodeGroup(
            f"{project_name}-eks-node-group",
            cluster_name=self.eks_cluster.name,
            node_group_name=f"{project_name}-eks-node-group",
            node_role_arn=eks_cluster_props["worker_role"].arn,
            subnet_ids=[subnet.id for subnet in self.application_subnets],
            scaling_config=aws.eks.NodeGroupScalingConfigArgs(
                desired_size=self.eks_cluster_props["eks_cluster_min_node_number"],
                min_size=self.eks_cluster_props["eks_cluster_min_node_number"],
                max_size=self.eks_cluster_props["eks_cluster_max_node_number"],
            ),
            instance_types=[self.eks_cluster_props["instance_type"]],
            version=self.eks_cluster_props["version"],
            tags={**self.base_tags, "Name": f"{project_name}-eks-node-group"},
            opts=pulumi.ResourceOptions(parent=self, depends_on=[self.eks_cluster]),
        )

        # Get the kubeconfig for the cluster using pulumi_command

        # kubeconfig = command.local.Command(
        #     f"{project_name}-eks-cluster-kubeconfig",
        #     create=f"aws eks update-kubeconfig --name {self.eks_cluster.name} --region us-east-1 --dry-run",
        #     triggers=["trigger-me-on-change"],
        #     opts=pulumi.ResourceOptions(parent=self, depends_on=[self.eks_cluster]),
        # )

        # kubeconfig = self.eks_cluster.name.apply(lambda name: command.local.Command(
        #     "updateKubeconfig",
        #     create=f"aws eks update-kubeconfig --name {name} --region us-east-1 --dry-run",
        #     # Replace `triggers` with actual triggers or remove if not applicable.
        #     triggers=["trigger-on-change"],
        # ))

        # pulumi.export("kubeconfig", kubeconfig.stdout)

        # # First, we'll create a Pulumi Kubernetes provider that connects to an EKS cluster.
        # # It assumes that kubeconfig is configured correctly in your environment.
        # kube_provider = k8s.Provider(
        #     'k8s-provider',
        #     kubeconfig=kubeconfig.stdout,)

        # # Next, we'll retrieve the existing 'aws-auth' ConfigMap.
        # aws_auth_configmap = k8s.core.v1.ConfigMap.get(
        #     'aws-auth',
        #     'kube-system/aws-auth',
        #     opts=pulumi.ResourceOptions(provider=kube_provider, depends_on=[self.eks_cluster]),
        # )

        # # Let's define the user details we want to add to the 'aws-auth' ConfigMap.
        # # Replace 'your-iam-user-arn' with the ARN of the IAM user you wish to add.
        # # The username and groups are applied in the Kubernetes RBAC system.
        # iam_user_arn = "arn:aws:sts::601749221392:assumed-role/Admin/jmroche-Isengard"
        # username = "jose"
        # groups = ['system:masters']

        # # We'll construct the new entry for the user.
        # # This includes the user ARN, a Kubernetes username, and a list of groups.
        # new_user_mapping = f"""
        # - userarn: {iam_user_arn}
        # username: {username}
        # groups:
        # - {groups[0]}
        # """

        # # We'll use the `apply` method to safely read and update the ConfigMap data.
        # # This involves appending the new IAM user's mapping to the `mapUsers` field.
        # updated_aws_auth_configmap = aws_auth_configmap.data.apply(lambda data: {
        #     'mapRoles': data['mapRoles'],
        #     'mapUsers': (data['mapUsers'] or '') + new_user_mapping,
        # })

        # # Finally, we'll create a new ConfigMap with the updated user mappings and apply it to the cluster.
        # # Pulumi will understand this as an update to an existing resource rather than creating a new one.
        # k8s.core.v1.ConfigMap(
        #     'aws-auth-updated',
        #     metadata={'name': 'aws-auth', 'namespace': 'kube-system'},
        #     data=updated_aws_auth_configmap,
        #     opts=pulumi.ResourceOptions(provider=kube_provider, depends_on=[aws_auth_configmap]),
        # )

        # # Output the updated 'aws-auth' ConfigMap.
        # pulumi.export('updated_aws_auth_configmap', updated_aws_auth_configmap)



        

   
        