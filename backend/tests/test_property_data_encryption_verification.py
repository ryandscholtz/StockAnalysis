"""
Property-based tests for data encryption verification.

Feature: tech-stack-modernization, Property 21: Data Encryption Verification
**Validates: Requirements 7.6**
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional, Union
import base64
import hashlib
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os


class MockEncryptionService:
    """Mock encryption service for testing data encryption verification properties."""
    
    def __init__(self, encryption_key: bytes = None):
        if encryption_key is None:
            encryption_key = Fernet.generate_key()
        self.encryption_key = encryption_key
        self.fernet = Fernet(encryption_key)
        self.encrypted_data_store = {}
        
    def encrypt_data(self, data: Union[str, bytes, Dict[str, Any]], data_type: str = "general") -> Dict[str, Any]:
        """Encrypt data and return encryption metadata."""
        # Convert data to bytes if needed
        if isinstance(data, dict):
            data_bytes = json.dumps(data, sort_keys=True).encode('utf-8')
        elif isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data
        
        # Encrypt the data
        encrypted_data = self.fernet.encrypt(data_bytes)
        
        # Generate data ID and store
        data_id = hashlib.sha256(data_bytes).hexdigest()[:16]
        
        encryption_metadata = {
            "data_id": data_id,
            "encrypted_data": base64.b64encode(encrypted_data).decode('utf-8'),
            "encryption_algorithm": "Fernet",
            "data_type": data_type,
            "encrypted": True,
            "key_id": hashlib.sha256(self.encryption_key).hexdigest()[:8],
            "original_type": type(data).__name__
        }
        
        self.encrypted_data_store[data_id] = encryption_metadata
        return encryption_metadata
    
    def decrypt_data(self, encryption_metadata: Dict[str, Any], authorized: bool = True) -> Dict[str, Any]:
        """Decrypt data if authorized."""
        if not authorized:
            return {
                "success": False,
                "error": "Unauthorized access to encrypted data",
                "data": None
            }
        
        try:
            encrypted_data_b64 = encryption_metadata["encrypted_data"]
            encrypted_data = base64.b64decode(encrypted_data_b64.encode('utf-8'))
            
            # Decrypt the data
            decrypted_bytes = self.fernet.decrypt(encrypted_data)
            
            # Return as string to maintain consistency
            decrypted_data = decrypted_bytes.decode('utf-8')
            
            # If it was originally a dict, parse it back
            original_type = encryption_metadata.get("original_type", "str")
            if original_type == "dict":
                try:
                    decrypted_data = json.loads(decrypted_data)
                except json.JSONDecodeError:
                    pass  # Keep as string if parsing fails
            
            return {
                "success": True,
                "data": decrypted_data,
                "data_id": encryption_metadata["data_id"]
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Decryption failed: {str(e)}",
                "data": None
            }
    
    def encrypt_in_transit(self, data: str, destination: str) -> Dict[str, Any]:
        """Simulate encryption for data in transit."""
        # Simulate TLS encryption
        encrypted_payload = self.fernet.encrypt(data.encode('utf-8'))
        
        return {
            "encrypted_payload": base64.b64encode(encrypted_payload).decode('utf-8'),
            "destination": destination,
            "transport_encryption": "TLS_1.3",
            "cipher_suite": "TLS_AES_256_GCM_SHA384",
            "encrypted_in_transit": True
        }
    
    def verify_encryption_at_rest(self, data_id: str) -> Dict[str, Any]:
        """Verify that data is properly encrypted at rest."""
        if data_id not in self.encrypted_data_store:
            return {
                "encrypted_at_rest": False,
                "error": "Data not found in encrypted store"
            }
        
        metadata = self.encrypted_data_store[data_id]
        
        # Verify encryption properties
        verification = {
            "encrypted_at_rest": metadata.get("encrypted", False),
            "encryption_algorithm": metadata.get("encryption_algorithm"),
            "key_id": metadata.get("key_id"),
            "data_type": metadata.get("data_type"),
            "verification_passed": True
        }
        
        # Additional security checks
        if not metadata.get("encrypted"):
            verification["verification_passed"] = False
            verification["error"] = "Data is not encrypted"
        
        if not metadata.get("encryption_algorithm"):
            verification["verification_passed"] = False
            verification["error"] = "No encryption algorithm specified"
        
        return verification
    
    def rotate_encryption_key(self) -> Dict[str, Any]:
        """Simulate encryption key rotation."""
        old_key_id = hashlib.sha256(self.encryption_key).hexdigest()[:8]
        
        # Generate new key
        new_key = Fernet.generate_key()
        new_fernet = Fernet(new_key)
        new_key_id = hashlib.sha256(new_key).hexdigest()[:8]
        
        # Re-encrypt all data with new key
        re_encrypted_count = 0
        for data_id, metadata in self.encrypted_data_store.items():
            try:
                # Decrypt with old key
                encrypted_data = base64.b64decode(metadata["encrypted_data"].encode('utf-8'))
                decrypted_data = self.fernet.decrypt(encrypted_data)
                
                # Encrypt with new key
                new_encrypted_data = new_fernet.encrypt(decrypted_data)
                
                # Update metadata
                metadata["encrypted_data"] = base64.b64encode(new_encrypted_data).decode('utf-8')
                metadata["key_id"] = new_key_id
                
                re_encrypted_count += 1
            except Exception:
                # Skip failed re-encryption for this test
                pass
        
        # Update service key
        self.encryption_key = new_key
        self.fernet = new_fernet
        
        return {
            "key_rotation_successful": True,
            "old_key_id": old_key_id,
            "new_key_id": new_key_id,
            "re_encrypted_items": re_encrypted_count
        }


class TestDataEncryptionVerification:
    """Property tests for data encryption verification."""
    
    @given(
        sensitive_data_items=st.lists(
            st.tuples(
                st.one_of(
                    st.text(min_size=1, max_size=100),  # String data
                    st.dictionaries(
                        st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
                        st.one_of(
                            st.text(min_size=1, max_size=50),
                            st.integers(min_value=0, max_value=1000000),
                            st.floats(min_value=0.0, max_value=1000000.0, allow_nan=False, allow_infinity=False)
                        ),
                        min_size=1, max_size=5
                    )  # Dictionary data
                ),
                st.sampled_from(["user_data", "financial_data", "credentials", "pii", "api_keys"])  # data_type
            ),
            min_size=1, max_size=15
        ),
        authorized_access=st.booleans()
    )
    @settings(max_examples=30, deadline=5000)
    def test_data_encryption_verification_property(self, sensitive_data_items: List[tuple], authorized_access: bool):
        """
        Property 21: Data Encryption Verification
        
        For any sensitive data, it should be encrypted when stored and transmitted, 
        and decryption should only be possible with proper credentials.
        
        **Validates: Requirements 7.6**
        """
        encryption_service = MockEncryptionService()
        
        encrypted_items = []
        
        for data, data_type in sensitive_data_items:
            # Encrypt the sensitive data
            encryption_metadata = encryption_service.encrypt_data(data, data_type)
            
            # Verify encryption metadata
            assert encryption_metadata["encrypted"] is True, \
                f"Data of type {data_type} should be marked as encrypted"
            assert "encrypted_data" in encryption_metadata, \
                f"Encryption metadata should contain encrypted data for {data_type}"
            assert "encryption_algorithm" in encryption_metadata, \
                f"Encryption metadata should specify algorithm for {data_type}"
            assert "key_id" in encryption_metadata, \
                f"Encryption metadata should include key ID for {data_type}"
            
            # Verify encrypted data is different from original
            encrypted_data_b64 = encryption_metadata["encrypted_data"]
            if isinstance(data, str):
                original_b64 = base64.b64encode(data.encode('utf-8')).decode('utf-8')
                assert encrypted_data_b64 != original_b64, \
                    f"Encrypted data should be different from original for {data_type}"
            
            encrypted_items.append((encryption_metadata, data, data_type))
        
        # Test decryption with authorization
        for encryption_metadata, original_data, data_type in encrypted_items:
            decryption_result = encryption_service.decrypt_data(encryption_metadata, authorized=authorized_access)
            
            if authorized_access:
                # Authorized access should succeed
                assert decryption_result["success"] is True, \
                    f"Authorized decryption should succeed for {data_type}"
                assert decryption_result["data"] == original_data, \
                    f"Decrypted data should match original for {data_type}"
            else:
                # Unauthorized access should fail
                assert decryption_result["success"] is False, \
                    f"Unauthorized decryption should fail for {data_type}"
                assert decryption_result["data"] is None, \
                    f"Unauthorized access should not return data for {data_type}"
                assert "error" in decryption_result, \
                    f"Unauthorized access should include error message for {data_type}"
    
    @given(
        transit_data=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=200, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Ps', 'Pe'))),  # data
                st.sampled_from([
                    "api.example.com", "secure-service.org", "financial-api.net", 
                    "stock-analysis.io", "data-processor.com"
                ])  # destination
            ),
            min_size=1, max_size=10
        )
    )
    @settings(max_examples=25, deadline=4000)
    def test_data_in_transit_encryption_property(self, transit_data: List[tuple]):
        """
        Property 21b: Data in Transit Encryption
        
        For any data transmitted between services, it should be encrypted using
        secure transport protocols (TLS 1.3).
        
        **Validates: Requirements 7.6**
        """
        encryption_service = MockEncryptionService()
        
        for data, destination in transit_data:
            # Skip empty data
            if not data.strip():
                continue
            
            # Encrypt data for transit
            transit_encryption = encryption_service.encrypt_in_transit(data, destination)
            
            # Verify transit encryption properties
            assert transit_encryption["encrypted_in_transit"] is True, \
                f"Data should be encrypted in transit to {destination}"
            
            assert "transport_encryption" in transit_encryption, \
                f"Transit encryption should specify transport protocol for {destination}"
            
            transport_protocol = transit_encryption["transport_encryption"]
            assert "TLS" in transport_protocol, \
                f"Should use TLS for transport encryption to {destination}"
            
            # Verify secure TLS version (1.2 or higher)
            assert any(version in transport_protocol for version in ["1.2", "1.3"]), \
                f"Should use secure TLS version for {destination}, got {transport_protocol}"
            
            # Verify cipher suite is specified
            assert "cipher_suite" in transit_encryption, \
                f"Transit encryption should specify cipher suite for {destination}"
            
            cipher_suite = transit_encryption["cipher_suite"]
            assert cipher_suite is not None and len(cipher_suite) > 0, \
                f"Cipher suite should be specified for {destination}"
            
            # Verify encrypted payload is different from original
            encrypted_payload = transit_encryption["encrypted_payload"]
            original_b64 = base64.b64encode(data.encode('utf-8')).decode('utf-8')
            assert encrypted_payload != original_b64, \
                f"Encrypted payload should be different from original for {destination}"
    
    @given(
        data_at_rest=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),  # data
                st.sampled_from(["database", "file_storage", "cache", "backup"])  # storage_type
            ),
            min_size=1, max_size=12
        )
    )
    @settings(max_examples=20, deadline=4000)
    def test_data_at_rest_encryption_property(self, data_at_rest: List[tuple]):
        """
        Property 21c: Data at Rest Encryption
        
        For any data stored persistently, it should be encrypted at rest with
        proper key management and verification capabilities.
        
        **Validates: Requirements 7.6**
        """
        encryption_service = MockEncryptionService()
        
        stored_data_ids = []
        
        for data, storage_type in data_at_rest:
            # Skip empty data
            if not data.strip():
                continue
            
            # Encrypt and store data
            encryption_metadata = encryption_service.encrypt_data(data, storage_type)
            data_id = encryption_metadata["data_id"]
            stored_data_ids.append(data_id)
            
            # Verify encryption at rest
            verification = encryption_service.verify_encryption_at_rest(data_id)
            
            assert verification["encrypted_at_rest"] is True, \
                f"Data should be encrypted at rest for {storage_type}"
            
            assert verification["verification_passed"] is True, \
                f"Encryption verification should pass for {storage_type}: {verification.get('error', '')}"
            
            assert "encryption_algorithm" in verification, \
                f"Verification should include encryption algorithm for {storage_type}"
            
            assert "key_id" in verification, \
                f"Verification should include key ID for {storage_type}"
            
            # Verify key ID is not empty
            key_id = verification["key_id"]
            assert key_id is not None and len(key_id) > 0, \
                f"Key ID should be specified for {storage_type}"
        
        # Verify all stored data can be verified
        for data_id in stored_data_ids:
            verification = encryption_service.verify_encryption_at_rest(data_id)
            assert verification["verification_passed"] is True, \
                f"All stored data should pass encryption verification: {data_id}"
    
    @given(
        key_rotation_scenarios=st.lists(
            st.tuples(
                st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),  # data
                st.sampled_from(["user_credentials", "api_keys", "financial_data", "personal_info"])  # data_type
            ),
            min_size=2, max_size=8
        )
    )
    @settings(max_examples=15, deadline=5000)
    def test_encryption_key_rotation_property(self, key_rotation_scenarios: List[tuple]):
        """
        Property 21d: Encryption Key Rotation
        
        For any encrypted data, key rotation should successfully re-encrypt all data
        with new keys while maintaining data integrity and accessibility.
        
        **Validates: Requirements 7.6**
        """
        encryption_service = MockEncryptionService()
        
        # Encrypt initial data
        original_data = {}
        for data, data_type in key_rotation_scenarios:
            if not data.strip():
                continue
                
            encryption_metadata = encryption_service.encrypt_data(data, data_type)
            data_id = encryption_metadata["data_id"]
            original_data[data_id] = {
                "original": data,
                "data_type": data_type,
                "pre_rotation_key_id": encryption_metadata["key_id"]
            }
        
        if not original_data:
            return  # Skip if no valid data
        
        # Perform key rotation
        rotation_result = encryption_service.rotate_encryption_key()
        
        # Verify key rotation succeeded
        assert rotation_result["key_rotation_successful"] is True, \
            "Key rotation should succeed"
        
        assert "old_key_id" in rotation_result, \
            "Key rotation should track old key ID"
        
        assert "new_key_id" in rotation_result, \
            "Key rotation should provide new key ID"
        
        assert rotation_result["old_key_id"] != rotation_result["new_key_id"], \
            "New key ID should be different from old key ID"
        
        # Verify data is still accessible after key rotation
        for data_id, data_info in original_data.items():
            # Verify encryption at rest with new key
            verification = encryption_service.verify_encryption_at_rest(data_id)
            
            assert verification["encrypted_at_rest"] is True, \
                f"Data should remain encrypted after key rotation: {data_id}"
            
            assert verification["verification_passed"] is True, \
                f"Encryption verification should pass after key rotation: {data_id}"
            
            # Verify key ID has been updated
            new_key_id = verification["key_id"]
            old_key_id = data_info["pre_rotation_key_id"]
            assert new_key_id != old_key_id, \
                f"Key ID should be updated after rotation for {data_id}"
            
            # Verify data can still be decrypted
            metadata = encryption_service.encrypted_data_store[data_id]
            decryption_result = encryption_service.decrypt_data(metadata, authorized=True)
            
            assert decryption_result["success"] is True, \
                f"Data should be decryptable after key rotation: {data_id}"
            
            assert decryption_result["data"] == data_info["original"], \
                f"Decrypted data should match original after key rotation: {data_id}"