import pulumi
import pulumi_aws as aws


class SecurityComponent(pulumi.ComponentResource):
    def __init__(self, name, vpc_id, project_name, base_tags, opts=None):
        super().__init__("devopsinthecloud:utils:security", name, None, opts)

        self.vpc_id = vpc_id
        self.base_tags = base_tags
        self.project_name = project_name

        # Create Security groups for the public, application and datbases subnet

        self.pod_sg = aws.ec2.SecurityGroup(
            "POD-SG",
            description="Security Group for PODS",
            vpc_id=self.vpc_id,
            ingress=[
                aws.ec2.SecurityGroupIngressArgs(
                    from_port=5000,
                    to_port=5000,
                    protocol="tcp",
                    cidr_blocks=["0.0.0.0/0"],
                    description="Allow TCP port 5000 from anywhere to access the flask-blog app.",
                ),
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
            tags={**self.base_tags, "Name": "POD-SG"},
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.rds_sg = aws.ec2.SecurityGroup(
            "RDS-SG",
            description="RDS Security Group",
            vpc_id=self.vpc_id,
            ingress=[
                aws.ec2.SecurityGroupIngressArgs(
                    from_port=3306,
                    to_port=3306,
                    protocol="tcp",
                    security_groups=[self.pod_sg.id],
                    description="Allow POD_SG to access RDS_SG on port 3306",
                )
            ],
            tags={**self.base_tags, "Name": "RDS-SG"},
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.bastion_sg = aws.ec2.SecurityGroup(
            "Bastion-SG",
            description="Allow outbound communiation for the bastion host",
            vpc_id=self.vpc_id,
            egress=[
                aws.ec2.SecurityGroupEgressArgs(
                    from_port=0,
                    to_port=0,
                    protocol="-1",
                    cidr_blocks=["0.0.0.0/0"],
                    description="Allow all outbound traffic",
                )
            ],
            tags={**self.base_tags, "Name": "Bastion-SG"},
            opts=pulumi.ResourceOptions(parent=self),
        )

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
            tags={
                **self.base_tags,
                "Name": "EKS-Cluster-SG",
                "kubernetes.io/cluster/eks-cluster": "owned",
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
            source_security_group_id=self.pod_sg.id,
            security_group_id=self.eks_cluster_sg.id,
            description="Allow POD_SG Access tp TCP 53",
            opts=pulumi.ResourceOptions(parent=self),
        )

        aws.ec2.SecurityGroupRule(
            f"{project_name}-eks-cluster-pod-dns-udp-access-sg-rule",
            type="ingress",
            from_port=53,
            to_port=53,
            protocol=aws.ec2.ProtocolType.UDP,
            source_security_group_id=self.pod_sg.id,
            security_group_id=self.eks_cluster_sg.id,
            description="Allow POD_SG Access tp UDP 53",
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Create IAM Roles for the required services

        assume_role = aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    effect="Allow",
                    principals=[
                        aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                            type="Service",
                            identifiers=["eks.amazonaws.com"],
                        )
                    ],
                    actions=["sts:AssumeRole"],
                )
            ]
        )

        self.eks_cluster_admin_role = aws.iam.Role(
            "ClusterAdminRole",
            name="eks-cluster-admin-role",
            assume_role_policy=assume_role.json,
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.eks_cluster_admin_role_policy = aws.iam.RolePolicyAttachment(
            "AmazonEKSClusterPolicy",
            policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
            role=self.eks_cluster_admin_role.name,
            opts=pulumi.ResourceOptions(parent=self),
        )

        eks_cluster_ssm_policy = aws.iam.RolePolicyAttachment(
            "AmazonSSMManagedInstanceCore",
            policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
            role=self.eks_cluster_admin_role.name,
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Enable Security Groups for Pods
        # Reference: https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html
        amazon_eksvpc_resource_controller = aws.iam.RolePolicyAttachment(
            "example-AmazonEKSVPCResourceController",
            policy_arn="arn:aws:iam::aws:policy/AmazonEKSVPCResourceController",
            role=self.eks_cluster_admin_role.name,
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Create A Role for the EKS Worked Node Groups

        worker_assume_role = aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    effect="Allow",
                    principals=[
                        aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                            type="Service",
                            identifiers=["ec2.amazonaws.com"],
                        )
                    ],
                    actions=["sts:AssumeRole"],
                )
            ]
        )

        self.eks_worker_admin_role = aws.iam.Role(
            "WorkerAdminRole",
            name="eks-worker-admin-role",
            assume_role_policy=worker_assume_role.json,
            opts=pulumi.ResourceOptions(parent=self),
        )

        worker_node_policy = aws.iam.RolePolicyAttachment(
            "AmazonEKSWorkerNodePolicy",
            policy_arn="arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
            role=self.eks_worker_admin_role.name,
            opts=pulumi.ResourceOptions(parent=self),
        )

        worker_node_ecr_policy = aws.iam.RolePolicyAttachment(
            "AmazonEKSWorkerNodeECRPolicy",
            policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
            role=self.eks_worker_admin_role.name,
            opts=pulumi.ResourceOptions(parent=self),
        )

        worker_node_vpc_cni_policy = aws.iam.RolePolicyAttachment(
            "AmazonEKSWorkerNodeVPCPolicy",
            policy_arn="arn:aws:iam::aws:policy/AmazonEKSVPCResourceController",
            role=self.eks_worker_admin_role.name,
            opts=pulumi.ResourceOptions(parent=self),
        )

        worker_node_ssm_policy = aws.iam.RolePolicyAttachment(
            "AmazonEKSWorkerNodeSSMPolicy",
            policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
            role=self.eks_worker_admin_role.name,
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.register_outputs(
            {
                "pod_sg": self.pod_sg.id,
                "rds_sg": self.rds_sg.id,
                "bastion_sg": self.bastion_sg.id,
                "eks_admin_role": self.eks_cluster_admin_role.arn,
                "worker_node_admin_role": self.eks_worker_admin_role.arn,
            }
        )
