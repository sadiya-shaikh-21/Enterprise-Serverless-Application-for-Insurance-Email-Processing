"""
Unit tests for Valid Domains Lambda function.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any, Tuple

# Import the functions to test
from lambda_fuction import (
    get_parameters,
    load_mailbox_configuration,
    save_configuration_to_s3,
    fetch_valid_domains_from_database,
    process_domain_data,
    validate_and_filter_domains,
    save_domains_to_s3,
    prepare_final_response,
    lambda_handler
)
from common_error_utils import SystemException


class TestGetParameters:
    """Tests for get_parameters function."""

    @patch('lambda_fuction.get_all_parameters')
    @patch('lambda_fuction.logger')
    def test_get_parameters_success(self, mock_logger, mock_get_all_params):
        """Test successful parameter retrieval."""
        mock_params = {"s3_bucket_name": "test-bucket", "db_host": "localhost"}
        mock_get_all_params.return_value = mock_params

        result = get_parameters("test-correlation-id")

        assert result == mock_params
        mock_get_all_params.assert_called_once()

    @patch('lambda_fuction.get_all_parameters')
    @patch('lambda_fuction.logger')
    def test_get_parameters_empty(self, mock_logger, mock_get_all_params):
        """Test parameter retrieval with empty result."""
        mock_get_all_params.return_value = {}

        with pytest.raises(SystemException) as exc_info:
            get_parameters("test-correlation-id")

        assert "EAWS006" in str(exc_info.value)

    @patch('lambda_fuction.get_all_parameters')
    @patch('lambda_fuction.logger')
    def test_get_parameters_exception(self, mock_logger, mock_get_all_params):
        """Test parameter retrieval with exception."""
        mock_get_all_params.side_effect = Exception("Connection error")

        with pytest.raises(SystemException) as exc_info:
            get_parameters("test-correlation-id")

        assert "EAWS006" in str(exc_info.value)


class TestLoadMailboxConfiguration:
    """Tests for load_mailbox_configuration function."""

    @patch('lambda_fuction.download_json_from_s3')
    @patch('lambda_fuction.logger')
    def test_load_mailbox_configuration_success(self, mock_logger, mock_download):
        """Test successful mailbox configuration loading."""
        mock_mailboxes = [{"mailbox": "inbox1"}, {"mailbox": "inbox2"}]
        mock_download.return_value = mock_mailboxes
        parameters = {"s3_bucket_name": "test-bucket"}

        result = load_mailbox_configuration(parameters, "test-correlation-id")

        assert result["inboxes"] == mock_mailboxes
        assert result["s3_bucket_name"] == "test-bucket"

    @patch('lambda_fuction.logger')
    def test_load_mailbox_configuration_missing_bucket(self, mock_logger):
        """Test mailbox configuration with missing S3 bucket."""
        parameters = {}

        with pytest.raises(SystemException) as exc_info:
            load_mailbox_configuration(parameters, "test-correlation-id")

        assert "EAWS014" in str(exc_info.value)

    @patch('lambda_fuction.download_json_from_s3')
    @patch('lambda_fuction.logger')
    def test_load_mailbox_configuration_download_error(self, mock_logger, mock_download):
        """Test mailbox configuration with download error."""
        mock_download.side_effect = Exception("Download failed")
        parameters = {"s3_bucket_name": "test-bucket"}

        with pytest.raises(SystemException) as exc_info:
            load_mailbox_configuration(parameters, "test-correlation-id")

        assert "EAWS008" in str(exc_info.value)


class TestSaveConfigurationToS3:
    """Tests for save_configuration_to_s3 function."""

    @patch('lambda_fuction.upload_to_s3')
    @patch('lambda_fuction.logger')
    @patch('lambda_fuction.uki_constants', {"config_json_file": "config.json"})
    def test_save_configuration_success(self, mock_logger, mock_upload):
        """Test successful configuration save."""
        parameters = {"s3_bucket_name": "test-bucket", "key": "value"}

        result = save_configuration_to_s3(parameters, "test-correlation-id")

        assert result == "test-bucket"
        mock_upload.assert_called_once()

    @patch('lambda_fuction.logger')
    def test_save_configuration_missing_bucket(self, mock_logger):
        """Test configuration save with missing S3 bucket."""
        parameters = {}

        with pytest.raises(SystemException) as exc_info:
            save_configuration_to_s3(parameters, "test-correlation-id")

        assert "EAWS014" in str(exc_info.value)

    @patch('lambda_fuction.upload_to_s3')
    @patch('lambda_fuction.logger')
    @patch('lambda_fuction.uki_constants', {"config_json_file": "config.json"})
    def test_save_configuration_upload_error(self, mock_logger, mock_upload):
        """Test configuration save with upload error."""
        mock_upload.side_effect = Exception("Upload failed")
        parameters = {"s3_bucket_name": "test-bucket"}

        with pytest.raises(SystemException) as exc_info:
            save_configuration_to_s3(parameters, "test-correlation-id")

        assert "EAWS016" in str(exc_info.value)


class TestFetchValidDomainsFromDatabase:
    """Tests for fetch_valid_domains_from_database function."""

    @patch('lambda_fuction.run_stored_procedure')
    @patch('lambda_fuction.logger')
    def test_fetch_valid_domains_success(self, mock_logger, mock_procedure):
        """Test successful domain fetching."""
        mock_rows = [("1", "sender@example.com", "category1")]
        mock_column_map = {"ID": 0, "From": 1, "Category": 2}
        mock_procedure.return_value = (mock_rows, mock_column_map)
        parameters = {"db_host": "localhost"}

        rows, column_map = fetch_valid_domains_from_database(parameters, "test-correlation-id")

        assert rows == mock_rows
        assert column_map == mock_column_map

    @patch('lambda_fuction.run_stored_procedure')
    @patch('lambda_fuction.logger')
    def test_fetch_valid_domains_empty(self, mock_logger, mock_procedure):
        """Test domain fetching with no results."""
        mock_procedure.return_value = ([], {})
        parameters = {"db_host": "localhost"}

        with pytest.raises(SystemException) as exc_info:
            fetch_valid_domains_from_database(parameters, "test-correlation-id")

        assert "EAWS007" in str(exc_info.value)

    @patch('lambda_fuction.run_stored_procedure')
    @patch('lambda_fuction.logger')
    def test_fetch_valid_domains_error(self, mock_logger, mock_procedure):
        """Test domain fetching with error."""
        mock_procedure.side_effect = Exception("DB error")
        parameters = {"db_host": "localhost"}

        with pytest.raises(SystemException) as exc_info:
            fetch_valid_domains_from_database(parameters, "test-correlation-id")

        assert "EAWS007" in str(exc_info.value)


class TestProcessDomainData:
    """Tests for process_domain_data function."""

    @patch('lambda_fuction.logger')
    def test_process_domain_data_success(self, mock_logger):
        """Test successful domain data processing."""
        rows = [("1", "sender@example.com", "Banking")]
        column_map = {"ID": 0, "From": 1, "Category": 2}

        result = process_domain_data(rows, column_map)

        assert len(result) == 1
        assert result[0]["id"] == "1"
        assert result[0]["from"] == "sender@example.com"
        assert result[0]["category"] == "Banking"
        assert result[0]["is_active"] is True

    @patch('lambda_fuction.logger')
    def test_process_domain_data_multiple_rows(self, mock_logger):
        """Test processing multiple domain rows."""
        rows = [
            ("1", "sender1@example.com", "Banking"),
            ("2", "sender2@example.com", "Insurance")
        ]
        column_map = {"ID": 0, "From": 1, "Category": 2}

        result = process_domain_data(rows, column_map)

        assert len(result) == 2

    @patch('lambda_fuction.logger')
    def test_process_domain_data_invalid_row(self, mock_logger):
        """Test processing with invalid row."""
        rows = [("1", "sender@example.com", "Banking"), ("invalid",)]
        column_map = {"ID": 0, "From": 1, "Category": 2}

        result = process_domain_data(rows, column_map)

        assert len(result) == 1

    @patch('lambda_fuction.logger')
    def test_process_domain_data_case_normalization(self, mock_logger):
        """Test email address normalization."""
        rows = [("1", "SENDER@EXAMPLE.COM", "Banking")]
        column_map = {"ID": 0, "From": 1, "Category": 2}

        result = process_domain_data(rows, column_map)

        assert result[0]["from"] == "sender@example.com"


class TestValidateAndFilterDomains:
    """Tests for validate_and_filter_domains function."""

    @patch('lambda_fuction.logger')
    def test_validate_and_filter_domains_valid(self, mock_logger):
        """Test validation with valid domains."""
        domains = [
            {"id": "1", "from": "sender@example.com", "category": "Banking"},
            {"id": "2", "from": "user@domain.org", "category": "Insurance"}
        ]

        result = validate_and_filter_domains(domains)

        assert len(result) == 2
        assert result[0]["domain_part"] == "example.com"
        assert result[0]["is_valid_format"] is True

    @patch('lambda_fuction.logger')
    def test_validate_and_filter_domains_invalid_format(self, mock_logger):
        """Test validation with invalid domain format."""
        domains = [
            {"id": "1", "from": "invalidemail", "category": "Banking"},
            {"id": "2", "from": "sender@localhost", "category": "Banking"}
        ]

        result = validate_and_filter_domains(domains)

        assert len(result) == 0

    @patch('lambda_fuction.logger')
    def test_validate_and_filter_domains_mixed(self, mock_logger):
        """Test validation with mixed valid and invalid domains."""
        domains = [
            {"id": "1", "from": "valid@example.com", "category": "Banking"},
            {"id": "2", "from": "invalid", "category": "Banking"},
            {"id": "3", "from": "another@domain.org", "category": "Insurance"}
        ]

        result = validate_and_filter_domains(domains)

        assert len(result) == 2

    @patch('lambda_fuction.logger')
    def test_validate_and_filter_domains_empty_from(self, mock_logger):
        """Test validation with empty from field."""
        domains = [{"id": "1", "from": "", "category": "Banking"}]

        result = validate_and_filter_domains(domains)

        assert len(result) == 0


class TestSaveDomainsToS3:
    """Tests for save_domains_to_s3 function."""

    @patch('lambda_fuction.upload_to_s3')
    @patch('lambda_fuction.logger')
    @patch('lambda_fuction.uki_constants', {"domains_json_file": "domains.json"})
    def test_save_domains_success(self, mock_logger, mock_upload):
        """Test successful domains save."""
        domains = [{"id": "1", "from": "sender@example.com"}]

        save_domains_to_s3(domains, "test-bucket", "test-correlation-id")

        mock_upload.assert_called_once()
        call_args = mock_upload.call_args
        assert "test-bucket" in call_args[1].values()

    @patch('lambda_fuction.logger')
    def test_save_domains_empty_list(self, mock_logger):
        """Test saving empty domains list."""
        with pytest.raises(SystemException) as exc_info:
            save_domains_to_s3([], "test-bucket", "test-correlation-id")

        assert "EAWS007" in str(exc_info.value)

    @patch('lambda_fuction.upload_to_s3')
    @patch('lambda_fuction.logger')
    @patch('lambda_fuction.uki_constants', {"domains_json_file": "domains.json"})
    def test_save_domains_upload_error(self, mock_logger, mock_upload):
        """Test domains save with upload error."""
        mock_upload.side_effect = Exception("Upload failed")
        domains = [{"id": "1", "from": "sender@example.com"}]

        with pytest.raises(SystemException) as exc_info:
            save_domains_to_s3(domains, "test-bucket", "test-correlation-id")

        assert "EAWS019" in str(exc_info.value)


class TestPrepareFinalResponse:
    """Tests for prepare_final_response function."""

    @patch('lambda_fuction.uki_constants', {
        "domains_json_file": "domains.json",
        "config_json_file": "config.json"
    })
    def test_prepare_final_response_success(self):
        """Test successful response preparation."""
        domains = [
            {"id": "1", "from": "sender@example.com", "domain_part": "example.com", "category": "Banking"},
            {"id": "2", "from": "user@domain.org", "domain_part": "domain.org", "category": "Insurance"}
        ]

        response = prepare_final_response(domains, "test-bucket", "test-correlation-id")

        assert response["status"] == "success"
        assert response["correlation_id"] == "test-correlation-id"
        assert response["summary"]["total_domains"] == 2
        assert response["summary"]["s3_bucket_name"] == "test-bucket"
        assert "timestamp" in response

    @patch('lambda_fuction.uki_constants', {
        "domains_json_file": "domains.json",
        "config_json_file": "config.json"
    })
    def test_prepare_final_response_categories(self):
        """Test response category counts."""
        domains = [
            {"id": "1", "from": "sender@example.com", "domain_part": "example.com", "category": "Banking"},
            {"id": "2", "from": "user@domain.org", "domain_part": "domain.org", "category": "Banking"},
            {"id": "3", "from": "admin@test.com", "domain_part": "test.com", "category": "Insurance"}
        ]

        response = prepare_final_response(domains, "test-bucket", "test-correlation-id")

        assert response["domain_categories"]["Banking"] == 2
        assert response["domain_categories"]["Insurance"] == 1

    @patch('lambda_fuction.uki_constants', {
        "domains_json_file": "domains.json",
        "config_json_file": "config.json"
    })
    def test_prepare_final_response_top_domains(self):
        """Test top domains extraction."""
        domains = [
            {"id": f"{i}", "from": f"sender{i}@example.com", "domain_part": "example.com", "category": "Banking"}
            for i in range(15)
        ]

        response = prepare_final_response(domains, "test-bucket", "test-correlation-id")

        assert len(response["top_domains"]) == 10

    @patch('lambda_fuction.uki_constants', {
        "domains_json_file": "domains.json",
        "config_json_file": "config.json"
    })
    def test_prepare_final_response_empty_domains(self):
        """Test response with empty domains."""
        response = prepare_final_response([], "test-bucket", "test-correlation-id")

        assert response["summary"]["total_domains"] == 0
        assert len(response["top_domains"]) == 0


class TestLambdaHandler:
    """Tests for lambda_handler function."""

    @patch('lambda_fuction.prepare_final_response')
    @patch('lambda_fuction.save_domains_to_s3')
    @patch('lambda_fuction.validate_and_filter_domains')
    @patch('lambda_fuction.process_domain_data')
    @patch('lambda_fuction.fetch_valid_domains_from_database')
    @patch('lambda_fuction.save_configuration_to_s3')
    @patch('lambda_fuction.load_mailbox_configuration')
    @patch('lambda_fuction.get_parameters')
    @patch('lambda_fuction.set_extra_log_attributes')
    @patch('lambda_fuction.logger')
    def test_lambda_handler_success(self, mock_logger, mock_set_attrs, mock_get_params,
                                    mock_load_config, mock_save_config, mock_fetch_domains,
                                    mock_process, mock_validate, mock_save_s3, mock_prepare):
        """Test successful lambda handler execution."""
        event = {"correlation_id": "test-correlation-id"}
        mock_get_params.return_value = {"s3_bucket_name": "test-bucket"}
        mock_load_config.return_value = {"s3_bucket_name": "test-bucket"}
        mock_save_config.return_value = "test-bucket"
        mock_fetch_domains.return_value = ([("1", "sender@example.com", "Banking")], {"ID": 0, "From": 1, "Category": 2})
        mock_process.return_value = [{"id": "1", "from": "sender@example.com"}]
        mock_validate.return_value = [{"id": "1", "from": "sender@example.com", "domain_part": "example.com"}]
        mock_prepare.return_value = {"status": "success"}

        result = lambda_handler(event)

        assert result["status"] == "success"
        assert result["correlation_id"] == "test-correlation-id"

    @patch('lambda_fuction.logger')
    def test_lambda_handler_missing_correlation_id(self, mock_logger):
        """Test lambda handler with missing correlation_id."""
        event = {}

        with pytest.raises(SystemException) as exc_info:
            lambda_handler(event)

        assert "EAWS001" in str(exc_info.value)

    @patch('lambda_fuction.get_parameters')
    @patch('lambda_fuction.set_extra_log_attributes')
    @patch('lambda_fuction.logger')
    def test_lambda_handler_get_parameters_error(self, mock_logger, mock_set_attrs, mock_get_params):
        """Test lambda handler with get_parameters error."""
        event = {"correlation_id": "test-correlation-id"}
        mock_get_params.side_effect = SystemException("EAWS006: Error")

        with pytest.raises(SystemException):
            lambda_handler(event)

    @patch('lambda_fuction.handle_exception')
    @patch('lambda_fuction.get_parameters')
    @patch('lambda_fuction.set_extra_log_attributes')
    @patch('lambda_fuction.logger')
    def test_lambda_handler_generic_exception(self, mock_logger, mock_set_attrs, mock_get_params, mock_handle):
        """Test lambda handler with generic exception."""
        event = {"correlation_id": "test-correlation-id"}
        mock_get_params.side_effect = Exception("Unexpected error")

        lambda_handler(event)

        mock_handle.assert_called_once()

    @patch('lambda_fuction.logger')
    def test_lambda_handler_with_id_field(self, mock_logger):
        """Test lambda handler with 'id' field instead of 'correlation_id'."""
        event = {"id": "test-id"}

        with patch('lambda_fuction.get_parameters') as mock_get_params:
            mock_get_params.return_value = {"s3_bucket_name": "test-bucket"}
            with patch('lambda_fuction.load_mailbox_configuration') as mock_load:
                mock_load.return_value = {"s3_bucket_name": "test-bucket"}
                with patch('lambda_fuction.save_configuration_to_s3') as mock_save:
                    mock_save.return_value = "test-bucket"
                    with patch('lambda_fuction.fetch_valid_domains_from_database') as mock_fetch:
                        mock_fetch.return_value = ([], {})

                        # Should not raise due to missing correlation_id
                        with pytest.raises(SystemException) as exc_info:
                            lambda_handler(event)