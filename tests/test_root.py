import pytest
from fastapi.testclient import TestClient

def test_read_root(client: TestClient):
    """Test GET / endpoint returns 200 and expected message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "API is running"}
