import aws_cdk as core
import aws_cdk.assertions as assertions

from example_deployment_cdk.example_deployment_cdk_stack import ExampleDeploymentCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in example_deployment_cdk/example_deployment_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = ExampleDeploymentCdkStack(app, "example-deployment-cdk")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
