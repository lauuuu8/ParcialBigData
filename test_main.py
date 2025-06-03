import pytest
from unittest.mock import patch, Mock, call
from Lambda import download_headlines
import datetime


def test_successful_download(mock_s3_client, mock_requests_get, mock_datetime):
    # Mock de fecha
    mock_datetime.now.return_value = datetime.datetime(2024, 1, 1)
    mock_datetime.now.return_value.strftime.return_value = "2024-01-01"

    # Mock de respuesta HTTP
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html>noticias</html>"
    mock_requests_get.return_value = mock_response

    download_headlines()

    # Verificamos que se hayan subido los dos medios esperados
    expected_keys = [
        "headlines/raw/eltiempo-contenido-2024-01-01.html",
        "headlines/raw/publimetro-contenido-2024-01-01.html"
    ]

    upload_calls = mock_s3_client.upload_file.call_args_list
    uploaded_keys = [call_args[0][2] for call_args in upload_calls]

    for key in expected_keys:
        assert key in uploaded_keys, f"No se encontró la carga para {key}"

def test_failed_request_handling(mock_s3_client, mock_requests_get, mock_datetime):
    mock_datetime.now.return_value = datetime.datetime(2024, 1, 1)
    mock_datetime.now.return_value.strftime.return_value = "2024-01-01"

    mock_response = Mock()
    mock_response.status_code = 500  # simulamos error en el sitio
    mock_requests_get.return_value = mock_response

    download_headlines()

    # Asegurarnos de que no se intentó subir nada a S3
    mock_s3_client.upload_file.assert_not_called()

def test_partial_failure(mock_s3_client, mock_requests_get, mock_datetime):
    mock_datetime.now.return_value = datetime.datetime(2024, 1, 1)
    mock_datetime.now.return_value.strftime.return_value = "2024-01-01"

    # Primera llamada exitosa, segunda falla
    def side_effect(url, headers):
        if "eltiempo" in url:
            ok_response = Mock()
            ok_response.status_code = 200
            ok_response.text = "<html>noticias tiempo</html>"
            return ok_response
        else:
            error_response = Mock()
            error_response.status_code = 500
            return error_response

    mock_requests_get.side_effect = side_effect

    download_headlines()

    upload_calls = mock_s3_client.upload_file.call_args_list
    assert len(upload_calls) == 1
    assert "eltiempo" in upload_calls[0][0][2]

