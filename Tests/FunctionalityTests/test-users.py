import requests

BASE_URL = "http://127.0.0.1:5000"  # Replace with your actual API URL

# Scenario: Tests- Patients
    
# 1. Valid Patient Addition
def test_add_patient_valid():
    url = f"{BASE_URL}/pms/add_patient"
    data = {
        "subject_id": 123,
        "gender": "M",
        "dob": "1990-05-20",
        "dod": ""  # Optional field
    }
    response = requests.post(url, data=data)
    assert response.status_code == 200  # Redirect indicates successful addition

import requests

BASE_URL = "http://localhost:5000"  # Update with the correct base URL

# 1. Valid Show Patients Request
def test_show_patients_valid():
    url = f"{BASE_URL}/pms/show_patients"
    response = requests.get(url)
    assert response.status_code == 200  # Expect successful retrieval
    assert "text/html" in response.headers["Content-Type"]  # Ensure it's rendering HTML content

    
# 1. Valid Edit Patient Request
def test_edit_patient_valid():
    url = f"{BASE_URL}/pms/edit_patient"
    data = {
        "subject_id": 123,
        "gender": "F",
        "dob": "1992-07-15",
        "dod": ""  # Optional field
    }
    response = requests.post(url, data=data)
    assert response.status_code == 200 # Redirect indicates successful update
    
    