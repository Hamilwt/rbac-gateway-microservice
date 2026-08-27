from redis.exceptions import RedisError
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
        response = client.post("/auth/refresh", json={"refresh_token": token})

        assert response.status_code == 401
        assert response.json()["detail"] == "Token has been revoked"

def test_refresh_token_rotation(client):
    # Register and log in to get the initial token pair
    client.post("/auth/register", json={"email": "rotate@example.com", "password": "password123"})
    login_resp = client.post(
        "/auth/login",
        data={"username": "rotate@example.com", "password": "password123"}
    )
    old_refresh_token = login_resp.json()["refresh_token"]

    # First refresh should succeed and hand back a brand new refresh token
    first_refresh = client.post("/auth/refresh", json={"refresh_token": old_refresh_token})
    assert first_refresh.status_code == 200
    new_refresh_token = first_refresh.json()["refresh_token"]

    # Proves rotation actually happened, not just that a token was returned
    assert new_refresh_token != old_refresh_token

    # Reusing the OLD refresh token a second time must now be rejected
    second_refresh = client.post("/auth/refresh", json={"refresh_token": old_refresh_token})
    assert second_refresh.status_code == 401
    assert second_refresh.json()["detail"] == "Token has been revoked"


def test_refresh_fails_closed_when_redis_down(client):
    token = create_refresh_token(subject=1)

    # Simulate Redis being unreachable during the revocation check
    with patch("app.api.auth.redis_client.get", side_effect=RedisError("connection refused")):
        response = client.post("/auth/refresh", json={"refresh_token": token})

        assert response.status_code == 503