from platform import node
from platform import release

from aws_cdk import aws_eks as eks
from aws_cdk import aws_iam as iam
from aws_cdk import Stack
from constructs import Construct


class ExternalDNSStack(Stack):
    def __init__(
        self, scope: Construct, id: str, cluster: eks.Cluster, **kwargs
    ) -> None:
        super().__init__(scope=scope, id=id, **kwargs)

        self.cluster = cluster

        # Create Service Account to install Externl DNS

        external_dns_service_account = self.cluster.add_service_account(
            "external-dns-service-account",
            name="external-dns-sa",
            namespace="kube-system",
        )

        # Give the SA access to modify records in the public hosted zone
        external_dns_service_account.add_to_principal_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["route53:ChangeResourceRecordSets"],
                resources=[self.node.try_get_context("rds_public_hosted_zone")],
            )
        )

        # Allow the SA to liist all records and hosted zones
        external_dns_service_account.add_to_principal_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["route53:ListHostedZones", "route53:ListResourceRecordSets"],
                resources=["*"],
            )
        )

        # Install the External DNS Helm chart

        external_dns_helm_chart = self.cluster.add_helm_chart(
            "external-dns-helm-chart",
            chart="external-dns",
            repository="https://kubernetes-sigs.github.io/external-dns/",
            version="1.7.1",
            release="external-dns",
            namespace="kube-system",
            values={
                "serviceAccount": {"create": False, "name": "external-dns-sa"},
                "resources": {"requests": {"cpu": "0.25", "memory": "0.5Gi"}},
            },
        )
