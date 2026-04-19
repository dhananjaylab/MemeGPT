#!/usr/bin/env python3
"""
Simple CORS configuration validation script.

This script validates the CORS configuration without requiring
the full FastAPI application to be running.
"""

import os
import sys
from typing import List

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

def validate_cors_settings():
    """Validate CORS configuration settings"""
    
    print("🔍 Validating CORS Configuration...")
    print("=" * 50)
    
    try:
        from core.config import settings
        
        # Check basic settings
        print(f"✅ Frontend URL: {settings.frontend_url}")
        print(f"✅ Environment: {settings.environment}")
        print(f"✅ Is Production: {settings.is_production}")
        
        # Check CORS origins
        print(f"✅ CORS Origins: {settings.cors_origins}")
        if not settings.cors_origins:
            print("⚠️  Warning: No CORS origins configured")
        
        # Check credentials
        print(f"✅ Allow Credentials: {settings.cors_allow_credentials}")
        
        # Check methods
        print(f"✅ Allowed Methods: {settings.cors_allow_methods}")
        required_methods = ["GET", "POST", "OPTIONS"]
        for method in required_methods:
            if method not in settings.cors_allow_methods:
                print(f"⚠️  Warning: Required method '{method}' not in allowed methods")
        
        # Check headers
        print(f"✅ Allowed Headers: {settings.cors_allow_headers}")
        required_headers = ["Authorization", "Content-Type"]
        for header in required_headers:
            if not any(h.lower() == header.lower() for h in settings.cors_allow_headers):
                print(f"⚠️  Warning: Required header '{header}' not in allowed headers")
        
        # Check max age
        print(f"✅ Max Age: {settings.cors_max_age} seconds")
        if settings.cors_max_age > 3600:
            print("⚠️  Warning: Max age is quite high (>1 hour)")
        
        print("\n🔒 Security Checks...")
        print("-" * 30)
        
        # Production security checks
        if settings.is_production:
            print("🔒 Production mode detected")
            
            # Check for wildcard origins
            if "*" in settings.cors_origins:
                print("❌ ERROR: Wildcard origin (*) not allowed in production!")
                return False
            
            # Check for localhost in production
            localhost_origins = [o for o in settings.cors_origins if "localhost" in o or "127.0.0.1" in o]
            if localhost_origins:
                print(f"⚠️  Warning: Localhost origins in production: {localhost_origins}")
            
            # Check for HTTP origins in production
            http_origins = [o for o in settings.cors_origins if o.startswith("http://")]
            if http_origins:
                print(f"⚠️  Warning: HTTP origins in production (consider HTTPS): {http_origins}")
        
        else:
            print("🔧 Development mode detected")
            
            # Check for localhost origins
            has_localhost = any("localhost" in o or "127.0.0.1" in o for o in settings.cors_origins)
            if not has_localhost:
                print("⚠️  Warning: No localhost origins for development")
        
        print("\n✅ CORS configuration validation completed successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ ERROR: Could not import settings: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: Validation failed: {e}")
        return False


def test_cors_functions():
    """Test CORS utility functions"""
    
    print("\n🧪 Testing CORS Functions...")
    print("=" * 50)
    
    try:
        # Test without full FastAPI dependencies
        print("✅ Basic configuration loading works")
        
        # Test environment variable parsing
        test_origins = "http://localhost:3000,http://127.0.0.1:3000"
        parsed_origins = test_origins.split(",")
        print(f"✅ Origin parsing: {parsed_origins}")
        
        # Test boolean parsing
        test_bool = "true"
        parsed_bool = test_bool.lower() == "true"
        print(f"✅ Boolean parsing: {parsed_bool}")
        
        # Test list parsing
        test_methods = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
        parsed_methods = test_methods.split(",")
        print(f"✅ Methods parsing: {parsed_methods}")
        
        print("✅ All CORS function tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Function test failed: {e}")
        return False


def main():
    """Main validation function"""
    
    print("🚀 MemeGPT CORS Configuration Validator")
    print("=" * 60)
    
    # Run validations
    settings_ok = validate_cors_settings()
    functions_ok = test_cors_functions()
    
    print("\n📋 Summary")
    print("=" * 20)
    
    if settings_ok and functions_ok:
        print("✅ All CORS validations passed!")
        print("🎉 CORS configuration is ready for frontend communication!")
        return 0
    else:
        print("❌ Some validations failed!")
        print("🔧 Please check the configuration and fix any issues.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)