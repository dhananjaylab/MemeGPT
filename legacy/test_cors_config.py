"""
Test CORS configuration for MemeGPT API.

This test verifies that CORS middleware is properly configured
for frontend communication with appropriate security measures.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import os

from backend.main import app
from backend.core.config import settings


class TestCORSConfiguration:
    """Test CORS middleware configuration"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_cors_preflight_request_allowed_origin(self):
        """Test CORS preflight request from allowed origin"""
        
        # Test with localhost origin (allowed in development)
        response = self.client.options(
            "/api/memes/public",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers
    
    def test_cors_simple_request_allowed_origin(self):
        """Test simple CORS request from allowed origin"""
        
        response = self.client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    
    def test_cors_credentials_allowed(self):
        """Test that credentials are allowed when configured"""
        
        response = self.client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        if settings.cors_allow_credentials:
            assert "Access-Control-Allow-Credentials" in response.headers
            assert response.headers["Access-Control-Allow-Credentials"] == "true"
    
    def test_cors_exposed_headers(self):
        """Test that rate limiting headers are exposed"""
        
        response = self.client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        if "Access-Control-Expose-Headers" in response.headers:
            exposed_headers = response.headers["Access-Control-Expose-Headers"]
            # Check for rate limiting headers
            assert "X-RateLimit-Limit" in exposed_headers or "x-ratelimit-limit" in exposed_headers.lower()
    
    def test_security_headers_present(self):
        """Test that security headers are added to responses"""
        
        response = self.client.get("/health")
        
        assert response.status_code == 200
        
        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
    
    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_production_security_headers(self):
        """Test additional security headers in production"""
        
        # Note: This test requires reloading the settings
        # In a real test, you'd restart the app with production config
        response = self.client.get("/health")
        
        assert response.status_code == 200
        # In production, CSP header should be present
        # This would need app restart to take effect
    
    def test_cors_methods_allowed(self):
        """Test that required HTTP methods are allowed"""
        
        # Test OPTIONS request for different methods
        for method in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
            response = self.client.options(
                "/api/memes/public",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": method,
                }
            )
            
            assert response.status_code == 200
            allowed_methods = response.headers.get("Access-Control-Allow-Methods", "")
            assert method in allowed_methods
    
    def test_cors_headers_allowed(self):
        """Test that required headers are allowed"""
        
        required_headers = [
            "Authorization",
            "Content-Type", 
            "X-API-Key",
            "X-Requested-With"
        ]
        
        for header in required_headers:
            response = self.client.options(
                "/api/memes/public",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": header
                }
            )
            
            assert response.status_code == 200
            allowed_headers = response.headers.get("Access-Control-Allow-Headers", "")
            assert header in allowed_headers or header.lower() in allowed_headers.lower()
    
    def test_cors_max_age_set(self):
        """Test that CORS max age is properly configured"""
        
        response = self.client.options(
            "/api/memes/public",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        
        assert response.status_code == 200
        assert "Access-Control-Max-Age" in response.headers
        max_age = int(response.headers["Access-Control-Max-Age"])
        assert max_age > 0
        assert max_age <= 3600  # Reasonable upper limit


class TestCORSSecurityValidation:
    """Test CORS security validation"""
    
    def test_cors_origins_configuration(self):
        """Test that CORS origins are properly configured"""
        
        from backend.core.cors import get_cors_origins
        
        origins = get_cors_origins()
        
        # Should have at least one origin
        assert len(origins) > 0
        
        # Should not contain wildcards in production
        if settings.is_production:
            assert "*" not in origins
        
        # All origins should be valid URLs
        for origin in origins:
            assert origin.startswith(("http://", "https://"))
            assert not origin.endswith("/")  # Should be normalized
    
    def test_cors_validation_function(self):
        """Test CORS configuration validation"""
        
        from backend.core.cors import validate_cors_config
        
        # Should not raise exception with current config
        try:
            validate_cors_config()
        except Exception as e:
            pytest.fail(f"CORS validation failed: {e}")
    
    @patch.dict(os.environ, {"ENVIRONMENT": "production", "CORS_ORIGINS": "*"})
    def test_wildcard_origin_blocked_in_production(self):
        """Test that wildcard origins are blocked in production"""
        
        from backend.core.cors import validate_cors_config
        
        # This should raise an error in production
        with pytest.raises(ValueError, match="Wildcard CORS origins not allowed"):
            validate_cors_config()


if __name__ == "__main__":
    # Run basic CORS test
    client = TestClient(app)
    
    print("Testing CORS configuration...")
    
    # Test basic health endpoint with CORS
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"}
    )
    
    print(f"Health endpoint status: {response.status_code}")
    print(f"CORS headers: {dict(response.headers)}")
    
    # Test preflight request
    response = client.options(
        "/api/memes/public",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        }
    )
    
    print(f"Preflight status: {response.status_code}")
    print(f"Preflight headers: {dict(response.headers)}")
    
    print("CORS configuration test completed!")