"""
Get S3 buckets in an AWS account and apply a incomplete multi-part uploads (MPU) Lifecycle rule to cleanup orphaned incomplete MPUs after 7 days.
Blog: https://aws.amazon.com/blogs/aws-cloud-financial-management/discovering-and-deleting-incomplete-multipart-uploads-to-lower-amazon-s3-costs/
"""

import boto3
from botocore.exceptions import ClientError
import os
import sys
import argparse
import time
import logging

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s: %(message)s",
)
logger = logging.getLogger()

parser = argparse.ArgumentParser(
    description="Program to add Incomplete MPU Lifecycle rule to specified S3 buckets."
)
parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Run the script in dry run mode. No changes will be made to the buckets.",
)

parser.add_argument(
    "--profile", required=True, help="The AWS profile to use. This is required."
)

args = parser.parse_args()

logger.info(f"Running in dry run mode: {args.dry_run}")
logger.info(f"Using AWS profile: {args.profile}")

session = boto3.Session(profile_name=args.profile)
s3_client = session.client("s3")


# Flag to run in dry run. No changes will be done to the buckets
DRY_RUN = args.dry_run

# Incomplete MPU Lifecycle rule to create
rule = {
    "Rules": [
        {
            "ID": "delete-incomplete-mpu-7days",
            "Status": "Enabled",
            "Filter": {"Prefix": ""},
            "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7},
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
        Bucket=bucket, LifecycleConfiguration=rule
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
        bucket_lifecycle = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket)
    except ClientError:
        # This means there are no lifecycle rules for the bucket. Create one
        logger.info(
            f"No Incomplete MPU rule exist for this bucket: {bucket}...Adding one"
        )

        if not DRY_RUN:
            response = create_incomplete_mpu_policy(bucket=bucket)

            # If there's a response, the rule was created
            if response is not None:
                logger.info(f"Lifecycle created for bucket {bucket}: \n{response}")
        else:
            logger.info("No changes done...Running in Dry run mode")

    # If there are already Lifecycle rules create for the bucket, check if the rules contain an Incomplete MPU rule
    else:
        logger.info(
            f"Bucket {bucket} has already created Lifecycle Rules: \nChecking if there is an Incomplete MPU rule in place..."
        )

        # Check if any existing rule has AbortIncompleteMultipartUpload
        mpu_rule_exists = False
        for rule in bucket_lifecycle["Rules"]:
            if rule.get("AbortIncompleteMultipartUpload"):
                logger.info(
                    f"The following Incomplete MPU rule already exists: {rule['ID']}. Nothing to do."
                )
                mpu_rule_exists = True
                break

        # If no MPU rule was found, create one
        if not mpu_rule_exists:
            logger.info(
                f"No Incomplete MPU rule exists for this bucket: {bucket}...Adding one"
            )

            if not DRY_RUN:
                # Append our rule to existing rules
                existing_rules = bucket_lifecycle["Rules"]
                existing_rules.append(rule["Rules"][0])

                updated_lifecycle = {"Rules": existing_rules}

                response = s3_client.put_bucket_lifecycle_configuration(
                    Bucket=bucket, LifecycleConfiguration=updated_lifecycle
                )
                logger.info(
                    f"Incomplete MPU Lifecycle rule created for bucket {bucket}: \n{response}"
                )
            else:
                logger.info(f"Not changing bucket {bucket}. Running in DRY RUN Mode")


if __name__ == "__main__":

    buckets = []

    if DRY_RUN:
        logger.info(
            "\033[32mRunning in DRY RUN mode. No changes will be done to the buckets\033[0m"
        )
        time.sleep(1)
        print()
    else:
        logger.info(
            "\033[91mRunning in LIVE mode. Changes will be done to the buckets\033[0m"
        )
        time.sleep(1)
        print()
        ack = input("Do you want to continue? (y/n): ").lower()
        if ack == "y":
            os.system("clear")
        else:
            os.system("clear")
            logger.info(f"Exiting...Goodbye!")
            sys.exit(0)

    print("Getting all buckets in the account...\n")
    buckets = s3_client.list_buckets()["Buckets"]

    # for bucket_name in buckets:
    run = True
    while run == True:
        for index, bucket_name in enumerate(buckets):
            print(f"{index+1}: {bucket_name['Name']}\n")

        bucket_index = input(
            "Select a bucket by index to check for Incomplete MPU Lifecycle rule, or 'a' for all (type 'exit' to quit): "
        ).lower()

        if bucket_index == "exit":
            os.system("clear")
            run = False
            logger.info(f"Exiting...Goodbye!")
            sys.exit(0)
            break

        elif bucket_index == "a":
            modify_buckets = input(
                f"Do you want to modify all buckets? (y/n): "
            ).lower()

            if modify_buckets == "y":
                logger.info("Applying Lifecycle rule to all buckets...")
                for bucket_name in buckets:
                    logger.info(
                        f"Checking bucket: {bucket_name['Name']} for Incomplete MPU Lifecycle rule"
                    )
                    get_incomplete_mpu_policy(bucket=bucket_name["Name"])
                    logger.info("Action completed succesfully!\n")
                    run = False
                    sys.exit(0)
                    break

            else:
                os.system("clear")
                logger.info(f"Exiting...No changes performed to buckets")
                run = False
                sys.exit(0)
                break

        else:
            selected_bucket = buckets[int(bucket_index) - 1]["Name"]
            print(f"\nThe bucket selected is: {selected_bucket}\n")
            modify_bucket = input(
                f"Do you want to modify the bucket: {selected_bucket}? (y/n): "
            ).lower()
            if modify_bucket == "y":

                get_incomplete_mpu_policy(bucket=selected_bucket)
                print()
            else:
                os.system("clear")
                logger.info(
                    f"Exiting...No changes performed to bucket: {selected_bucket}"
                )
                sys.exit(0)

            should_continue = input("Do you want to continue? (y/n): ").lower()
            if should_continue == "y":
                os.system("clear")
                continue
            else:
                run = False
                os.system("clear")
                logger.info(f"Exiting...Goodbye!")
                sys.exit(0)
                break

