import requests

BASE_URL = "http://127.0.0.1:5000"  # Replace with your actual API URL

# Scenario: Test - Patient Progress

# 1. Valid Patient Progress Request
def test_show_patient_progress_valid():
    url = f"{BASE_URL}/pms/show_progress?patient_id=123"  # Valid patient_id
    response = requests.get(url)
    assert response.status_code == 200 

# 2. Missing patient_id Query Parameter
def test_show_patient_progress_missing_patient_id():
    url = f"{BASE_URL}/pms/show_progress"  # Missing patient_id
    response = requests.get(url)
    assert response.status_code == 400  # Expecting Bad Request due to missing required parameter

# 3. Invalid patient_id (Non-numeric Value)
def test_show_patient_progress_invalid_patient_id():
    url = f"{BASE_URL}/pms/show_progress?patient_id=abc"  # Invalid patient_id (non-numeric)
    response = requests.get(url)
    assert response.status_code == 400  # Expecting Bad Request due to invalid patient_id

# 4. Non-existent patient_id
def test_show_patient_progress_non_existent_patient_id():
    url = f"{BASE_URL}/pms/show_progress?patient_id=999999"  # Non-existent patient_id
    response = requests.get(url)
    assert response.status_code == 404  # Not Found, patient does not exist

# 5. Invalid HTTP Method (Using POST Instead of GET)
def test_show_patient_progress_invalid_method():
    url = f"{BASE_URL}/pms/show_progress?patient_id=123"  # Valid patient_id
    response = requests.post(url)  # Using POST instead of GET
    assert response.status_code == 405  # Method Not Allowed


