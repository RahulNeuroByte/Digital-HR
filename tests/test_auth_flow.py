from unittest.mock import MagicMock
from app.db import db_manager

def test_sync_user_profile_real_credentials():
    # Test that sync_user_profile constructs clean profile from real user details
    profile = db_manager.sync_user_profile(
        user_id="real-uuid-12345",
        email="testuser@coforge.com",
        name="Test User",
        avatar_url="https://lh3.googleusercontent.com/a/sample-avatar",
    )

    assert profile["id"] == "real-uuid-12345"
    assert profile["email"] == "testuser@coforge.com"
    assert profile["name"] == "Test User"
    assert profile["avatar"] == "https://lh3.googleusercontent.com/a/sample-avatar"
    assert profile["role"] == "Employee"

def test_sync_user_profile_fallback_name():
    # If name is missing from Google metadata, fall back to email username
    profile = db_manager.sync_user_profile(
        user_id="real-uuid-67890",
        email="john.doe@domain.com",
        name="",
        avatar_url="",
    )

    assert profile["id"] == "real-uuid-67890"
    assert profile["email"] == "john.doe@domain.com"
    assert profile["name"] == "john.doe"
