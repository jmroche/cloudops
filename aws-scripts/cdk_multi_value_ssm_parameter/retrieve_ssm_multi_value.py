"""
Small script to get multiple values serialized into a SSM Parameter value
"""

import boto3
import json

# Create a ssm boto3 client to interact with the SSM API
client = boto3.client('ssm')


response = client.get_parameter(
    Name="StringParamMultipleValues",
    WithDecryption=True
)

# The SSM response is an object and we need access the value as such
# Then we deserialize it to a list of dictionaries
resposne_values =  json.loads(response["Parameter"]["Value"])

# Print the list of dictionaries
print(resposne_values)