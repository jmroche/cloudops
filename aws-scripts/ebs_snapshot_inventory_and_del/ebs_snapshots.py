"""
This script will scan EC2 EBS Snapshots. It will create a DynamoDB table and store the snapshot information (snapshot_id, snapshot_age, volume_size,
snapshot_state and date_taken). It will create a report for snapshots that are older than certain amount of time, for the customer to decide if 
snapshots older that selected age should be deleted.
"""

import boto3
import datetime
from datetime import timezone, date
import os
from botocore.exceptions import ClientError
import time

ec2_client = boto3.client("ec2")
dynamodb_client = boto3.client("dynamodb")


# Check if DynamoDB Table exist, if not, create one
def create_ebs_snapshots_table(dynamodb_table: str = None) -> dict:
    """Given a table name, it will create a DynamoDB table with required Snapshot attributes.

    Args:
        dynamodb_table (str, optional): DynamoDB Table name. Defaults to None.

    Returns:
        dict: Returns the result of the DynamoDB create command.
    """
    if dynamodb_table:

        # Check if the Dynamo DB exists
        try:
            table = dynamodb_client.describe_table(TableName=dynamodb_table)
        except dynamodb_client.exceptions.ResourceNotFoundException:
            print(f"table not found...Creating table: {dynamodb_table}")
            table = dynamodb_client.create_table(
                TableName="EbsSnapshots",
                KeySchema=[
                    {
                        "AttributeName": "snapshot_id",
                        "KeyType": "HASH",
                    },  # Partition key
                    # {"AttributeName": "snapshot_age", "KeyType": "RANGE"},  # Sort key
                ],
                AttributeDefinitions=[
                    {"AttributeName": "snapshot_id", "AttributeType": "S"},
                    # {"AttributeName": "snapshot_age", "AttributeType": "N"},
                ],
                Tags=[
                    {"Key": "auto-delete", "Value": "never"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            time.sleep(7)  # Sleep 5 seconds to allow DynamoDB to be created
            return table
        else:
            #
            return f"table {dynamodb_table} already exist."


def add_snapshot_item(item: dict, dynamodb_table: str) -> dict:
    """Given an item and a DynamoDB table, the function will add item 'item' to the DynamoDB table 'dynamodb_table'.

    Args:
        item (dict): EBS Snapshot item to add to the DynamoDB Table.
        dynamodb_table (str): Name of the DynamoDB table to update.

    Returns:
        dict: Result of the put_item command.
    """
    response = dynamodb_client.put_item(Item=item, TableName=dynamodb_table)
    return response


def get_snapshot_item(snapshot_id, dynamodb_table) -> dict:
    """Given a Snapshot Id and DynamoDB Table, check if the item exists in the table.

    Args:
        snapshot_id (_type_): Snapshot_id to look up in the DynamoDB Table.
        dynamodb_table (_type_): Name of the DynamoDB table to check.

    Returns:
        dict: Result of the put_item command.
    """
    try:
        response = dynamodb_client.get_item(
            Key={"snapshot_id": {"S": snapshot_id}}, TableName=dynamodb_table
        )
    except ClientError as e:
        # print(e.response['Error']['Message'])
        return
    else:
        return response


if __name__ == "__main__":

    dynamodb_table = os.environ.get("DYNAMO_TABLE", "EbsSnapshots")
    ebs_snapshots_table = create_ebs_snapshots_table(dynamodb_table=dynamodb_table)
    print(ebs_snapshots_table)

    result = ec2_client.describe_snapshots(OwnerIds=[""])

    today = datetime.datetime.now(timezone.utc)
    total_volumes_size: int = 0
    # snapshots_data = []

    for snapshot in result["Snapshots"]:
        # snapshots_data.append({
        #     "snapshot_id": snapshot["SnapshotId"],
        #     "volume_size": snapshot["VolumeSize"],
        #     "date_taken": (snapshot["StartTime"]).strftime("%Y, %m, %d:%H:%M:%S"),
        #     "snapshot_age": int((today - snapshot["StartTime"]).days),
        #     "snapshot_state": snapshot["State"],
        #     "snapshot_encrypted": bool(snapshot["Encrypted"])
        # })
        result = get_snapshot_item(
            snapshot_id=snapshot["SnapshotId"], dynamodb_table=dynamodb_table
        )
        # print(f"Result: {result}")
        if result.get("Item") is None:
            add_snapshot_item(
                item={
                    "snapshot_id": {"S": snapshot["SnapshotId"]},
                    "volume_size": {"N": str(snapshot["VolumeSize"])},
                    "date_taken": {
                        "S": (snapshot["StartTime"]).strftime("%Y, %m, %d:%H:%M:%S")
                    },
                    "snapshot_age": {"N": str((today - snapshot["StartTime"]).days)},
                    "snapshot_state": {"S": snapshot["State"]},
                    "snapshot_encrypted": {"BOOL": snapshot["Encrypted"]},
                },
                dynamodb_table=dynamodb_table,
            )
            print(f'Item: {snapshot["SnapshotId"]} added to the Table {dynamodb_table}')
        else:
            print(f'Snapshot id: {snapshot["SnapshotId"]} already exist, nothing done.')
