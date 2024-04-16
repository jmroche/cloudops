"""
Stack to create and configure the EKS Cluster, its environments and addons. Example, here we define the installation for: Metric Server,
Load Balancer, Security Groups for Pods, Cluster Autoscaler, Flux, etc.
"""
import json
import os
from urllib import request

import aws_cdk
import requests
import yaml
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_eks as eks
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_secretsmanager as sm
from aws_cdk import RemovalPolicy
from aws_cdk import Stack
from aws_cdk.lambda_layer_kubectl_v27 import KubectlV27Layer
from constructs import Construct
from constructs import Node

from .addons.flux2_stack import FluxStack

# from rds_stack import RDSStack
# from vpc_stack import VPCStack


class EKSStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        pod_sg: ec2.SecurityGroup,
        rds_sg: ec2.SecurityGroup,
        bastion_sg: ec2.SecurityGroup,
        ecr_repo: ecr.Repository,
        kmskey: kms.Key,
        test_creds_secret_arn: str = None,
        prod_creds_secret_arn: str = None,
        test_db_hostname_arn: str = None,
        prod_db_hostname_arn: str = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Set the region to be used
        region = self.node.try_get_context("region")

        # Set the tags to be used for te cluster and nodes
        spring_cleaning_tags = {"auto-delete": "never"}

        # Import the cluster roles arn from security stack export

        cluster_admin_role_arn = aws_cdk.Fn.import_value("eks-bastion-role")

        # Read the EKS Control Plane versions from the context
        # This is the version of the control plane that will be installed on the cluster
        cluster_new_version = self.node.try_get_context("cluster_new_versions")
        if cluster_new_version["upgrade_cluster"]:
            EKS_CONTROL_PLANE_VERSION = cluster_new_version["eks_control_version"]
            EKS_WORKER_AMI_VERSION = cluster_new_version["eks_worker_ami_version"]
            AWSLBCONTROLLER_VERSION = cluster_new_version["awslbcontroller_version"]
            CLUSTER_AUTOSCALER_VERSION = cluster_new_version[
                "cluster_autoscaler_version"
            ]
            METRICS_SERVER_VERSION = cluster_new_version["metrics_server_version"]
            AWS_VPC_CNI_VERSION = cluster_new_version["aws_vpc_cni_version"]
        else:
            EKS_CONTROL_PLANE_VERSION = self.node.try_get_context("eks_control_version")
            EKS_WORKER_AMI_VERSION = self.node.try_get_context("eks_worker_ami_version")
            AWSLBCONTROLLER_VERSION = self.node.try_get_context(
                "awslbcontroller_version"
            )
            CLUSTER_AUTOSCALER_VERSION = self.node.try_get_context(
                "cluster_autoscaler_version"
            )
            METRICS_SERVER_VERSION = self.node.try_get_context("metrics_server_version")
            AWS_VPC_CNI_VERSION = self.node.try_get_context("aws_vpc_cni_version")

        # Create an EKS Cluster

        self.eks_cluster = eks.Cluster(
            self,
            "cluster",
            vpc=vpc,
            masters_role=iam.Role.from_role_arn(
                self, "cluster_admin_role", role_arn=cluster_admin_role_arn
            ),
            # Make our cluster's control plane accessible only within our private VPC
            # This means that we'll have to ssh to a jumpbox/bastion or set up a VPN to manage it
            endpoint_access=eks.EndpointAccess.PRIVATE,
            version=eks.KubernetesVersion.of(EKS_CONTROL_PLANE_VERSION),
            default_capacity=0,
            tags=spring_cleaning_tags,
            kubectl_layer=KubectlV27Layer(self, "KubectlV27Layer"),
        )

        # Map my user arn to the K8s system:master group in order to manage it via the AWS Console
        self.eks_cluster.aws_auth.add_user_mapping(
            user=iam.User.from_user_arn(
                self, "user", self.node.try_get_context("user_arn")
            ),
            groups=["system:masters"],
            username=self.node.try_get_context("user_name"),
        )

        worker_role = aws_cdk.Fn.import_value("eks-worker-node-role")

        # Create Managed Worker Nodes
        # Node Release version seperated from control K8s version in order to update separately
        # AMI versions for worker nodes: https://docs.aws.amazon.com/eks/latest/userguide/eks-linux-ami-versions.html
        # https://github.com/awslabs/amazon-eks-ami/releases
        node_capacity_type = eks.CapacityType.ON_DEMAND
        self.eks_node_group = self.eks_cluster.add_nodegroup_capacity(
            "cluster-default-ng",
            capacity_type=node_capacity_type,
            desired_size=self.node.try_get_context("eks_node_quantity"),
            max_size=self.node.try_get_context("eks_node_max_quantity"),
            disk_size=self.node.try_get_context("eks_node_disk_size"),
            # The default in CDK is to force upgrades through even if they violate - it is safer to not do that
            force_update=False,
            instance_types=[
                ec2.InstanceType(self.node.try_get_context("eks_node_instance_type"))
            ],
            release_version=EKS_WORKER_AMI_VERSION,
            node_role=iam.Role.from_role_arn(
                self, "worker-node-role", role_arn=worker_role
            ),
            tags=spring_cleaning_tags
            # release_version=self.node.try_get_context(
            #     "eks_node_ami_version")
        )

        self.eks_node_group.stack.tags.set_tag(
            "auto-delete", "never"
        )  # apply tags to nodegroup

        # Allow POD_SG to access internal K8s DNS
        self.eks_cluster.cluster_security_group.add_ingress_rule(
            peer=pod_sg,
            connection=ec2.Port.tcp(53),
            description="Allow POD_SG Access tp TCP 53",
        )
        self.eks_cluster.cluster_security_group.add_ingress_rule(
            peer=pod_sg,
            connection=ec2.Port.udp(53),
            description="Allow POD_SG Access tp UDP 53",
        )

        self.eks_cluster.cluster_security_group.add_ingress_rule(
            peer=bastion_sg,
            connection=ec2.Port.tcp(443),
            description="Allow Bastion to reach the cluster on port 443",
        )

        # Create a secret to be used as secret key for Flask and store in secrets manager

        json_template = {"flask-secret": "key"}

        self.flask_secret_key = sm.Secret(
            self,
            "flask-secret-key",
            description="Flask Secret Key",
            secret_name="flask-secret-key",
            encryption_key=kmskey,
            generate_secret_string=(
                sm.SecretStringGenerator(
                    include_space=False,
                    exclude_lowercase=False,
                    exclude_numbers=False,
                    exclude_uppercase=False,
                    exclude_punctuation=False,
                    password_length=80,
                    require_each_included_type=True,
                    generate_string_key="key",
                    secret_string_template=json.dumps(json_template),
                )
            ),
        )

        # Create the test and production namesapces needed to deploy our app later

        """Kubernetes Namespace Manifest Example:
        apiVersion: v1
        kind: Namespace
        metadata:
            name:
        """

        # Create test namespace

        test_namespace_manifest = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {"name": "test"},
        }

        test_namespace = self.eks_cluster.add_manifest(
            "test-namespace", test_namespace_manifest
        )

        # Create production namespace

        prod_namespace_manifest = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {"name": "production"},
        }

        prod_namespace = self.eks_cluster.add_manifest(
            "prod-namespace", prod_namespace_manifest
        )

        # Create the AWS Load Balancer Controller resources

        awslbcontroller_service_account = self.eks_cluster.add_service_account(
            "aws-load-balancer-controller",
            name="aws-load-balancer-controller",
            namespace="kube-system",
        )

        # Create the PolicyStatements to attach to the role
        # Got the required policy from https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json

        alb_policy_json_path = os.path.abspath(
            os.path.join(os.getcwd(), "stacks", "addons", "aws_alb_iam_policy.json")
        )

        with open(alb_policy_json_path, "r") as rf:
            # lines = rf.read()

            awslbcontroller_policy_document_json = json.loads(rf.read())

        # Attach the necessary permissions
        awslbcontroller_policy = iam.Policy(
            self,
            "awslbcontrollerpolicy",
            document=iam.PolicyDocument.from_json(awslbcontroller_policy_document_json),
        )
        awslbcontroller_service_account.role.attach_inline_policy(
            awslbcontroller_policy
        )

        # Deploy the AWS Load Balancer Controller from the AWS Helm Chart
        # For more info check out https://github.com/aws/eks-charts/tree/master/stable/aws-load-balancer-controller
        awslbcontroller_chart = self.eks_cluster.add_helm_chart(
            "aws-load-balancer-controller",
            chart="aws-load-balancer-controller",
            version=AWSLBCONTROLLER_VERSION,
            release="awslbcontroller",
            repository="https://aws.github.io/eks-charts",
            namespace="kube-system",
            values={
                "clusterName": self.eks_cluster.cluster_name,
                "region": region,
                "vpcId": vpc.vpc_id,
                "serviceAccount": {
                    "create": False,
                    "name": "aws-load-balancer-controller",
                },
                "replicaCount": 2,
                "podDisruptionBudget": {"maxUnavailable": 1},
                "resources": {"requests": {"cpu": "0.25", "memory": "0.5Gi"}},
            },
        )
        awslbcontroller_chart.node.add_dependency(awslbcontroller_service_account)

        # Cluster Autoscaler
        clusterautoscaler_service_account = self.eks_cluster.add_service_account(
            "clusterautoscaler", name="clusterautoscaler", namespace="kube-system"
        )

        # Create the PolicyStatements to attach to the role
        clusterautoscaler_policy_statement_json_1 = {
            "Effect": "Allow",
            "Action": [
                "autoscaling:DescribeAutoScalingGroups",
                "autoscaling:DescribeAutoScalingInstances",
                "autoscaling:DescribeLaunchConfigurations",
                "autoscaling:DescribeScalingActivities",
                "autoscaling:DescribeTags",
                "autoscaling:SetDesiredCapacity",
                "autoscaling:TerminateInstanceInAutoScalingGroup",
                "eks:DescribeNodegroup",
                "ec2:DescribeInstanceTypes",
                "ec2:DescribeLaunchTemplateVersions",
            ],
            "Resource": "*",
        }

        # Attach the necessary permissions
        clusterautoscaler_service_account.add_to_principal_policy(
            iam.PolicyStatement.from_json(clusterautoscaler_policy_statement_json_1)
        )

        # Install the Cluster Autoscaler
        # For more info see https://github.com/kubernetes/autoscaler
        clusterautoscaler_chart = self.eks_cluster.add_helm_chart(
            "cluster-autoscaler",
            chart="cluster-autoscaler",
            version=CLUSTER_AUTOSCALER_VERSION,
            release="clusterautoscaler",
            repository="https://kubernetes.github.io/autoscaler",
            namespace="kube-system",
            values={
                "autoDiscovery": {"clusterName": self.eks_cluster.cluster_name},
                "awsRegion": region,
                "rbac": {
                    "serviceAccount": {"create": False, "name": "clusterautoscaler"}
                },
                "replicaCount": 2,
                "extraArgs": {
                    "skip-nodes-with-system-pods": False,
                    "balance-similar-node-groups": True,
                },
            },
        )
        clusterautoscaler_chart.node.add_dependency(clusterautoscaler_service_account)

        # Metrics Server (required for the Horizontal Pod Autoscaler (HPA))
        # For more info see https://github.com/kubernetes-sigs/metrics-server/tree/master/charts/metrics-server
        metricsserver_chart = self.eks_cluster.add_helm_chart(
            "metrics-server",
            chart="metrics-server",
            version=METRICS_SERVER_VERSION,
            release="metricsserver",
            repository="https://kubernetes-sigs.github.io/metrics-server/",
            namespace="kube-system",
            values={"resources": {"requests": {"cpu": "0.25", "memory": "0.5Gi"}}},
        )

        #  Install the AWS VPC CNI for Pod SG to work

        # Upgrading that to the latest version 1.10.0 via the Helm Chart
        # Patching CNI Pluging following recommendation here: https://github.com/aws/aws-cdk/issues/10788
        # If this process somehow breaks the CNI you can repair it manually by following the steps here:
        # https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html#updating-vpc-cni-add-on
        # TODO: Move this to the CNI Managed Add-on when that supports flipping the required ENABLE_POD_ENI setting

        # Adopting the existing aws-node managed resources to Helm
        patch_types = ["DaemonSet", "ClusterRole", "ClusterRoleBinding"]
        patches = []
        for kind in patch_types:
            patch = eks.KubernetesPatch(
                self,
                "CNI-Patch-" + kind,
                cluster=self.eks_cluster,
                resource_name=kind + "/aws-node",
                resource_namespace="kube-system",
                apply_patch={
                    "metadata": {
                        "annotations": {
                            "meta.helm.sh/release-name": "aws-vpc-cni",
                            "meta.helm.sh/release-namespace": "kube-system",
                        },
                        "labels": {"app.kubernetes.io/managed-by": "Helm"},
                    }
                },
                restore_patch={},
                patch_type=eks.PatchType.STRATEGIC,
            )
            # We don't want to clean this up on Delete - it is a one-time patch to let the Helm Chart own the resources
            patch_resource = patch.node.find_child("Resource")
            patch_resource.apply_removal_policy(RemovalPolicy.RETAIN)
            # Keep track of all the patches to set dependencies down below
            patches.append(patch)

        # Create the Service Account
        sg_pods_service_account = self.eks_cluster.add_service_account(
            "aws-node", name="aws-node-helm", namespace="kube-system"
        )

        # Give it the required policies
        sg_pods_service_account.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKS_CNI_Policy")
        )
        # sg_pods_service_account.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKSVPCResourceController"))
        self.eks_cluster.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonEKSVPCResourceController"
            )
        )

        # Deploy the Helm chart
        # For more info check out https://github.com/aws/eks-charts/tree/master/stable/aws-vpc-cni
        # Note that for some regions different account # required - https://docs.aws.amazon.com/eks/latest/userguide/add-ons-images.html
        sg_pods_chart = self.eks_cluster.add_helm_chart(
            "aws-vpc-cni",
            chart="aws-vpc-cni",
            version=AWS_VPC_CNI_VERSION,
            release="aws-vpc-cni",
            repository="https://aws.github.io/eks-charts",
            namespace="kube-system",
            values={
                "init": {
                    "image": {
                        "region": region,
                        "account": "602401143452",
                    },
                    "env": {"DISABLE_TCP_EARLY_DEMUX": True},
                },
                "image": {"region": region, "account": "602401143452"},
                "env": {"ENABLE_POD_ENI": True},
                "serviceAccount": {"create": False, "name": "aws-node-helm"},
                "crd": {"create": False},
                "originalMatchLabels": True,
            },
        )
        # This depends both on the service account and the patches to the existing CNI resources having been done first
        sg_pods_chart.node.add_dependency(sg_pods_service_account)
        for patch in patches:
            sg_pods_chart.node.add_dependency(patch)

        """
        Add a SecurityGroupPolicy to each of the Namespaces to allow pods to access RDS based on their labels

        Example:
        apiVersion: vpcresources.k8s.aws/v1beta1
        kind: SecurityGroupPolicy
        metadata:
            name: allow-rds-access
            namespace: test
        spec:
            podSelector:
                matchLabels:
                app.kubernetes.io/name": "flaskblog
            securityGroups:
                groupIds:
                - sg-0de220e399fbdbcd1

        """
        # Get the SG_POD Id from security stack exports

        pod_sg_id = aws_cdk.Fn.import_value("podsg-id")

        # Add SecurityGroupPolicy to allow Pod access to RDS to both namesapces

        if test_creds_secret_arn is not None:
            test_sg_policy_manifest = {
                "apiVersion": "vpcresources.k8s.aws/v1beta1",
                "kind": "SecurityGroupPolicy",
                "metadata": {"name": "allow-rds-access", "namespace": "test"},
                "spec": {
                    "podSelector": {
                        "matchLabels": {"app.kubernetes.io/name": "flaskblog"},
                    },
                    "securityGroups": {"groupIds": [pod_sg_id]},
                },
            }
            test_sg_policy = self.eks_cluster.add_manifest(
                "test-securitygrouppolicy", test_sg_policy_manifest
            )
            test_sg_policy.node.add_dependency(test_namespace)

        if prod_creds_secret_arn is not None:
            prod_sg_policy_manifest = {
                "apiVersion": "vpcresources.k8s.aws/v1beta1",
                "kind": "SecurityGroupPolicy",
                "metadata": {"name": "allow-rds-access", "namespace": "production"},
                "spec": {
                    "podSelector": {
                        "matchLabels": {"app.kubernetes.io/name": "flaskblog"},
                    },
                    "securityGroups": {"groupIds": [pod_sg_id]},
                },
            }
            prod_sg_policy = self.eks_cluster.add_manifest(
                "production-securitygrouppolicy", prod_sg_policy_manifest
            )
            prod_sg_policy.node.add_dependency(prod_namespace)

        # Allow Cluster to pull images from ECR Repository
        ecr_repo.grant_pull(self.eks_cluster.role)

        # # Install Flux
        flux_stack = FluxStack(self, "FluxStack", cluster=self.eks_cluster)
        flux_stack.node.add_dependency(self.eks_cluster)

        # Get the manifest prepared in the flux stack
        flux_manifest_import = flux_stack.flux_manifest_yaml

        # After flux version 0.24.1 the Flux install manifest are too big for lambda
        # Therefore we need to breakdown the manifest in parts

        # We create a lsit of manifests in order to add dependencies later
        # We need ot guarantee the very first manifest (at index 0) gets installed first
        flux_manifests_list = []

        for index, manifest in enumerate(flux_manifest_import):

            manifest_id = f"flux-manifest-id-{index}"

            flux_manifest = self.eks_cluster.add_manifest(manifest_id, manifest)

            flux_manifests_list.append(flux_manifest)

            if index > 0:
                flux_manifest.node.add_dependency(flux_manifests_list[0])

        # Create the manifest to install Flux
        # flux_manifest = eks.KubernetesManifest(
        #     self,
        #     "FluxManifest",
        #     cluster=self.eks_cluster,
        #     manifest=flux_stack.flux_manifest_yaml,
        #     skip_validation=True,
        # )

        # Install AWS Secrets Manager

        # 1. Install the Secrets Manager CSI Driver
        # https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating_csi_driver.html
        # https://github.com/kubernetes-sigs/secrets-store-csi-driver (install instructions)
        # Workshop guide: https://www.eksworkshop.com/beginner/194_secrets_manager/configure-csi-driver/
        # Chart version 1.1.0

        csi_secrets_manager_driver = self.eks_cluster.add_helm_chart(
            "csi-secrets-manager-driver",
            chart="secrets-store-csi-driver",
            namespace="kube-system",
            release="csi-secrets-manager-driver",
            repository="https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts",
            # Set the values for syncSecret to True in order to enable secrets as Env variablels for the pods
            # syncSecret.enabled=true
            values={"syncSecret": {"enabled": True}},
        )

        # 2. Install AWS Secrets Aand Configuration Provider (ASCP)
        # https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating_csi_driver.html
        # https://github.com/aws/secrets-store-csi-driver-provider-aws

        # Check if we have secrets creds ARNs passed to the stacks for the test and production DBs

        if test_creds_secret_arn is not None:

            # Test Environment IRSA Service Account
            test_sa_secrets_manager_csi = self.eks_cluster.add_service_account(
                "test-secrets-manager-csi-sa",
                name="secrets-manager-csi-aws-provider-sa",
                namespace="test",
            )

            test_sa_secrets_manager_csi.add_to_principal_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret",
                    ],
                    resources=[test_creds_secret_arn, self.flask_secret_key.secret_arn],
                )
            )

            test_sa_secrets_manager_csi.add_to_principal_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["ssm:GetParameters"],
                    resources=[test_db_hostname_arn],
                )
            )

            # Wait for the test namespace to be created
            test_sa_secrets_manager_csi.node.add_dependency(test_namespace)

            # Allow the test SA to use the KMS key used to encryot the RDS secret to decrypt it
            kmskey.grant_decrypt(test_sa_secrets_manager_csi)

        # Prod Environment IRSA Service Account
        if prod_creds_secret_arn is not None:

            prod_sa_secrets_manager_csi = self.eks_cluster.add_service_account(
                "prod-secrets-manager-csi-sa",
                name="secrets-manager-csi-aws-provider-sa",
                namespace="production",
            )

            prod_sa_secrets_manager_csi.add_to_principal_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret",
                    ],
                    resources=[prod_creds_secret_arn, self.flask_secret_key.secret_arn],
                )
            )
            prod_sa_secrets_manager_csi.add_to_principal_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["ssm:GetParameters"],
                    resources=[prod_db_hostname_arn],
                )
            )

            # Wait for the production namespace to be created
            prod_sa_secrets_manager_csi.node.add_dependency(prod_namespace)

            # Allow the prod SA to use the KMS key used to encryot the RDS secret to decrypt it
            kmskey.grant_decrypt(prod_sa_secrets_manager_csi)

        # Install ASCP YAML file
        # kubectl apply -f https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml
        # https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating_csi_driver.html

        ascp_yaml_url = "https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml"
        ascp_yaml_text = requests.get(ascp_yaml_url).text
        ascp_yaml = list(yaml.load_all(ascp_yaml_text, Loader=yaml.Loader))

        # Create the manifest to install ASCP
        ascp_manifest = eks.KubernetesManifest(
            self,
            "ASCPManifest",
            cluster=self.eks_cluster,
            manifest=ascp_yaml,
            skip_validation=True,
        )
        ascp_manifest.node.add_dependency(csi_secrets_manager_driver)

        # SecretProviderClass for test RDS DB
        # https://aws.amazon.com/blogs/security/how-to-use-aws-secrets-configuration-provider-with-kubernetes-secrets-store-csi-driver/

        """
        Example description:

        apiVersion: secrets-store.csi.x-k8s.io/v1alpha1
        kind: SecretProviderClass
        metadata:
            name: <NAME>
        spec:
            provider: aws
            parameters:
        """
        # TODO

        # Secret Provider Class mamnifest for each environment are found in the /stack directory
        # we check if the secrets ARN exist to indicate that this particualr environment was created
        # and we can extract the config from the yaml file and install the manifest to K8s

        if test_creds_secret_arn is not None:
            basedir = os.getcwd()
            local_path = os.path.abspath(
                os.path.join(basedir, "stacks", "secret_provider_class_test.yaml")
            )

            with open(local_path, "r") as yaml_in:
                test_yaml_file = yaml.safe_load(yaml_in)

            test_secret_manifest = self.eks_cluster.add_manifest(
                "test_creds_secret", test_yaml_file
            )
            test_secret_manifest.node.add_dependency(test_namespace)
            test_secret_manifest.node.add_dependency(ascp_manifest)

        if prod_creds_secret_arn is not None:
            basedir = os.getcwd()
            local_path = os.path.abspath(
                os.path.join(basedir, "stacks", "secret_provider_class_prod.yaml")
            )

            with open(local_path, "r") as yaml_in:
                prod_yaml_file = yaml.safe_load(yaml_in)

            prod_secret_manifest = self.eks_cluster.add_manifest(
                "proddb_creds_secret", prod_yaml_file
            )
            prod_secret_manifest.node.add_dependency(prod_namespace)
            prod_secret_manifest.node.add_dependency(ascp_manifest)
