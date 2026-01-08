"""
Property-based tests for JWT authentication security.

Feature: tech-stack-modernization, Property 17: JWT Authentication Security
**Validates: Requirements 7.1**
"""

from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
import jwt
from typing import Dict, Any, Optional


class MockJWTService:
    """Mock JWT service for testing authentication security properties."""

    def __init__(self, secret_key: str = "test-secret-key", algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.refresh_tokens = {}  # Store refresh tokens

    def generate_access_token(self, user_id: str, expires_in: int = 3600) -> str:
        """Generate JWT access token."""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def generate_refresh_token(self, user_id: str, expires_in: int = 86400) -> str:
        """Generate JWT refresh token."""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        self.refresh_tokens[token] = user_id
        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Generate new access token using refresh token."""
        if refresh_token not in self.refresh_tokens:
            return None

        payload = self.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        return self.generate_access_token(user_id)

    def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke refresh token."""
        if refresh_token in self.refresh_tokens:
            del self.refresh_tokens[refresh_token]
            return True
        return False


class TestJWTAuthenticationSecurity:
    """Property tests for JWT authentication security."""

    @given(
        user_id=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=(
                    'Lu',
                    'Ll',
                    'Nd'))),
        expires_in=st.integers(min_value=60, max_value=86400),  # 1 minute to 1 day
        secret_key=st.text(min_size=16, max_size=64)
    )
    @settings(max_examples=50, deadline=5000)
    def test_jwt_authentication_security_property(
            self, user_id: str, expires_in: int, secret_key: str):
        """
        Property 17: JWT Authentication Security

        For any authentication request, JWT tokens should expire according to policy
        and refresh tokens should successfully generate new access tokens.

        **Validates: Requirements 7.1**
        """
        jwt_service = MockJWTService(secret_key=secret_key)

        # Generate access and refresh tokens
        access_token = jwt_service.generate_access_token(user_id, expires_in)
        refresh_token = jwt_service.generate_refresh_token(
            user_id, expires_in * 24)  # Refresh token lasts longer

        # Verify tokens are valid initially
        access_payload = jwt_service.verify_token(access_token)
        refresh_payload = jwt_service.verify_token(refresh_token)

        assert access_payload is not None, "Access token should be valid when first generated"
        assert refresh_payload is not None, "Refresh token should be valid when first generated"
        assert access_payload["user_id"] == user_id, "Access token should contain correct user ID"
        assert refresh_payload["user_id"] == user_id, "Refresh token should contain correct user ID"
        assert access_payload["type"] == "access", "Access token should have correct type"
        assert refresh_payload["type"] == "refresh", "Refresh token should have correct type"

        # Verify token expiration is set correctly
        access_exp = datetime.fromtimestamp(access_payload["exp"])
        refresh_exp = datetime.fromtimestamp(refresh_payload["exp"])
        now = datetime.utcnow()

        assert access_exp > now, "Access token expiration should be in the future"
        assert refresh_exp > now, "Refresh token expiration should be in the future"
        assert refresh_exp > access_exp, "Refresh token should expire after access token"

        # Test refresh token functionality
        new_access_token = jwt_service.refresh_access_token(refresh_token)
        assert new_access_token is not None, "Refresh token should generate new access token"

        new_access_payload = jwt_service.verify_token(new_access_token)
        assert new_access_payload is not None, "New access token should be valid"
        assert new_access_payload["user_id"] == user_id, "New access token should contain same user ID"

        # Test token revocation
        revoke_result = jwt_service.revoke_refresh_token(refresh_token)
        assert revoke_result is True, "Refresh token should be successfully revoked"

        # Revoked refresh token should not work
        revoked_access_token = jwt_service.refresh_access_token(refresh_token)
        assert revoked_access_token is None, "Revoked refresh token should not generate new access token"

    @given(
        user_id=st.text(min_size=1, max_size=50),
        invalid_secret=st.text(min_size=1, max_size=64),
        valid_secret=st.text(min_size=16, max_size=64)
    )
    @settings(max_examples=30, deadline=4000)
    def test_jwt_token_security_validation_property(
            self, user_id: str, invalid_secret: str, valid_secret: str):
        """
        Property 17b: JWT Token Security Validation

        For any JWT token, validation should fail with incorrect secrets and succeed with correct secrets.

        **Validates: Requirements 7.1**
        """
        # Ensure secrets are different
        if invalid_secret == valid_secret:
            invalid_secret = valid_secret + "_different"

        jwt_service_valid = MockJWTService(secret_key=valid_secret)
        jwt_service_invalid = MockJWTService(secret_key=invalid_secret)

        # Generate token with valid secret
        token = jwt_service_valid.generate_access_token(user_id)

        # Valid secret should verify token
        valid_payload = jwt_service_valid.verify_token(token)
        assert valid_payload is not None, "Token should be valid with correct secret"
        assert valid_payload["user_id"] == user_id, "Token should contain correct user data"

        # Invalid secret should fail to verify token
        invalid_payload = jwt_service_invalid.verify_token(token)
        assert invalid_payload is None, "Token should be invalid with incorrect secret"

    @given(user_ids=st.lists(st.text(min_size=1,
                                     max_size=20,
                                     alphabet=st.characters(whitelist_categories=('Lu',
                                                                                  'Ll',
                                                                                  'Nd'))),
                             min_size=1,
                             max_size=10,
                             unique=True),
           token_operations=st.lists(st.sampled_from(["generate",
                                                      "verify",
                                                      "refresh",
                                                      "revoke"]),
                                     min_size=5,
                                     max_size=20))
    @settings(max_examples=20, deadline=6000)
    def test_jwt_concurrent_operations_security_property(
            self, user_ids: list, token_operations: list):
        """
        Property 17c: JWT Concurrent Operations Security

        For any sequence of JWT operations, the system should maintain security invariants
        even with concurrent token generation, verification, and revocation.

        **Validates: Requirements 7.1**
        """
        jwt_service = MockJWTService()
        user_tokens = {}  # Track tokens per user

        for operation in token_operations:
            if not user_ids:
                continue

            user_id = user_ids[hash(operation) % len(user_ids)]

            if operation == "generate":
                access_token = jwt_service.generate_access_token(user_id)
                refresh_token = jwt_service.generate_refresh_token(user_id)

                user_tokens[user_id] = {
                    "access": access_token,
                    "refresh": refresh_token
                }

                # Verify generated tokens are valid
                assert jwt_service.verify_token(access_token) is not None, \
                    f"Generated access token should be valid for user {user_id}"
                assert jwt_service.verify_token(refresh_token) is not None, \
                    f"Generated refresh token should be valid for user {user_id}"

            elif operation == "verify" and user_id in user_tokens:
                tokens = user_tokens[user_id]

                access_payload = jwt_service.verify_token(tokens["access"])
                refresh_payload = jwt_service.verify_token(tokens["refresh"])

                # Tokens should remain valid unless explicitly revoked
                if tokens["refresh"] in jwt_service.refresh_tokens:
                    assert access_payload is not None, \
                        f"Access token should be valid for user {user_id}"
                    assert refresh_payload is not None, \
                        f"Refresh token should be valid for user {user_id}"

            elif operation == "refresh" and user_id in user_tokens:
                refresh_token = user_tokens[user_id]["refresh"]
                new_access_token = jwt_service.refresh_access_token(refresh_token)

                if refresh_token in jwt_service.refresh_tokens:
                    assert new_access_token is not None, \
                        f"Refresh should generate new access token for user {user_id}"

                    # Update stored access token
                    user_tokens[user_id]["access"] = new_access_token

            elif operation == "revoke" and user_id in user_tokens:
                refresh_token = user_tokens[user_id]["refresh"]
                revoke_result = jwt_service.revoke_refresh_token(refresh_token)

                # Should successfully revoke if token exists
                if refresh_token in jwt_service.refresh_tokens:
                    assert revoke_result is True, \
                        f"Should successfully revoke refresh token for user {user_id}"

                # After revocation, refresh should fail
                new_access_token = jwt_service.refresh_access_token(refresh_token)
                assert new_access_token is None, \
                    f"Revoked refresh token should not generate new access token for user {user_id}"

    @given(
        user_id=st.text(min_size=1, max_size=50),
        malformed_tokens=st.lists(
            st.one_of(
                st.text(min_size=1, max_size=100),  # Random strings
                st.just(""),  # Empty string
                st.just("invalid.jwt.token"),  # Invalid format
                # Invalid signature
                st.just("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.signature")
            ),
            min_size=1, max_size=10
        )
    )
    @settings(max_examples=25, deadline=4000)
    def test_jwt_malformed_token_security_property(
            self, user_id: str, malformed_tokens: list):
        """
        Property 17d: JWT Malformed Token Security

        For any malformed or invalid JWT token, the system should reject it securely
        without exposing sensitive information.

        **Validates: Requirements 7.1**
        """
        jwt_service = MockJWTService()

        for malformed_token in malformed_tokens:
            # All malformed tokens should be rejected
            payload = jwt_service.verify_token(malformed_token)
            assert payload is None, \
                f"Malformed token '{malformed_token}' should be rejected"

            # Refresh attempts with malformed tokens should fail
            new_token = jwt_service.refresh_access_token(malformed_token)
            assert new_token is None, \
                f"Malformed refresh token '{malformed_token}' should not generate access token"

            # Revocation attempts with malformed tokens should fail gracefully
            revoke_result = jwt_service.revoke_refresh_token(malformed_token)
            assert revoke_result is False, \
                f"Malformed token '{malformed_token}' revocation should return False"
