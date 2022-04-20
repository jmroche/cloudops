# Cloudops


Collection of different projects and learning experience around cloud technologies I'm experimenting with. This is a work in progress, and will be adding other projects soon.


* [/aws-cdk/nj-driver-license/](https://github.com/jmroche/cloudops/tree/main/aws-cdk/nj-driver-license): AWS CDK Project and Python application. This projects uses ```Selenium``` to scrape New Jersey's DMV site and look for available appointments for out of state driver license change. The code will run on a schedule of every 10 minutes and use AWS SNS to send a notification to the user once and available appointment is found. 
    * The CDK project creates the infrastructure for the application code to run. Here's we create a VPC, SNS topic, ECS Cluster, and Scheduled ECS Fargate task definition. This will provide a serverless environment that requires no intervention to operate.
* [cloudops/aws-scripts/](https://github.com/jmroche/cloudops/tree/main/aws-scripts): Contains a collection of scripts to automate several aspects of operating in AWS.
    * /ebs_snapshot_inventory_and_del: This script will scan an AWS Account looking for EC2 EBS Snapshots. It will create a DynamoDB table and store the snapshot information (snapshot_id, snapshot_age, volume_size, snapshot_state and date_taken). It will create a report for snapshots that are older than certain amount of time, for the customer to decide if snapshots older that selected age should be deleted.
    * /s3-incomplete-mpu: Get S3 buckets in an AWS account and apply a incomplete multi-part uploads (MPU) Lifecycle rule to cleanup orphaned incomplete MPUs after 7 days. It extends the ideas covered in this [blog](https://aws.amazon.com/blogs/aws-cloud-financial-management/discovering-and-deleting-incomplete-multipart-uploads-to-lower-amazon-s3-costs/). The  [README](https://github.com/jmroche/cloudops/blob/main/aws-scripts/s3-incomplete-mpu/README.md) goes in detail on how the logic works.
        * /[s3-incomplete-mpu](https://github.com/jmroche/cloudops/tree/main/aws-scripts/s3-incomplete-mpu)/s3-mpu-cdk: Takes the above idea and takes the automation a step further by creating an event-driven and serverless architecture to detect when new buckets are created to apply the rules automatically, with no human intervention. README post coming soon.

