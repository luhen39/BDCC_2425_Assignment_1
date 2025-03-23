import pytest
import requests

BASE_URL = "http://127.0.0.1:5000"  # Replace with your actual API URL

# Scenario: Test - Long Waiting Patients Endpoint
def test_long_waiting_patients():
    url = f"{BASE_URL}/pms/longer_waiting_time"
    response = requests.get(url)
    assert response.status_code == 200
    assert "text/html" in response.headers["Content-Type"]

if __name__ == "__main__":
    pytest.main()
