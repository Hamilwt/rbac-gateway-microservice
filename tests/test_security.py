from unittest.mock import patch
from app.core.security import create_refresh_token

def test_rate_limiter_triggers_429(client):
    # Mock the Lua script to return 0 (meaning "no tokens allowed")
    with patch("app.services.rate_limiter.rate_limit_script") as mock_script:
        mock_script.return_value = 0
        
        response = client.post(
            "/auth/login",
            data={"username": "hacker@example.com", "password": "pw"}
        )
        
        # Verify the 429 Too Many Requests was raised
        assert response.status_code == 429
        assert response.json()["detail"] == "Too many requests"
        assert "Retry-After" in response.headers

def test_revoked_refresh_token_fails(client):
    token = create_refresh_token(subject=1)
    
    # Mock Redis to pretend this token's JTI was found in the blacklist
    with patch("app.api.auth.redis_client.get", return_value=b"revoked"):
        response = client.post(f"/auth/refresh?refresh_token={token}")
        
        assert response.status_code == 401
        assert response.json()["detail"] == "Token has been revoked"