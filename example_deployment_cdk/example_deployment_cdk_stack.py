from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_rds as rds,
    CfnOutput,
    Duration,
    RemovalPolicy
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

        # Allow inbound traffic on port 22 (SSH) from anywhere
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(22),
            "Allow SSH traffic"
        )

        # Create PostgreSQL instance
        db_instance = rds.DatabaseInstance(self, "PostgreSQLInstance",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_14),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[security_group],
            database_name="your_db_name",
            credentials=rds.Credentials.from_generated_secret("postgres"),  # This will generate a secret in AWS Secrets Manager
            backup_retention=Duration.days(7),
            removal_policy=RemovalPolicy.DESTROY  # Be careful with this in production
        )

        # Allow EC2 instance to access the RDS instance
        db_instance.connections.allow_default_port_from(security_group)

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
                yum install -y python3 python3-pip nginx git postgresql

                # Create uvicorn.service file
                cat << EOF > /etc/systemd/system/uvicorn.service
                [Unit]
                Description=uvicorn daemon
                After=network.target

                [Service]
                User=ec2-user
                Group=ec2-user
                WorkingDirectory=/home/ec2-user/app/api_project
                ExecStart=/home/ec2-user/app/venv/bin/python -m uvicorn api_project.asgi:application --host 0.0.0.0 --port 8000

                [Install]
                WantedBy=multi-user.target
                EOF

                # Reload systemd to recognize the new service
                systemctl daemon-reload

                # Enable the service to start on boot
                systemctl enable uvicorn.service
            ''')
        )

        # Output the database endpoint
        CfnOutput(self, "DBEndpoint", value=db_instance.db_instance_endpoint_address)
        CfnOutput(self, "DBPort", value=db_instance.db_instance_endpoint_port)
        CfnOutput(self, "DBName", value=db_instance.instance_identifier)
        CfnOutput(self, "DBSecretName", value=db_instance.secret.secret_name)

        # Output the instance ID and public IP
        CfnOutput(self, "InstanceId", value=instance.instance_id)
        CfnOutput(self, "PublicIP", value=instance.instance_public_ip)