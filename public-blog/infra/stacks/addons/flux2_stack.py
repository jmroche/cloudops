"""
Stack to generate the manifest to install and bootstrap Flux in the EKS cluster created in the the EKS Stack.
"""
import requests
import yaml
from aws_cdk import aws_eks as eks
from aws_cdk import aws_secretsmanager as sm
from aws_cdk import Stack
from constructs import Construct
from constructs import Node


class FluxStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        cluster: eks.Cluster,
        flux_version=None,
        secret_name=None,
        repo_url=None,
        repo_branch=None,
        repo_path=None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.cluster = cluster
        self.flux_version = flux_version

        # Get the ARN for Github token stored in secrets manager.

        def get_latest_flux_version():
            """Grab the latest version of the FluxV2 application and return it to the caller.

            Returns:
                str: Returns a string with the latest tag (i.e. 'v0.24.1')
            """
            # Check if we defined a value for the version in the context, if not then get the latest from their github
            flux_env_context = self.node.try_get_context("flux")

            if flux_env_context.get("flux_version") is not None:
                return flux_env_context.get("flux_version")

            else:

                flux_url = "https://api.github.com/repos/fluxcd/flux2/releases/latest"
                result = requests.get(flux_url)
                result.raise_for_status()
                result_json = result.json()
                return result_json["tag_name"]

        def get_flux_manifest(tag_name):
            """Given a tag value, preapre a downlaod url for the latests FluxV2 installation manifest from the Github repo.

            Args:
                tag_name (str): FluxV2 version to download.

            Returns:
                str: URL to the FluxV2 installation manifest version defined by the tag value.
            """
            manifest_url = f"https://github.com/fluxcd/flux2/releases/download/{tag_name}/install.yaml"
            return manifest_url

        flux_version = get_latest_flux_version()
        flux_manifest_url = get_flux_manifest(tag_name=flux_version)

        manifest_data = requests.get(flux_manifest_url)
        manifest_data.raise_for_status()
        manifest_text = manifest_data.text

        self.flux_manifest_yaml = list(yaml.load_all(manifest_text, Loader=yaml.Loader))
