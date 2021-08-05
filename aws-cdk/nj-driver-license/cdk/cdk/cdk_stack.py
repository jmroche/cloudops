from aws_cdk import core as cdk
from aws_cdk import(
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_ecs_patterns as ecs_patterns,
    aws_applicationautoscaling as applicationautoscaling,
    aws_ssm as ssm
)

# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core


class CdkStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a VPC construct with AZs for private Fargte and public for 1 Nat Gateway
        vpc = ec2.Vpc(self, "FargateVPC", max_azs=3, enable_dns_hostnames=True, enable_dns_support=True, nat_gateways=1)


        # SNS Topic 
        sns_topic = sns.Topic(self, 
        "sns-topic",
        display_name="NJ DMV License Appointment Checker",
        topic_name="nj-dmv-scraper-email-topic")

        # SNS Topic subscription for an email to receive the push notifications
        # email address is setup in the context inside cdk.json.
        # Additionally could be passed as a flag: cdk synth -c email_address=value
        sns_topic.add_subscription(subs.EmailSubscription(
            email_address=self.node.try_get_context("email_address")))


        # Create an ECS Cluster
        ecs_cluster = ecs.Cluster(self, "ECSCluster", vpc=vpc)
        #Example of a load balanced Fargate service 
        # ecs_patterns.ApplicationLoadBalancedFargateService(self,
        #     "FargateService",
        #     cluster=ecs_cluster,
        #     cpu=512,
        #     desired_count=1,
        #     task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
        #         image=ecs.ContainerImage.from_asset(directory="../src")),
        #     memory_limit_mib=2048,
        #     public_load_balancer=False
        # )

        # Create a scheduled Fargate task that will run every 10 minutes
        # It builds the image from the Docker file in the src directory
        task = ecs_patterns.ScheduledFargateTask(self,
            "ScheduledFargateService",
            cluster=ecs_cluster,
            vpc=vpc,
            desired_task_count=1,
            scheduled_fargate_task_image_options=ecs_patterns.ScheduledFargateTaskImageOptions(
                image=ecs.ContainerImage.from_asset(directory="../src"),
                memory_limit_mib=2048,
                cpu=512,
                environment=["FARGATE"]),
            schedule=applicationautoscaling.Schedule.cron(minute="0/10"))

        # Allow the ECS task to publish to the sns topic
        sns_topic.grant_publish(task.task_definition.task_role)


        # Store the Topic ARN in Parameter store in order to push it 
        # to the task as an environment variable and be avialble
        # to the notification logic
        ssm_param = ssm.StringParameter(self,
        "sns-topic-arn",
        description="SNS Topic ARN",
        parameter_name="sns-topic-arn",
        string_value=sns_topic.topic_arn)

        # Give access to read the SSM parameters to the task role
        ssm_param.grant_read(task.task_definition.task_role) 