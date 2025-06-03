import pytest
from unittest.mock import Mock, call
import datetime
from Lambda import download_headlines  # Ajusta esto al nombre del archivo

def test_download_headlines_success(mocker):
    # Mock response de requests
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "contenido html de prueba"
    
    mocker.patch('requests.get', return_value=mock_response)
    
    # Mock boto3 client y su método upload_file
    mock_s3_client = mocker.patch('boto3.client')
    
    # Mock datetime para fijar fecha
    mock_datetime = mocker.patch('datetime.datetime')
    mock_datetime.now.return_value.strftime.return_value = "2025-06-03"
    
    download_headlines()
    
    s3_instance = mock_s3_client.return_value
    
    expected_calls = [
        call.upload_file(
            f"/tmp/{site}-contenido-2025-06-03.html",
            "eltiempop",
            f"headlines/raw/{site}-contenido-2025-06-03.html"
        ) for site in ["eltiempo", "publimetro"]
    ]
    
    for expected_call in expected_calls:
        assert expected_call in s3_instance.upload_file.mock_calls

def test_download_headlines_http_error(mocker):
    # Simula un error HTTP 404
    mock_response = Mock()
    mock_response.status_code = 404
    
    mocker.patch('requests.get', return_value=mock_response)
    mock_s3_client = mocker.patch('boto3.client')
    
    download_headlines()
    
    s3_instance = mock_s3_client.return_value
    s3_instance.upload_file.assert_not_called()
