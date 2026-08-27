def test_register_success(client):
    response = client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "securepassword123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    # Ensure sensitive data is stripped!
    assert "password" not in data
    assert "hashed_password" not in data

def test_register_duplicate_email(client):
    # Register the first time
    client.post(
        "/auth/register",
        json={"email": "duplicate@example.com", "password": "password123"}
    )
    # Try to register the exact same email again
    response = client.post(
        "/auth/register",
        json={"email": "duplicate@example.com", "password": "password123"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_login_success(client):
    # Create the user
    client.post(
        "/auth/register",
        json={"email": "login@example.com", "password": "password123"}
    )
    # Attempt to log in (FastAPI OAuth2 uses form data, not JSON)
    response = client.post(
        "/auth/login",
        data={"username": "login@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()

def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        json={"email": "wrong@example.com", "password": "password123"}
    )
    response = client.post(
        "/auth/login",
        data={"username": "wrong@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"