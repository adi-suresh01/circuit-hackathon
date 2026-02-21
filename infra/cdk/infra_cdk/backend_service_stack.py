from __future__ import annotations

from aws_cdk import (
    Aws,
    CfnOutput,
    CfnParameter,
    Duration,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct


def _to_bool_text(value: object | None, *, default: bool) -> str:
    if value is None:
        return "true" if default else "false"
    return "true" if str(value).strip().lower() in {"1", "true", "yes", "on"} else "false"


def _to_int(value: object | None, *, default: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


class BackendServiceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        image_tag = str(self.node.try_get_context("imageTag") or "latest")
        ecr_repo_name = str(self.node.try_get_context("ecrRepoName") or "circuit-backend")
        desired_count = _to_int(self.node.try_get_context("desiredCount"), default=0)
        task_cpu = _to_int(self.node.try_get_context("taskCpu"), default=1024)
        task_memory_mib = _to_int(self.node.try_get_context("taskMemoryMiB"), default=2048)
        dd_service = str(self.node.try_get_context("ddService") or "circuit-backend")
        dd_env = str(self.node.try_get_context("ddEnv") or "prod")
        dd_version = str(self.node.try_get_context("ddVersion") or image_tag)
        dd_site = str(self.node.try_get_context("ddSite") or "datadoghq.com")
        dd_api_key_secret_arn = str(self.node.try_get_context("ddApiKeySecretArn") or "").strip()
        enable_datadog_agent_ctx = self.node.try_get_context("enableDatadogAgent")
        enable_datadog_agent = (
            enable_datadog_agent_ctx is not None
            and str(enable_datadog_agent_ctx).strip().lower() in {"1", "true", "yes", "on"}
        ) or (enable_datadog_agent_ctx is None and bool(dd_api_key_secret_arn))
        dd_trace_enabled = _to_bool_text(
            self.node.try_get_context("ddTraceEnabled"),
            default=enable_datadog_agent,
        )
        dd_logs_injection = _to_bool_text(
            self.node.try_get_context("ddLogsInjection"),
            default=True,
        )
        log_level = str(self.node.try_get_context("logLevel") or "INFO")

        neo4j_uri_param = CfnParameter(
            self,
            "Neo4jUri",
            type="String",
            description="Neo4j Bolt URI, e.g. bolt://host:7687",
        )
        neo4j_username_secret_arn_param = CfnParameter(
            self,
            "Neo4jUsernameSecretArn",
            type="String",
            description="Secrets Manager ARN containing NEO4J_USERNAME as plaintext secret value",
        )
        neo4j_password_secret_arn_param = CfnParameter(
            self,
            "Neo4jPasswordSecretArn",
            type="String",
            description="Secrets Manager ARN containing NEO4J_PASSWORD as plaintext secret value",
        )
        bedrock_model_id_param = CfnParameter(
            self,
            "BedrockModelId",
            type="String",
            default="nvidia.nemotron-nano-12b-v2",
            description="Bedrock model id used by /extract",
        )

        vpc = ec2.Vpc(
            self,
            "BackendVpc",
            max_azs=2,
            nat_gateways=1,
        )

        cluster = ecs.Cluster(
            self,
            "BackendCluster",
            vpc=vpc,
            container_insights=True,
        )

        repository = ecr.Repository(
            self,
            "BackendRepository",
            repository_name=ecr_repo_name,
            image_scan_on_push=True,
            removal_policy=RemovalPolicy.RETAIN,
            empty_on_delete=False,
        )

        task_role = iam.Role(
            self,
            "BackendTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Application task role for backend runtime access",
        )

        execution_role = iam.Role(
            self,
            "BackendExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                )
            ],
            description="Execution role for ECS image pull/logging/secret env injection",
        )

        secret_arns: list[str] = [
            neo4j_username_secret_arn_param.value_as_string,
            neo4j_password_secret_arn_param.value_as_string,
        ]
        if dd_api_key_secret_arn:
            secret_arns.append(dd_api_key_secret_arn)

        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["*"],
            )
        )
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["*"],
            )
        )
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=secret_arns if secret_arns else ["*"],
            )
        )

        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue", "kms:Decrypt"],
                resources=secret_arns if secret_arns else ["*"],
            )
        )

        task_definition = ecs.FargateTaskDefinition(
            self,
            "BackendTaskDefinition",
            cpu=task_cpu,
            memory_limit_mib=task_memory_mib,
            task_role=task_role,
            execution_role=execution_role,
        )

        api_log_group = logs.LogGroup(
            self,
            "ApiLogGroup",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.RETAIN,
        )
        datadog_log_group = logs.LogGroup(
            self,
            "DatadogLogGroup",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.RETAIN,
        )

        neo4j_username_secret = secretsmanager.Secret.from_secret_complete_arn(
            self,
            "Neo4jUsernameSecret",
            neo4j_username_secret_arn_param.value_as_string,
        )
        neo4j_password_secret = secretsmanager.Secret.from_secret_complete_arn(
            self,
            "Neo4jPasswordSecret",
            neo4j_password_secret_arn_param.value_as_string,
        )

        api_environment = {
            "APP_ENV": "production",
            "LOG_LEVEL": log_level,
            "AWS_REGION": Aws.REGION,
            "BEDROCK_MODEL_ID": bedrock_model_id_param.value_as_string,
            "NEO4J_URI": neo4j_uri_param.value_as_string,
            "DD_SERVICE": dd_service,
            "DD_ENV": dd_env,
            "DD_VERSION": dd_version,
            "DD_AGENT_HOST": "127.0.0.1",
            "DD_TRACE_ENABLED": dd_trace_enabled,
            "DD_LOGS_INJECTION": dd_logs_injection,
        }
        api_secrets = {
            "NEO4J_USERNAME": ecs.Secret.from_secrets_manager(neo4j_username_secret),
            "NEO4J_PASSWORD": ecs.Secret.from_secrets_manager(neo4j_password_secret),
        }

        api_container = task_definition.add_container(
            "api",
            image=ecs.ContainerImage.from_ecr_repository(repository, image_tag),
            environment=api_environment,
            secrets=api_secrets,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="api",
                log_group=api_log_group,
            ),
            essential=True,
        )
        api_container.add_port_mappings(
            ecs.PortMapping(container_port=8080, protocol=ecs.Protocol.TCP)
        )

        if enable_datadog_agent:
            datadog_kwargs: dict[str, object] = {
                "image": ecs.ContainerImage.from_registry("public.ecr.aws/datadog/agent:7"),
                "essential": False,
                "environment": {
                    "ECS_FARGATE": "true",
                    "DD_SITE": dd_site,
                    "DD_ENV": dd_env,
                    "DD_APM_ENABLED": "true",
                    "DD_LOGS_ENABLED": "true",
                    "DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL": "true",
                    "DD_DOGSTATSD_NON_LOCAL_TRAFFIC": "true",
                },
                "logging": ecs.LogDrivers.aws_logs(
                    stream_prefix="datadog-agent",
                    log_group=datadog_log_group,
                ),
            }
            if dd_api_key_secret_arn:
                dd_api_key_secret = secretsmanager.Secret.from_secret_complete_arn(
                    self,
                    "DatadogApiKeySecret",
                    dd_api_key_secret_arn,
                )
                datadog_kwargs["secrets"] = {
                    "DD_API_KEY": ecs.Secret.from_secrets_manager(dd_api_key_secret)
                }

            datadog_container = task_definition.add_container(
                "datadog-agent",
                **datadog_kwargs,
            )
            datadog_container.add_port_mappings(
                ecs.PortMapping(container_port=8126, protocol=ecs.Protocol.TCP),
                ecs.PortMapping(container_port=8125, protocol=ecs.Protocol.UDP),
            )

        repository.grant_pull(execution_role)

        alb_security_group = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup",
            vpc=vpc,
            description="ALB security group for public HTTP traffic",
            allow_all_outbound=True,
        )
        alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "Allow inbound HTTP",
        )

        service_security_group = ec2.SecurityGroup(
            self,
            "ServiceSecurityGroup",
            vpc=vpc,
            description="Fargate service security group for api container",
            allow_all_outbound=True,
        )
        service_security_group.add_ingress_rule(
            alb_security_group,
            ec2.Port.tcp(8080),
            "Allow ALB to reach api",
        )

        service = ecs.FargateService(
            self,
            "BackendService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=desired_count,
            security_groups=[service_security_group],
            assign_public_ip=False,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            health_check_grace_period=Duration.seconds(60),
        )

        load_balancer = elbv2.ApplicationLoadBalancer(
            self,
            "BackendAlb",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_security_group,
        )
        listener = load_balancer.add_listener(
            "HttpListener",
            port=80,
            open=True,
        )
        listener.add_targets(
            "ApiFleet",
            port=8080,
            targets=[
                service.load_balancer_target(
                    container_name="api",
                    container_port=8080,
                )
            ],
            health_check=elbv2.HealthCheck(
                path="/health",
                healthy_http_codes="200",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3,
            ),
        )

        CfnOutput(self, "AlbDnsName", value=load_balancer.load_balancer_dns_name)
        CfnOutput(
            self,
            "AlbUrl",
            value=f"http://{load_balancer.load_balancer_dns_name}",
        )
        CfnOutput(self, "EcrRepositoryName", value=repository.repository_name)
        CfnOutput(self, "EcrRepositoryUri", value=repository.repository_uri)
        CfnOutput(self, "EcsClusterName", value=cluster.cluster_name)
        CfnOutput(self, "EcsServiceName", value=service.service_name)
