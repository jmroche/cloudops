#!/bin/bash
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent
curl -o kubectl https://amazon-eks.s3.us-west-2.amazonaws.com/1.21.2/2021-07-05/bin/linux/amd64/kubectl
chmod +x ./kubectl
mv ./kubectl /usr/bin
curl -s https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash -
curl -s https://fluxcd.io/install.sh | bash -
aws eks update-kubeconfig --name ${Token[TOKEN.681]} --region us-east-1 --kubeconfig '/home/ec2-user/.kube/config'
chown ec2-user:ec2-user /home/ec2-user/.kube/config
yum update -y
cat << EOF > /home/ec2-user/get_secrets.py # Program to use boto3 to grab AWS Secrets Manager secrets needed to bootstrap Flux from the bastion host.
# This program will be copied to the bastion instance to be ran there.
import base64
import json
import os
import subprocess
import time

import boto3
from botocore.exceptions import ClientError


def get_secret():

    secret_name = os.environ.get("GITHUB_TOKEN_SECRET_ARN")
    secret_name = (
        "arn:aws:secretsmanager:us-east-1:601749221392:secret:GITHUB_TOKEN-XBtDg1"
    )
    region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        if e.response["Error"]["Code"] == "DecryptionFailureException":
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "InternalServiceErrorException":
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "InvalidParameterException":
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "InvalidRequestException":
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "ResourceNotFoundException":
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS key.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if "SecretString" in get_secret_value_response:
            secret = get_secret_value_response["SecretString"]
            return secret
        else:
            decoded_binary_secret = base64.b64decode(
                get_secret_value_response["SecretBinary"]
            )
            return decoded_binary_secret


secret_value = get_secret()

secret_json = json.loads(secret_value)
print(f"export GITHUB_USER={secret_json['username']}")
print(f"export GITHUB_TOKEN={secret_json['GITHUB_TOKEN']}")

EOF

pip3 install boto3
cat << 'EOF' > /home/ec2-user/set_env_vars.sh
#!/bin/bash

FILE="/home/ec2-user/.bashrc"

output=$(python3 /home/ec2-user/get_secrets.py)
echo "${output}" >> $FILE

EOF

chmod +x /home/ec2-user/set_env_vars.sh
chown ec2-user:ec2-user /home/ec2-user/set_env_vars.sh
chown ec2-user:ec2-user /home/ec2-user/get_secrets.py
runuser -l ec2-user -c 'cp /home/ec2-user/.bashrc /home/ec2-user/.bashrc_bkp'
runuser -l ec2-user -c 'eval `sh /home/ec2-user/set_env_vars.sh`'
echo export PATH='/usr/local/bin:$PATH' >> /home/ec2-user/.bashrc
