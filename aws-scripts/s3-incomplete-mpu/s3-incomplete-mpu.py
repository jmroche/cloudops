"""
Get S3 buckets in an AWS account and apply a incomplete multi-part uploads (MPU) Lifecycle rule to cleanup orphaned incomplete MPUs after 7 days.
Blog: https://aws.amazon.com/blogs/aws-cloud-financial-management/discovering-and-deleting-incomplete-multipart-uploads-to-lower-amazon-s3-costs/
"""

import boto3
from botocore.exceptions import ClientError


s3_client = boto3.client("s3")

# Flag to run in dry run. No changes will be done to the buckets
DRY_RUN = True

# Incomplete MPU Lifecycle rule to create
rule = {
    "Rules": [
        {
            "ID": "delete-incomplete-mpu-7days",
            "Status": "Enabled",
            "Filter": {
                "Prefix": ""
            },
            "AbortIncompleteMultipartUpload": {
                "DaysAfterInitiation": 7
            }
        }
    ]
}


def create_incomplete_mpu_policy(bucket: str) -> dict:
    """Function that calls the S3 API and puts a lifecycle configuration on the bucket passed to it
        and returns the lifecycle policy id to the caller

    Args:
        bucket (str): The name of the bucket to apply the configuration onto.

    Returns: 
        response (dict): Dictionary containing the information of the Lifecycle Rule created.
    """

    response = s3_client.put_bucket_lifecycle_configuration(
        Bucket = bucket,
        LifecycleConfiguration = rule
    )
    return response


def get_incomplete_mpu_policy(bucket: str):
    """Given a bucket 'bucket' check if it has Lifecycle rules, in specific MPU Lifecycle rules. 
        If there aren't any Lifecycle rules create an MPU Lifecycle rule. If there are other
        Lifecycle rules, check first to ensure none of the rules is an MPU rule, by checking 
        if a rule with a statement 'AbortIncompleteMultipartUpload' exist.

    Args:
        bucket (str): bucket name to check and/or create rule.
    """

    # Check if there are lifecycle rules created on the bucket. Will return with ClientError if no rules configured on the bucket
    try:
        bucket_lifecycle = s3_client.get_bucket_lifecycle_configuration(
            Bucket=bucket
        )
    except ClientError:
        # This means there are no lifecycle rules for the bucket. Create one
        print(f"No Incomplete MPU rule exist for this bucket: {bucket}...Adding one")

        if not DRY_RUN:
            response = create_incomplete_mpu_policy(bucket=bucket)

            # If there's a response, the rule was created
            if response is not None:
                print(f"Lifecycle created for bucket {bucket}: \n{response}")
        else:
            print("No changes done...Running in Dry run mode")

    # If there are already Lifecycle rules create for the bucket, check if the rules contain an Incomplete MPU rule 
    else:
        print(f"Bucket {bucket} has already created Lifecycle Rules: \nChecking if there is an Incomplete MPU rule in place...")

        # Go through all the lifecycle rules configured in the bucket
        for rule in bucket_lifecycle["Rules"]:

            if rule.get("AbortIncompleteMultipartUpload"):
                print(f"The following Incomplete MPU rule already exist: {rule['ID']}. Nothing to do.")
            else:
                print(f"No Incomplete MPU rule exist for this bucket: {bucket}...Adding one")

                if not DRY_RUN:
                    response = create_incomplete_mpu_policy(bucket=bucket)
                    print(f"Incomplete MPU Lifecycle rule created for bucket {bucket}: \n{response}")
                else:
                    print(f"Not changing bucket {bucket}. Running in DRY RUN Mode")


if __name__ == "__main__":

    buckets = []
    buckets = s3_client.list_buckets()["Buckets"]

    for bucket_name in buckets:
    
        get_incomplete_mpu_policy(bucket=bucket_name["Name"])



