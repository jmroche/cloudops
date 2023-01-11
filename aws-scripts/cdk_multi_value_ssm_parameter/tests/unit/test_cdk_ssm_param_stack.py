import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk_ssm_param.cdk_ssm_param_stack import CdkSsmParamStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk_ssm_param/cdk_ssm_param_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CdkSsmParamStack(app, "cdk-ssm-param")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
