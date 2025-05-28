# S3 Incomplete Multipart Upload Lifecycle Manager

## Overview

This script helps manage AWS S3 storage costs by identifying and configuring lifecycle rules for incomplete multipart uploads (MPUs). Incomplete multipart uploads can accumulate over time and incur unnecessary storage costs. This tool allows you to add a lifecycle rule that automatically cleans up incomplete multipart uploads after 7 days.

## Background

Multipart uploads allow you to upload large objects to S3 in parts. However, if these uploads are not completed or aborted, they remain in your bucket and you continue to be charged for the storage. This script implements the best practices described in the [AWS blog post on discovering and deleting incomplete multipart uploads](https://aws.amazon.com/blogs/aws-cloud-financial-management/discovering-and-deleting-incomplete-multipart-uploads-to-lower-amazon-s3-costs/).

## Prerequisites

- Python 3.x
- Boto3 library
- AWS credentials configured with appropriate S3 permissions
- AWS CLI profile with access to the target S3 buckets

## Installation

1. Ensure you have Python 3.x installed
2. Install required dependencies:
   ```
   pip install boto3
   ```
3. Configure your AWS credentials using the AWS CLI:
   ```
   aws configure --profile your-profile-name
   ```

## Usage

```bash
python3 s3-incomplete-mpu.py --profile YOUR_AWS_PROFILE [--dry-run]
```

### Command Line Arguments

- `--profile` (required): Specifies the AWS profile to use for authentication
- `--dry-run` (optional): Runs the script without making any changes to buckets

### Interactive Workflow

1. The script lists all S3 buckets in your account
2. You can select a bucket by its index number or choose 'a' to process all buckets
3. The script checks if the selected bucket(s) already has an incomplete MPU lifecycle rule
4. If no rule exists, it adds one (unless in dry-run mode)
5. You can continue to check other buckets or exit

### Example

```bash
python3 s3-incomplete-mpu.py --profile production --dry-run
```

## Lifecycle Rule Details

The script applies the following lifecycle rule to selected buckets:

```json
{
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
```

This rule will automatically abort any incomplete multipart uploads that are more than 7 days old.

## Functions

### `create_incomplete_mpu_policy(bucket: str) -> dict`

Applies the lifecycle configuration to the specified bucket.

- **Parameters:**
  - `bucket` (str): The name of the bucket to apply the configuration to
- **Returns:**
  - `response` (dict): Dictionary containing information about the created lifecycle rule
- **Known Issue:**
  - In the current implementation, this function replaces all existing lifecycle rules with just the incomplete MPU rule. This means any other lifecycle rules previously configured on the bucket will be deleted.

### `get_incomplete_mpu_policy(bucket: str)`

Checks if a bucket has existing lifecycle rules, particularly for incomplete MPUs.

- **Parameters:**
  - `bucket` (str): The name of the bucket to check and/or modify
- **Behavior:**
  - If no lifecycle rules exist, creates an incomplete MPU rule
  - If lifecycle rules exist but none for incomplete MPUs, adds one
  - If an incomplete MPU rule already exists, does nothing

## Safety Features

- Dry-run mode to preview changes without modifying buckets
- Color-coded console output to distinguish between dry-run and live modes
- Confirmation prompts before making changes
- Option to exit at various points in the workflow

## Limitations

- The script only adds a single lifecycle rule for incomplete MPUs
- **Important:** The current implementation replaces all existing lifecycle rules when adding the incomplete MPU rule. This means any other lifecycle configurations on the bucket will be lost.
- The script operates on one bucket at a time through interactive selection or can process all buckets at once

## Recommended Fixes

To preserve existing lifecycle rules when adding the incomplete MPU rule, the script should be modified to:

1. Retrieve the existing lifecycle rules (if any)
2. Check if an incomplete MPU rule already exists
3. If no incomplete MPU rule exists, add the new rule to the existing rules
4. Apply the combined rules back to the bucket

This would ensure that other lifecycle configurations are preserved while adding the incomplete MPU rule.

## Author

Jose Roche - josemroche@gmail.com