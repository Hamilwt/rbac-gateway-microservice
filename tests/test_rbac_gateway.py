from unittest.mock import AsyncMock, patch
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.core.security import create_access_token

def test_no_token_returns_401(client):
    response = client.get("/users/me")
    assert response.status_code == 401

def test_missing_permission_returns_403(client):
    # Register and login to get a fresh token (no permissions assigned)
    client.post("/auth/register", json={"email": "rbac@example.com", "password": "pass"})
    login_resp = client.post("/auth/login", data={"username": "rbac@example.com", "password": "pass"})
    token = login_resp.json()["access_token"]
    
    # Attempt to hit an endpoint that requires 'users:read'
    response = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    # FIX: Updated the expected string to match our actual API response
    assert "Missing required permission" in response.json().get("detail", "")

@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
def test_gateway_forwards_request(mock_request, client, db_session):
    # 1. Setup DB with a user that explicitly has the 'inventory:read' permission
    perm = Permission(name="inventory:read")
    role = Role(name="gateway_admin", permissions=[perm])
    user = User(email="gateway@example.com", hashed_password="pw", roles=[role])
    db_session.add(user)
    db_session.commit()
    
    # 2. Generate their token
    token = create_access_token(subject=user.id, permissions=["inventory:read"])
    
    # 3. Configure our fake "Inventory API" response
    mock_request.return_value.status_code = 200
    mock_request.return_value.content = b'{"mocked": "inventory_data"}'
    mock_request.return_value.headers = {"Content-Type": "application/json"}
    
    # 4. Hit our Gateway route
    response = client.get(
        "/gateway/inventory/products",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # 5. Verify the gateway intercepted, authorized, and forwarded it properly
    assert response.status_code == 200
    assert response.json() == {"mocked": "inventory_data"}
    mock_request.assert_called_once()