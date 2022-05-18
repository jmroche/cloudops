"""
Script to list all packages with the version installed in the AWS Lambda Execution environment runtime.
Documentation: https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
"""

import json
import pkg_resources

def lambda_handler(event, context):
    # Convert to string remove split by space and use the first and second position to cosntruct the dictionary
    result = {str(pkg).split()[0]:str(pkg).split()[1] for pkg in pkg_resources.working_set}
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }

"""

Sample Response:


{
  "statusCode": 200,
  "body": "{\"urllib3\": \"1.26.6\", \"six\": \"1.16.0\", \"simplejson\": \"3.17.2\", \"s3transfer\": \"0.5.2\", \"python-dateutil\": \"2.8.2\", \"jmespath\": \"0.10.0\", \"botocore\": \"1.23.32\", \"boto3\": \"1.20.32\", \"awslambdaric\": \"2.0.0\", \"setuptools\": \"58.1.0\", \"pip\": \"22.0.4\"}"
}
"""