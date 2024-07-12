from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    CfnOutput
)
from constructs import Construct

class ExampleDeploymentCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create VPC
        vpc = ec2.Vpc(self, "DjangoScraperVPC",
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
                ec2.SubnetConfiguration(name="Private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=24)
            ]
        )

        # Create Security Group
        security_group = ec2.SecurityGroup(self, "DjangoScraperSG",
            vpc=vpc,
            allow_all_outbound=True,
            description="Security group for Django Scraper EC2 instance"
        )

        # Allow inbound traffic on port 80 (HTTP) from anywhere
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "Allow HTTP traffic"
        )

        # Create IAM Role for EC2
        role = iam.Role(self, "DjangoScraperEC2Role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )

        # Add necessary policies to the role
        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))
        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess"))

        # Create Key Pair
        key_pair = ec2.CfnKeyPair(self, "DjangoScraperKeyPair",
            key_name="django-scraper-key"
        )

        # Create EC2 Instance
        instance = ec2.Instance(self, "DjangoScraperInstance",
            instance_type=ec2.InstanceType("t3.micro"),
            machine_image=ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group=security_group,
            role=role,
            key_name=key_pair.key_name,
            user_data=ec2.UserData.custom('''
                #!/bin/bash
                yum update -y
                yum install -y python3 python3-pip nginx git
                pip3 install gunicorn
            ''')
        )

        # Output the instance ID and public IP
        CfnOutput(self, "InstanceId", value=instance.instance_id)
        CfnOutput(self, "PublicIP", value=instance.instance_public_ip)