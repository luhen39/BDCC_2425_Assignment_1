import requests

BASE_URL = "http://127.0.0.1:5000"  # Replace with your actual API URL

# Scenario: Tests- Admissions
    
# 1. Valid Show Admissions Request
def test_show_admissions_valid():
    url = f"{BASE_URL}/pms/show_admissions"
    params = {
        "patient_id": 123  # Valid patient_id
    }
    response = requests.get(url, params=params)
    assert response.status_code == 200  # Expect successful retrieval
    assert "text/html" in response.headers["Content-Type"]  # Ensure it's rendering HTML content

# 2. Missing Patient ID in Show Admissions Request
def test_show_admissions_missing_patient_id():
    url = f"{BASE_URL}/pms/show_admissions"
    response = requests.get(url)
    assert response.status_code == 400  # Bad request due to missing patient_id
    assert response.json().get("error") == "patient_id is required"  # Check the error message



