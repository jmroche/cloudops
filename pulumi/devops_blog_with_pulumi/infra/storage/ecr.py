"""
Component that creates the Elastic Container Registry (ECR) to
push images from GitHub Actions and deploy them to EKS via GitOps.
"""
import pulumi
import pulumi_aws as aws


class ECRComponent(pulumi.ComponentResource):
    def __init__(self, name, project_name, base_tags, opts=None):
        super().__init__("devopsinthecloud:utils:ecr", name, None, opts)

        self.project_name = project_name
        self.base_tags = base_tags

        # Create ECR REpository

        self.ecr_repo = aws.ecr.Repository(
            f"{project_name}-ecr-repository",
            name=f"{project_name}-image-repository",
            image_tag_mutability="MUTABLE",
            image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(
                scan_on_push=True,
            ),
            force_delete=True,
            tags={**base_tags, "Name": f"{project_name}-ecr-repository"},
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Save the repo arn in SSM Parameter Store

        ecr_repo_arn_param = aws.ssm.Parameter(
            f"{project_name}-ecr-repo-arn",
            name=f"/prod/{project_name}/ecr-repo-arn",
            type="String",
            value=self.ecr_repo.arn,
            opts=pulumi.ResourceOptions(parent=self),
            tags={**base_tags, "Name": f"{project_name}-ecr-repo-arn"},
        )
