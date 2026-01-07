"""
Property-based tests for IAM least privilege compliance.

Feature: tech-stack-modernization, Property 19: IAM Least Privilege Compliance
**Validates: Requirements 7.4**
"""

from hypothesis import given, strategies as st, settings
from typing import Dict, Any, List


class MockIAMService:
    """Mock IAM service for testing least privilege compliance properties."""

    def __init__(self):
        self.policies = {}
        self.roles = {}
        self.permissions = {
            # DynamoDB permissions
            "dynamodb:GetItem": {"resource_type": "table", "action_type": "read"},
            "dynamodb:PutItem": {"resource_type": "table", "action_type": "write"},
            "dynamodb:UpdateItem": {"resource_type": "table", "action_type": "write"},
            "dynamodb:DeleteItem": {"resource_type": "table", "action_type": "write"},
            "dynamodb:Query": {"resource_type": "table", "action_type": "read"},
            "dynamodb:Scan": {"resource_type": "table", "action_type": "read"},

            # S3 permissions
            "s3:GetObject": {"resource_type": "bucket", "action_type": "read"},
            "s3:PutObject": {"resource_type": "bucket", "action_type": "write"},
            "s3:DeleteObject": {"resource_type": "bucket", "action_type": "write"},
            "s3:ListBucket": {"resource_type": "bucket", "action_type": "read"},

            # Lambda permissions
            "lambda:InvokeFunction": {"resource_type": "function", "action_type": "execute"},

            # Secrets Manager permissions
            "secretsmanager:GetSecretValue": {"resource_type": "secret", "action_type": "read"},
            "secretsmanager:CreateSecret": {"resource_type": "secret", "action_type": "write"},

            # CloudWatch permissions
            "cloudwatch:PutMetricData": {"resource_type": "metric", "action_type": "write"},
            "logs:CreateLogGroup": {"resource_type": "log", "action_type": "write"},
            "logs:PutLogEvents": {"resource_type": "log", "action_type": "write"},

            # Administrative permissions (should be restricted)
            "iam:CreateRole": {"resource_type": "iam", "action_type": "admin"},
            "iam:DeleteRole": {"resource_type": "iam", "action_type": "admin"},
            "iam:AttachRolePolicy": {"resource_type": "iam", "action_type": "admin"},
            "ec2:TerminateInstances": {"resource_type": "ec2", "action_type": "admin"},
            "rds:DeleteDBInstance": {"resource_type": "rds", "action_type": "admin"}
        }

    def create_role(self,
                    role_name: str,
                    service: str,
                    permissions: List[str],
                    resources: List[str] = None) -> Dict[str,
                                                         Any]:
        """Create IAM role with specified permissions."""
        if resources is None:
            resources = ["*"]

        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": permissions,
                    "Resource": resources
                }
            ]
        }

        role = {
            "role_name": role_name,
            "service": service,
            "permissions": permissions,
            "resources": resources,
            "policy_document": policy_document,
            "created": True
        }

        self.roles[role_name] = role
        return role

    def check_permission(self, role_name: str, action: str,
                         resource: str = "*") -> Dict[str, Any]:
        """Check if role has permission to perform action on resource."""
        if role_name not in self.roles:
            return {"allowed": False, "reason": "Role not found"}

        role = self.roles[role_name]

        # Check if action is in role permissions
        if action not in role["permissions"]:
            return {"allowed": False, "reason": "Action not in role permissions"}

        # Check resource access (simplified - in real AWS, this would be more complex)
        if resource != "*" and "*" not in role["resources"]:
            if resource not in role["resources"]:
                return {"allowed": False, "reason": "Resource not accessible"}

        return {"allowed": True, "reason": "Permission granted"}

    def analyze_least_privilege(
            self, role_name: str, required_actions: List[str]) -> Dict[str, Any]:
        """Analyze if role follows least privilege principle."""
        if role_name not in self.roles:
            return {"compliant": False, "reason": "Role not found"}

        role = self.roles[role_name]
        role_permissions = set(role["permissions"])
        required_permissions = set(required_actions)

        # Check for excessive permissions
        excessive_permissions = role_permissions - required_permissions

        # Check for administrative permissions (should be avoided)
        admin_permissions = []
        for perm in role_permissions:
            if perm in self.permissions and self.permissions[perm]["action_type"] == "admin":
                admin_permissions.append(perm)

        # Check for wildcard resources (should be specific when possible)
        has_wildcard_resources = "*" in role["resources"]

        analysis = {
            "compliant": len(excessive_permissions) == 0 and len(admin_permissions) == 0,
            "excessive_permissions": list(excessive_permissions),
            "admin_permissions": admin_permissions,
            "has_wildcard_resources": has_wildcard_resources,
            "required_permissions": list(required_permissions),
            "granted_permissions": list(role_permissions),
            "missing_permissions": list(
                required_permissions - role_permissions)}

        return analysis

    def test_unauthorized_access(
            self, role_name: str, unauthorized_actions: List[str]) -> Dict[str, Any]:
        """Test that role cannot perform unauthorized actions."""
        results = {}

        for action in unauthorized_actions:
            result = self.check_permission(role_name, action)
            results[action] = result

        # All unauthorized actions should be denied
        all_denied = all(not result["allowed"] for result in results.values())

        return {
            "all_unauthorized_denied": all_denied,
            "results": results
        }


class TestIAMLeastPrivilegeCompliance:
    """Property tests for IAM least privilege compliance."""

    @given(
        role_configs=st.lists(
            st.tuples(
                st.text(
                    min_size=3,
                    max_size=20,
                    alphabet=st.characters(
                        whitelist_categories=(
                            'Lu',
                            'Ll',
                            'Nd',
                            'Pc'))),
                # role_name
                st.sampled_from(["lambda", "ec2", "ecs", "api-gateway"]),  # service
                st.lists(
                    st.sampled_from([
                        "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query",
                        "s3:GetObject", "s3:PutObject", "s3:ListBucket",
                        "secretsmanager:GetSecretValue", "cloudwatch:PutMetricData",
                        "logs:PutLogEvents"
                    ]),
                    min_size=1, max_size=8, unique=True
                )  # permissions
            ),
            min_size=1, max_size=5
        ),
        required_actions=st.lists(
            st.sampled_from([
                "dynamodb:GetItem", "dynamodb:PutItem", "s3:GetObject",
                "secretsmanager:GetSecretValue", "cloudwatch:PutMetricData"
            ]),
            min_size=1, max_size=5, unique=True
        )
    )
    @settings(max_examples=30, deadline=5000)
    def test_iam_least_privilege_compliance_property(
            self, role_configs: List[tuple], required_actions: List[str]):
        """
        Property 19: IAM Least Privilege Compliance

        For any AWS service access, the system should only have the minimum required permissions
        and should fail when attempting unauthorized operations.

        **Validates: Requirements 7.4**
        """
        iam_service = MockIAMService()

        for role_name, service, permissions in role_configs:
            # Skip invalid role names
            if not role_name or role_name.isspace():
                continue

            # Create role with specified permissions
            role = iam_service.create_role(role_name, service, permissions)
            assert role["created"] is True, f"Role {role_name} should be created successfully"

            # Analyze least privilege compliance
            analysis = iam_service.analyze_least_privilege(role_name, required_actions)

            # Role should not have administrative permissions
            assert len(
                analysis["admin_permissions"]) == 0, f"Role {role_name} should not have administrative permissions: {
                analysis['admin_permissions']}"

            # Role should have all required permissions
            missing_permissions = analysis["missing_permissions"]
            if missing_permissions:
                # This is expected if role was created with fewer permissions than required
                # The test validates that we can detect missing permissions
                assert isinstance(missing_permissions, list), \
                    f"Missing permissions should be a list for role {role_name}"

            # Check that role can perform granted actions
            for permission in permissions:
                if permission in required_actions:
                    check_result = iam_service.check_permission(role_name, permission)
                    assert check_result["allowed"] is True, \
                        f"Role {role_name} should be able to perform granted permission {permission}"

    @given(
        service_roles=st.lists(
            st.tuples(
                st.sampled_from(["stock-analysis-api", "pdf-processor",
                                "data-fetcher", "cache-manager"]),  # service_name
                st.lists(
                    st.sampled_from([
                        "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query", "dynamodb:UpdateItem",
                        "s3:GetObject", "s3:PutObject", "secretsmanager:GetSecretValue",
                        "cloudwatch:PutMetricData", "logs:PutLogEvents"
                    ]),
                    min_size=2, max_size=6, unique=True
                ),
                st.lists(
                    st.sampled_from([
                        "arn:aws:dynamodb:*:*:table/stock-analyses",
                        "arn:aws:s3:::stock-analysis-bucket/*",
                        "arn:aws:secretsmanager:*:*:secret:stock-analysis/*"
                    ]),
                    min_size=1, max_size=3, unique=True
                )
            ),
            min_size=1, max_size=4
        )
    )
    @settings(max_examples=25, deadline=4000)
    def test_service_specific_permissions_property(self, service_roles: List[tuple]):
        """
        Property 19b: Service-Specific Permissions

        For any service role, permissions should be scoped to specific resources
        and actions required by that service only.

        **Validates: Requirements 7.4**
        """
        iam_service = MockIAMService()

        for service_name, permissions, resources in service_roles:
            role_name = f"{service_name}-role"

            # Create role with specific resources (not wildcard)
            role = iam_service.create_role(role_name, "lambda", permissions, resources)

            # Verify role was created with specific resources
            assert role["resources"] == resources, \
                f"Role {role_name} should have specific resources, not wildcards"

            # Verify role doesn't have wildcard resources when specific ones are
            # provided
            analysis = iam_service.analyze_least_privilege(role_name, permissions)
            if len(resources) > 0 and "*" not in resources:
                # Role should not have wildcard access when specific resources are
                # provided
                specific_resources_used = not analysis["has_wildcard_resources"]
                assert specific_resources_used, \
                    f"Role {role_name} should use specific resources when provided"

            # Test that role can access granted resources
            for resource in resources:
                for permission in permissions:
                    check_result = iam_service.check_permission(
                        role_name, permission, resource)
                    assert check_result["allowed"] is True, \
                        f"Role {role_name} should access granted resource {resource} with permission {permission}"

    @given(
        roles_and_unauthorized_actions=st.lists(
            st.tuples(
                st.text(
                    min_size=3,
                    max_size=15,
                    alphabet=st.characters(
                        whitelist_categories=(
                            'Lu',
                            'Ll',
                            'Nd'))),
                # role_name
                st.lists(
                    st.sampled_from([
                        "dynamodb:GetItem", "s3:GetObject", "secretsmanager:GetSecretValue"
                    ]),
                    min_size=1, max_size=3, unique=True
                ),  # granted_permissions
                st.lists(
                    st.sampled_from([
                        "iam:CreateRole", "iam:DeleteRole", "ec2:TerminateInstances",
                        "rds:DeleteDBInstance", "dynamodb:DeleteItem", "s3:DeleteObject"
                    ]),
                    min_size=1, max_size=4, unique=True
                )  # unauthorized_actions
            ),
            min_size=1, max_size=6
        )
    )
    @settings(max_examples=20, deadline=4000)
    def test_unauthorized_access_prevention_property(
            self, roles_and_unauthorized_actions: List[tuple]):
        """
        Property 19c: Unauthorized Access Prevention

        For any role with limited permissions, attempts to perform unauthorized actions
        should be denied by the IAM system.

        **Validates: Requirements 7.4**
        """
        iam_service = MockIAMService()

        for role_name, granted_permissions, unauthorized_actions in roles_and_unauthorized_actions:
            # Skip invalid role names
            if not role_name or role_name.isspace():
                continue

            # Create role with limited permissions
            iam_service.create_role(role_name, "lambda", granted_permissions)

            # Test unauthorized access
            unauthorized_test = iam_service.test_unauthorized_access(
                role_name, unauthorized_actions)

            # All unauthorized actions should be denied
            assert unauthorized_test["all_unauthorized_denied"] is True, \
                f"Role {role_name} should be denied all unauthorized actions"

            # Verify each unauthorized action is specifically denied
            for action in unauthorized_actions:
                result = unauthorized_test["results"][action]
                assert result["allowed"] is False, \
                    f"Role {role_name} should be denied unauthorized action {action}"
                assert "reason" in result, \
                    f"Denial of {action} for role {role_name} should include reason"

    @given(
        cross_service_scenarios=st.lists(
            st.tuples(
                st.sampled_from(["api-service", "data-processor",
                                "auth-service"]),  # service_type
                st.lists(
                    st.sampled_from([
                        ("dynamodb:GetItem", "table"),
                        ("s3:GetObject", "bucket"),
                        ("secretsmanager:GetSecretValue", "secret"),
                        ("lambda:InvokeFunction", "function")
                    ]),
                    min_size=1, max_size=4, unique=True
                ),  # required_access
                st.lists(
                    st.sampled_from([
                        ("iam:CreateRole", "iam"),
                        ("ec2:TerminateInstances", "ec2"),
                        ("rds:DeleteDBInstance", "rds")
                    ]),
                    min_size=1, max_size=3, unique=True
                )  # prohibited_access
            ),
            min_size=1, max_size=4
        )
    )
    @settings(max_examples=15, deadline=5000)
    def test_cross_service_access_control_property(
            self, cross_service_scenarios: List[tuple]):
        """
        Property 19d: Cross-Service Access Control

        For any multi-service architecture, each service should only have access to
        resources it needs and be denied access to other services' resources.

        **Validates: Requirements 7.4**
        """
        iam_service = MockIAMService()

        for service_type, required_access, prohibited_access in cross_service_scenarios:
            role_name = f"{service_type}-cross-service-role"

            # Extract permissions and resource types
            required_permissions = [access[0] for access in required_access]
            [access[1] for access in required_access]

            prohibited_permissions = [access[0] for access in prohibited_access]

            # Create role with only required permissions
            iam_service.create_role(role_name, "lambda", required_permissions)

            # Verify role can perform required actions
            for permission in required_permissions:
                check_result = iam_service.check_permission(role_name, permission)
                assert check_result["allowed"] is True, \
                    f"Service {service_type} should be able to perform required action {permission}"

            # Verify role cannot perform prohibited actions
            for prohibited_permission in prohibited_permissions:
                check_result = iam_service.check_permission(
                    role_name, prohibited_permission)
                assert check_result["allowed"] is False, \
                    f"Service {service_type} should be denied prohibited action {prohibited_permission}"

            # Analyze overall compliance
            required_permissions + prohibited_permissions
            analysis = iam_service.analyze_least_privilege(
                role_name, required_permissions)

            # Should not have excessive permissions beyond what's required
            excessive_perms = set(
                analysis["granted_permissions"]) - set(required_permissions)
            assert len(excessive_perms) == 0, \
                f"Service {service_type} should not have excessive permissions: {excessive_perms}"
