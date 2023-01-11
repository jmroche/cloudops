from aws_cdk import (
    # Duration,
    Stack,
    aws_ssm as ssm
)

import json

from constructs import Construct

class CdkSsmParamStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Sample dictionaries to test saving multiple values into one SSM Parameter
        ec2_in_running_state = {
            "state": "running",
            "types": [
            {
                "type": "x1e.8xlarge",
                "count": 3
            },
            {
                "type": "m4.xlarge",
                "count": 1
            },
            {
                "type": "t2.medium",
                "count": 1
            },
            {
                "type": "t2.micro",
                "count": 112
            }
        ]}

        ec2_in_stopped_state = {
            "state": "stopped",
            "types": [
            {
                "type": "m4.large",
                "count": 1
            }
            ]
        }

        # Serialize the dictionaries into a string containing a list of dictionaries.
        parameters_serialized_list = json.dumps([ec2_in_running_state, ec2_in_stopped_state], indent=2)


        # Create and and save the SSM parameter
        new_ssm_parameter = ssm.StringParameter(
            self,
            "ssm-string-parameter-with-multiple-values",
            description="Saving JSON objects as string list parameters in SSM via AWS CDK",
            parameter_name="StringParamMultipleValues",
            string_value=parameters_serialized_list
        )

        


