import pytest
import requests

BASE_URL = "http://127.0.0.1:5000"  # Replace with your actual API URL

# Scenario: Test - Questions

# 1. Missing patient_id Query Parameter
def test_view_questions_missing_patient_id():
    url = f"{BASE_URL}/qms/view_questions"  # Missing patient_id
    response = requests.get(url)
    assert response.status_code == 400  # Expecting Bad Request due to missing required parameter

# 2. Invalid `patient_id` (Non-numeric Value)
def test_view_questions_invalid_patient_id():
    url = f"{BASE_URL}/qms/view_questions?patient_id=abc"  # Invalid patient_id (non-numeric)
    response = requests.get(url)
    assert response.status_code == 500  # Bad request (parameter validation failure)

# 3. Empty `patient_id` Query Parameter
def test_view_questions_empty_patient_id():
    url = f"{BASE_URL}/qms/view_questions?patient_id="  # Empty patient_id
    response = requests.get(url)
    assert response.status_code == 400  # Bad request due to empty value

# 4. Invalid `patient_id` with Special Characters
def test_view_questions_special_characters_patient_id():
    url = f"{BASE_URL}/qms/view_questions?patient_id=@#%^"  # Special characters in patient_id
    response = requests.get(url)
    assert response.status_code == 500  # Bad request due to invalid characters

# 5. Invalid HTTP Method (Trying POST instead of GET)
def test_view_questions_invalid_method():
    url = f"{BASE_URL}/qms/view_questions?patient_id=123"
    response = requests.post(url)  # Wrong HTTP method
    assert response.status_code == 405  # Method Not Allowed

# 6. Valid scenario for viewing questions
def test_view_questions():
    url = f"{BASE_URL}/qms/view_questions?patient_id=123"  # Add patient_id query parameter
    response = requests.get(url)
    assert response.status_code == 200
