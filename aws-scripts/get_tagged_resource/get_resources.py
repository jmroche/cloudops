"""
This script used the Python SDK (boto3) to interact with the ResourceGroupsTaggingAPI
and get a list of resources tagged for each AWS region of a given AWS account.
SDK doc: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/resourcegroupstaggingapi.html#ResourceGroupsTaggingAPI.Client.get_resources
"""

import boto3


# Create an ec2 client
ec2_client = boto3.client("ec2")

# USe the Resposne Service to desribe the regions
response = ec2_client.describe_regions()

# Save the regions to a list ot be used later
for item in response["Regions"]:
    print(item["RegionName"])

regions = [region["RegionName"] for region in response["Regions"]]


total_resources_per_region = {}

# For each region call the get_resource method and get all the resources
for region in regions:
    resource_group_client = boto3.client("resourcegroupstaggingapi", region_name=region)

    response = resource_group_client.get_resources(
        ResourcesPerPage=100
    )

    resource_groups = response["ResourceTagMappingList"]

    # check if there are more pagination token.
    # If the token is present this means additional resoruces need to be read
    # TODO: Check if this logic can be enhanced
    
    while response["PaginationToken"] != "":
        response = resource_group_client.get_resources(
        ResourcesPerPage=100,
        PaginationToken = response["PaginationToken"]
    )

    resource_groups += response

    print(f"Gathering resources in region: {region}...")

    total_resources_per_region[region] = resource_groups

print(total_resources_per_region)

