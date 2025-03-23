import requests

BASE_URL = "http://127.0.0.1:5000"  # Replace with your actual API URL

# Scenario: Test - View Media

# 1. Valid Media Request
def test_view_media_valid():
    url = f"{BASE_URL}/mms/show_media/123"  # Valid media_key
    response = requests.get(url)
    assert response.status_code == 200  # Expecting a successful response
    assert "Content-Type" in response.headers  # Check if the Content-Type header is present
    assert "image" in response.headers["Content-Type"] or "application" in response.headers["Content-Type"]  # Check if it's a media file

# 2. Invalid Media Key (Non-existent)
def test_view_media_invalid_key():
    url = f"{BASE_URL}/mms/show_media/999999"  # Non-existent media_key
    response = requests.get(url)
    assert response.status_code == 404  # Expecting a Not Found error

# 3. Invalid Media Key (Non-numeric)
def test_view_media_invalid_key_format():
    url = f"{BASE_URL}/mms/show_media/abc"  # Invalid media_key (non-numeric)
    response = requests.get(url)
    assert response.status_code == 400  # Bad Request due to invalid media key format

# 4. Timeout Scenario (Slow Media Retrieval)
def test_view_media_timeout():
    url = f"{BASE_URL}/mms/show_media/123"  # Valid media_key
    try:
        response = requests.get(url, timeout=1)  # Set a short timeout
        assert response.status_code == 408  # Expecting a Timeout
    except requests.exceptions.Timeout:
        assert True  # Timeout expected

# 5. Invalid HTTP Method (Using POST Instead of GET)
def test_view_media_invalid_method():
    url = f"{BASE_URL}/mms/show_media/123"  # Valid media_key
    response = requests.post(url)  # Using POST instead of GET
    assert response.status_code == 405  # Method Not Allowed

# 6. Missing Media Key
def test_view_media_missing_key():
    url = f"{BASE_URL}/mms/show_media/"  # Missing media_key in URL
    response = requests.get(url)
    assert response.status_code == 400  # Bad Request due to missing media_key
