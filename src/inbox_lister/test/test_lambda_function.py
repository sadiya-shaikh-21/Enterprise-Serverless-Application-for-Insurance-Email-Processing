import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any, List

# Mock external dependencies
@pytest.fixture(autouse=True)
def mock_dependencies():
    with patch('lambda_function.get_common_logger'):
        with patch('lambda_function.set_extra_log_attributes'):
            with patch('lambda_function.download_json_from_s3'):
                with patch('lambda_function.handle_exception'):
                    yield


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def sample_mailbox_config():
    return {
        "mailboxes": [
            {
                "mailboxName": "ops-inbox-1",
                "mailboxType": "ops",
                "teamID": "team_ops_001",
                "isActive": True,
                "priority": 3,
                "processingLimit": 50
            },
            {
                "mailboxName": "claims-inbox-1",
                "mailboxType": "claims",
                "teamID": "team_claims_001",
                "isActive": True,
                "priority": 5
            }
        ]
    }


@pytest.fixture
def sample_event():
    return {
        'correlation_id': 'corr-12345',
        'team_id': 'team_ops_001',
        's3_bucket_name': 'my-test-bucket'
    }


class TestValidateSingleMailbox:
    """Test cases for _validate_single_mailbox function"""

    def test_valid_mailbox_with_all_fields(self):
        import lambda_function
        mailbox = {
            "mailboxName": "ops-inbox-1",
            "mailboxType": "ops",
            "teamID": "team_ops_001",
            "isActive": True,
            "priority": 3,
            "processingLimit": 50,
            "retryCount": 5,
            "description": "Operations mailbox",
            "category": "primary"
        }
        result = lambda_function._validate_single_mailbox(mailbox, 0)
        assert result["mailboxName"] == "ops-inbox-1"
        assert result["mailboxType"] == "ops"
        assert result["priority"] == 3
        assert result["description"] == "Operations mailbox"

    def test_valid_mailbox_with_defaults(self):
        import lambda_function
        mailbox = {
            "mailboxName": "claims-inbox",
            "mailboxType": "claims",
            "teamID": "team_claims_001"
        }
        result = lambda_function._validate_single_mailbox(mailbox, 0)
        assert result["priority"] == 5
        assert result["processingLimit"] == 75
        assert result["retryCount"] == 3
        assert result["isActive"] is True
        assert result["description"] == ""
        assert result["category"] == "default"

    def test_mailbox_type_case_insensitive(self):
        import lambda_function
        mailbox = {
            "mailboxName": "test",
            "mailboxType": "OPS",
            "teamID": "team_001"
        }
        result = lambda_function._validate_single_mailbox(mailbox, 0)
        assert result["mailboxType"] == "ops"

    def test_mailbox_type_claims_case_insensitive(self):
        import lambda_function
        mailbox = {
            "mailboxName": "test",
            "mailboxType": "Claims",
            "teamID": "team_001"
        }
        result = lambda_function._validate_single_mailbox(mailbox, 0)
        assert result["mailboxType"] == "claims"

    def test_missing_mailbox_name(self):
        import lambda_function
        mailbox = {
            "mailboxType": "ops",
            "teamID": "team_001"
        }
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function._validate_single_mailbox(mailbox, 0)
        assert "EAWS012" in str(exc_info.value)
        assert "mailboxName" in str(exc_info.value)

    def test_missing_mailbox_type(self):
        import lambda_function
        mailbox = {
            "mailboxName": "test",
            "teamID": "team_001"
        }
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function._validate_single_mailbox(mailbox, 0)
        assert "EAWS012" in str(exc_info.value)

    def test_missing_team_id(self):
        import lambda_function
        mailbox = {
            "mailboxName": "test",
            "mailboxType": "ops"
        }
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function._validate_single_mailbox(mailbox, 0)
        assert "EAWS012" in str(exc_info.value)

    def test_missing_multiple_fields(self):
        import lambda_function
        mailbox = {"mailboxName": "test"}
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function._validate_single_mailbox(mailbox, 0)
        assert "EAWS012" in str(exc_info.value)

    def test_invalid_mailbox_type(self):
        import lambda_function
        mailbox = {
            "mailboxName": "test",
            "mailboxType": "invalid",
            "teamID": "team_001"
        }
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function._validate_single_mailbox(mailbox, 0)
        assert "EAWS015" in str(exc_info.value)

    def test_processing_limit_exceeds_maximum(self):
        import lambda_function
        mailbox = {
            "mailboxName": "test",
            "mailboxType": "ops",
            "teamID": "team_001",
            "processingLimit": 150
        }
        result = lambda_function._validate_single_mailbox(mailbox, 0)
        assert result["processingLimit"] == 100

    def test_processing_limit_at_maximum(self):
        import lambda_function
        mailbox = {
            "mailboxName": "test",
            "mailboxType": "ops",
            "teamID": "team_001",
            "processingLimit": 100
        }
        result = lambda_function._validate_single_mailbox(mailbox, 0)
        assert result["processingLimit"] == 100

    def test_mailbox_name_stripped(self):
        import lambda_function
        mailbox = {
            "mailboxName": "  test-inbox  ",
            "mailboxType": "ops",
            "teamID": "team_001"
        }
        result = lambda_function._validate_single_mailbox(mailbox, 0)
        assert result["mailboxName"] == "test-inbox"

    def test_team_id_stripped(self):
        import lambda_function
        mailbox = {
            "mailboxName": "test",
            "mailboxType": "ops",
            "teamID": "  team_001  "
        }
        result = lambda_function._validate_single_mailbox(mailbox, 0)
        assert result["teamID"] == "team_001"

    def test_empty_mailbox_name(self):
        import lambda_function
        mailbox = {
            "mailboxName": "",
            "mailboxType": "ops",
            "teamID": "team_001"
        }
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function._validate_single_mailbox(mailbox, 0)
        assert "EAWS012" in str(exc_info.value)

    def test_priority_zero(self):
        import lambda_function
        mailbox = {
            "mailboxName": "test",
            "mailboxType": "ops",
            "teamID": "team_001",
            "priority": 0
        }
        result = lambda_function._validate_single_mailbox(mailbox, 0)
        assert result["priority"] == 0

    def test_high_priority_value(self):
        import lambda_function
        mailbox = {
            "mailboxName": "test",
            "mailboxType": "ops",
            "teamID": "team_001",
            "priority": 1000
        }
        result = lambda_function._validate_single_mailbox(mailbox, 0)
        assert result["priority"] == 1000

    def test_negative_processing_limit(self):
        import lambda_function
        mailbox = {
            "mailboxName": "test",
            "mailboxType": "ops",
            "teamID": "team_001",
            "processingLimit": -10
        }
        result = lambda_function._validate_single_mailbox(mailbox, 0)
        assert result["processingLimit"] == -10


class TestValidateMailboxConfiguration:
    """Test cases for validate_mailbox_configuration function"""

    def test_valid_dict_with_mailboxes_key(self):
        import lambda_function
        config = {
            "mailboxes": [
                {
                    "mailboxName": "inbox1",
                    "mailboxType": "ops",
                    "teamID": "team_001"
                }
            ]
        }
        result = lambda_function.validate_mailbox_configuration(config)
        assert len(result) == 1
        assert result[0]["mailboxName"] == "inbox1"

    def test_valid_list_format(self):
        import lambda_function
        config = [
            {
                "mailboxName": "inbox1",
                "mailboxType": "ops",
                "teamID": "team_001"
            },
            {
                "mailboxName": "inbox2",
                "mailboxType": "claims",
                "teamID": "team_002"
            }
        ]
        result = lambda_function.validate_mailbox_configuration(config)
        assert len(result) == 2

    def test_valid_inboxes_key(self):
        import lambda_function
        config = {
            "inboxes": [
                {
                    "mailboxName": "test",
                    "mailboxType": "ops",
                    "teamID": "team_001"
                }
            ]
        }
        result = lambda_function.validate_mailbox_configuration(config)
        assert len(result) == 1

    def test_valid_boxes_key(self):
        import lambda_function
        config = {
            "boxes": [
                {
                    "mailboxName": "test",
                    "mailboxType": "ops",
                    "teamID": "team_001"
                }
            ]
        }
        result = lambda_function.validate_mailbox_configuration(config)
        assert len(result) == 1

    def test_valid_mailbox_list_key(self):
        import lambda_function
        config = {
            "mailbox_list": [
                {
                    "mailboxName": "test",
                    "mailboxType": "ops",
                    "teamID": "team_001"
                }
            ]
        }
        result = lambda_function.validate_mailbox_configuration(config)
        assert len(result) == 1

    def test_invalid_format_string(self):
        import lambda_function
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function.validate_mailbox_configuration("invalid")
        assert "EAWS009" in str(exc_info.value)

    def test_invalid_format_number(self):
        import lambda_function
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function.validate_mailbox_configuration(12345)
        assert "EAWS009" in str(exc_info.value)

    def test_invalid_format_none(self):
        import lambda_function
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function.validate_mailbox_configuration(None)
        assert "EAWS009" in str(exc_info.value)

    def test_empty_mailboxes_list(self):
        import lambda_function
        config = {"mailboxes": []}
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function.validate_mailbox_configuration(config)
        assert "EAWS010" in str(exc_info.value)

    def test_empty_inboxes_list(self):
        import lambda_function
        config = {"inboxes": []}
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function.validate_mailbox_configuration(config)
        assert "EAWS010" in str(exc_info.value)

    def test_empty_list(self):
        import lambda_function
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function.validate_mailbox_configuration([])
        assert "EAWS010" in str(exc_info.value)

    def test_dict_without_recognized_keys(self):
        import lambda_function
        config = {"unknown_key": [{"mailboxName": "test"}]}
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function.validate_mailbox_configuration(config)
        assert "EAWS010" in str(exc_info.value)

    def test_no_valid_mailboxes_after_validation(self):
        import lambda_function
        config = {
            "mailboxes": [
                {"mailboxName": "test"},
                {"mailboxType": "ops"}
            ]
        }
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function.validate_mailbox_configuration(config)
        assert "EAWS011" in str(exc_info.value)

    def test_mixed_valid_invalid_mailboxes(self):
        import lambda_function
        config = {
            "mailboxes": [
                {
                    "mailboxName": "valid1",
                    "mailboxType": "ops",
                    "teamID": "team_001"
                },
                {"mailboxName": "invalid"},
                {
                    "mailboxName": "valid2",
                    "mailboxType": "claims",
                    "teamID": "team_002"
                }
            ]
        }
        result = lambda_function.validate_mailbox_configuration(config)
        assert len(result) == 2
        assert result[0]["mailboxName"] == "valid1"
        assert result[1]["mailboxName"] == "valid2"

    def test_many_invalid_mailboxes(self):
        import lambda_function
        config = {
            "mailboxes": [
                {"mailboxType": "ops"},
                {"teamID": "team_001"},
                {"unknown": "field"}
            ]
        }
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function.validate_mailbox_configuration(config)
        assert "EAWS011" in str(exc_info.value)

    def test_mailboxes_key_with_none_value(self):
        import lambda_function
        config = {"mailboxes": None}
        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function.validate_mailbox_configuration(config)
        assert "EAWS010" in str(exc_info.value)


class TestFilterMailboxesByTeam:
    """Test cases for filter_mailboxes_by_team function"""

    @pytest.fixture
    def sample_mailboxes(self):
        return [
            {
                "mailboxName": "inbox1",
                "mailboxType": "ops",
                "teamID": "team_001"
            },
            {
                "mailboxName": "inbox2",
                "mailboxType": "claims",
                "teamID": "team_002"
            },
            {
                "mailboxName": "inbox3",
                "mailboxType": "ops",
                "teamID": "team_001"
            },
            {
                "mailboxName": "inbox4",
                "mailboxType": "claims",
                "teamID": "team_003"
            }
        ]

    def test_no_filter_returns_all_mailboxes(self, sample_mailboxes):
        import lambda_function
        result = lambda_function.filter_mailboxes_by_team(sample_mailboxes, None)
        assert len(result) == 4

    def test_no_team_id_filter_returns_all(self, sample_mailboxes):
        import lambda_function
        result = lambda_function.filter_mailboxes_by_team(sample_mailboxes, "NO_TEAM_ID")
        assert len(result) == 4

    def test_filter_by_team_id_single_result(self, sample_mailboxes):
        import lambda_function
        result = lambda_function.filter_mailboxes_by_team(sample_mailboxes, "team_002")
        assert len(result) == 1
        assert result[0]["mailboxName"] == "inbox2"

    def test_filter_by_team_id_multiple_results(self, sample_mailboxes):
        import lambda_function
        result = lambda_function.filter_mailboxes_by_team(sample_mailboxes, "team_001")
        assert len(result) == 2
        assert result[0]["mailboxName"] == "inbox1"
        assert result[1]["mailboxName"] == "inbox3"

    def test_filter_returns_empty_when_no_match(self, sample_mailboxes):
        import lambda_function
        result = lambda_function.filter_mailboxes_by_team(sample_mailboxes, "team_nonexistent")
        assert len(result) == 0

    def test_filter_with_empty_list(self):
        import lambda_function
        result = lambda_function.filter_mailboxes_by_team([], "team_001")
        assert len(result) == 0

    def test_filter_with_empty_string(self, sample_mailboxes):
        import lambda_function
        result = lambda_function.filter_mailboxes_by_team(sample_mailboxes, "")
        assert len(result) == 4

    def test_filter_case_sensitive(self, sample_mailboxes):
        import lambda_function
        result = lambda_function.filter_mailboxes_by_team(sample_mailboxes, "Team_001")
        assert len(result) == 0


class TestSortMailboxesByPriority:
    """Test cases for sort_mailboxes_by_priority function"""

    def test_sort_by_priority_ascending(self):
        import lambda_function
        mailboxes = [
            {"mailboxName": "inbox1", "priority": 5},
            {"mailboxName": "inbox2", "priority": 2},
            {"mailboxName": "inbox3", "priority": 8}
        ]
        result = lambda_function.sort_mailboxes_by_priority(mailboxes)
        priorities = [m["priority"] for m in result]
        assert priorities == [2, 5, 8]

    def test_sort_by_name_when_priority_equal(self):
        import lambda_function
        mailboxes = [
            {"mailboxName": "zulu", "priority": 5},
            {"mailboxName": "alpha", "priority": 5},
            {"mailboxName": "bravo", "priority": 5}
        ]
        result = lambda_function.sort_mailboxes_by_priority(mailboxes)
        names = [m["mailboxName"] for m in result]
        assert names == ["alpha", "bravo", "zulu"]

    def test_sort_with_default_priority(self):
        import lambda_function
        mailboxes = [
            {"mailboxName": "inbox1"},
            {"mailboxName": "inbox2", "priority": 3},
            {"mailboxName": "inbox3", "priority": 7}
        ]
        result = lambda_function.sort_mailboxes_by_priority(mailboxes)
        names = [m["mailboxName"] for m in result]
        assert names == ["inbox2", "inbox1", "inbox3"]

    def test_single_mailbox(self):
        import lambda_function
        mailboxes = [{"mailboxName": "inbox1", "priority": 5}]
        result = lambda_function.sort_mailboxes_by_priority(mailboxes)
        assert len(result) == 1
        assert result[0]["mailboxName"] == "inbox1"

    def test_empty_list(self):
        import lambda_function
        result = lambda_function.sort_mailboxes_by_priority([])
        assert len(result) == 0

    def test_sort_with_zero_priority(self):
        import lambda_function
        mailboxes = [
            {"mailboxName": "inbox1", "priority": 0},
            {"mailboxName": "inbox2", "priority": 5}
        ]
        result = lambda_function.sort_mailboxes_by_priority(mailboxes)
        priorities = [m["priority"] for m in result]
        assert priorities == [0, 5]

    def test_sort_with_negative_priority(self):
        import lambda_function
        mailboxes = [
            {"mailboxName": "inbox1", "priority": -1},
            {"mailboxName": "inbox2", "priority": 0},
            {"mailboxName": "inbox3", "priority": 5}
        ]
        result = lambda_function.sort_mailboxes_by_priority(mailboxes)
        priorities = [m["priority"] for m in result]
        assert priorities == [-1, 0, 5]

    def test_sort_stability_secondary_key(self):
        import lambda_function
        mailboxes = [
            {"mailboxName": "charlie", "priority": 5},
            {"mailboxName": "alpha", "priority": 5},
            {"mailboxName": "bravo", "priority": 3},
            {"mailboxName": "delta", "priority": 3}
        ]
        result = lambda_function.sort_mailboxes_by_priority(mailboxes)
        names = [m["mailboxName"] for m in result]
        assert names == ["bravo", "delta", "alpha", "charlie"]


class TestPrepareMailboxListOutput:
    """Test cases for prepare_mailbox_list_output function"""

    @pytest.fixture
    def sample_mailboxes(self):
        return [
            {
                "mailboxName": "ops1",
                "mailboxType": "ops",
                "teamID": "team_001",
                "isActive": True,
                "priority": 3
            },
            {
                "mailboxName": "claims1",
                "mailboxType": "claims",
                "teamID": "team_002",
                "isActive": False,
                "priority": 5
            },
            {
                "mailboxName": "ops2",
                "mailboxType": "ops",
                "teamID": "team_001",
                "isActive": True,
                "priority": 7
            }
        ]

    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_output_structure(self, sample_mailboxes):
        import lambda_function
        output = lambda_function.prepare_mailbox_list_output(
            sample_mailboxes,
            "corr-123",
            "my-bucket"
        )
        assert "status" in output
        assert "correlation_id" in output
        assert "summary" in output
        assert "mailboxes" in output
        assert "metadata" in output
        assert "function_name" in output
        assert "timestamp" in output

    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_summary_calculations(self, sample_mailboxes):
        import lambda_function
        output = lambda_function.prepare_mailbox_list_output(
            sample_mailboxes,
            "corr-123",
            "my-bucket"
        )
        summary = output["summary"]
        assert summary["total_mailboxes"] == 3
        assert summary["ops_mailboxes"] == 2
        assert summary["claims_mailboxes"] == 1
        assert summary["active_mailboxes"] == 2
        assert summary["average_priority"] == pytest.approx(5.0)

    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_status_is_success(self, sample_mailboxes):
        import lambda_function
        output = lambda_function.prepare_mailbox_list_output(
            sample_mailboxes,
            "corr-123",
            "my-bucket"
        )
        assert output["status"] == "success"

    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_correlation_id_matches(self, sample_mailboxes):
        import lambda_function
        output = lambda_function.prepare_mailbox_list_output(
            sample_mailboxes,
            "corr-456",
            "my-bucket"
        )
        assert output["correlation_id"] == "corr-456"

    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_empty_mailboxes_list(self):
        import lambda_function
        output = lambda_function.prepare_mailbox_list_output(
            [],
            "corr-123",
            "my-bucket"
        )
        assert output["summary"]["total_mailboxes"] == 0
        assert output["summary"]["ops_mailboxes"] == 0
        assert output["summary"]["claims_mailboxes"] == 0
        assert output["summary"]["active_mailboxes"] == 0
        assert output["summary"]["average_priority"] == 0

    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_metadata_contains_s3_info(self, sample_mailboxes):
        import lambda_function
        output = lambda_function.prepare_mailbox_list_output(
            sample_mailboxes,
            "corr-123",
            "my-bucket"
        )
        assert output["metadata"]["s3_bucket_name"] == "my-bucket"
        assert output["metadata"]["max_processing_limit"] == 100

    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_mailboxes_included(self, sample_mailboxes):
        import lambda_function
        output = lambda_function.prepare_mailbox_list_output(
            sample_mailboxes,
            "corr-123",
            "my-bucket"
        )
        assert len(output["mailboxes"]) == 3
        assert output["mailboxes"] == sample_mailboxes

    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_single_mailbox(self):
        import lambda_function
        mailboxes = [
            {
                "mailboxName": "single",
                "mailboxType": "ops",
                "teamID": "team_001",
                "isActive": True,
                "priority": 5
            }
        ]
        output = lambda_function.prepare_mailbox_list_output(
            mailboxes,
            "corr-123",
            "my-bucket"
        )
        assert output["summary"]["total_mailboxes"] == 1
        assert output["summary"]["average_priority"] == 5


class TestGetMailboxConfiguration:
    """Test cases for get_mailbox_configuration function"""

    @patch('lambda_function.download_json_from_s3')
    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_successful_retrieval(self, mock_download):
        import lambda_function
        mock_config = {"mailboxes": [{"mailboxName": "test"}]}
        mock_download.return_value = mock_config

        result = lambda_function.get_mailbox_configuration("my-bucket", "corr-123")
        assert result == mock_config
        mock_download.assert_called_once()

    @patch('lambda_function.download_json_from_s3')
    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_empty_configuration_raises_exception(self, mock_download):
        import lambda_function
        mock_download.return_value = None

        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function.get_mailbox_configuration("my-bucket", "corr-123")
        assert "EAWS008" in str(exc_info.value)

    @patch('lambda_function.download_json_from_s3')
    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_download_error_raises_exception(self, mock_download):
        import lambda_function
        mock_download.side_effect = Exception("S3 Error")

        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function.get_mailbox_configuration("my-bucket", "corr-123")
        assert "EAWS008" in str(exc_info.value)

    @patch('lambda_function.download_json_from_s3')
    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_with_team_id(self, mock_download):
        import lambda_function
        mock_config = {"mailboxes": []}
        mock_download.return_value = mock_config

        lambda_function.get_mailbox_configuration("my-bucket", "corr-123", "team_001")
        mock_download.assert_called_once()
        call_args = mock_download.call_args
        assert call_args.kwargs["team_id"] == "team_001"

    @patch('lambda_function.download_json_from_s3')
    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_empty_dict_configuration(self, mock_download):
        import lambda_function
        mock_download.return_value = {}

        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function.get_mailbox_configuration("my-bucket", "corr-123")
        assert "EAWS008" in str(exc_info.value)


class TestLambdaHandler:
    """Test cases for lambda_handler function"""

    @patch('lambda_function.handle_exception')
    @patch('lambda_function.set_extra_log_attributes')
    def test_missing_s3_bucket_raises_exception(self, mock_set_attrs, mock_handle):
        import lambda_function
        event = {
            'correlation_id': 'corr-123',
            'team_id': 'team_001'
        }

        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function.lambda_handler(event)
        assert "EAWS014" in str(exc_info.value)

    @patch('lambda_function.handle_exception')
    @patch('lambda_function.set_extra_log_attributes')
    @patch('lambda_function.get_mailbox_configuration')
    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_successful_execution(self, mock_get_config, mock_set_attrs, mock_handle):
        import lambda_function
        mock_get_config.return_value = {
            "mailboxes": [
                {
                    "mailboxName": "inbox1",
                    "mailboxType": "ops",
                    "teamID": "team_001"
                }
            ]
        }

        event = {
            'correlation_id': 'corr-123',
            'team_id': 'team_001',
            's3_bucket_name': 'my-bucket'
        }

        result = lambda_function.lambda_handler(event)
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['status'] == 'success'
        assert body['correlation_id'] == 'corr-123'

    @patch('lambda_function.handle_exception')
    @patch('lambda_function.set_extra_log_attributes')
    @patch('lambda_function.get_mailbox_configuration')
    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_system_exception_is_raised(self, mock_get_config, mock_set_attrs, mock_handle):
        import lambda_function
        mock_get_config.side_effect = lambda_function.SystemException("EAWS008: Test error")

        event = {
            'correlation_id': 'corr-123',
            'team_id': 'team_001',
            's3_bucket_name': 'my-bucket'
        }

        with pytest.raises(lambda_function.SystemException):
            lambda_function.lambda_handler(event)

    @patch('lambda_function.handle_exception')
    @patch('lambda_function.set_extra_log_attributes')
    @patch('lambda_function.get_mailbox_configuration')
    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_unexpected_exception_calls_handler(self, mock_get_config, mock_set_attrs, mock_handle):
        import lambda_function
        mock_get_config.side_effect = ValueError("Unexpected error")

        event = {
            'correlation_id': 'corr-123',
            'team_id': 'team_001',
            's3_bucket_name': 'my-bucket'
        }

        try:
            lambda_function.lambda_handler(event)
        except:
            pass

        mock_handle.assert_called_once()

    @patch('lambda_function.handle_exception')
    @patch('lambda_function.set_extra_log_attributes')
    @patch('lambda_function.get_mailbox_configuration')
    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_default_values_for_missing_event_fields(self, mock_get_config, mock_set_attrs, mock_handle):
        import lambda_function
        mock_get_config.return_value = {
            "mailboxes": [
                {
                    "mailboxName": "inbox1",
                    "mailboxType": "ops",
                    "teamID": "team_001"
                }
            ]
        }

        event = {'s3_bucket_name': 'my-bucket'}
        result = lambda_function.lambda_handler(event)
        body = json.loads(result['body'])
        assert body['status'] == 'success'

    @patch('lambda_function.handle_exception')
    @patch('lambda_function.set_extra_log_attributes')
    @patch('lambda_function.get_mailbox_configuration')
    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_response_timestamp_format(self, mock_get_config, mock_set_attrs, mock_handle):
        import lambda_function
        mock_get_config.return_value = {"mailboxes": []}

        event = {'s3_bucket_name': 'my-bucket'}
        result = lambda_function.lambda_handler(event)
        body = json.loads(result['body'])
        assert body['timestamp'].endswith('Z')

    @patch('lambda_function.handle_exception')
    @patch('lambda_function.set_extra_log_attributes')
    @patch('lambda_function.get_mailbox_configuration')
    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_filter_by_team_in_handler(self, mock_get_config, mock_set_attrs, mock_handle):
        import lambda_function
        mock_get_config.return_value = {
            "mailboxes": [
                {
                    "mailboxName": "inbox1",
                    "mailboxType": "ops",
                    "teamID": "team_001"
                },
                {
                    "mailboxName": "inbox2",
                    "mailboxType": "claims",
                    "teamID": "team_002"
                }
            ]
        }

        event = {
            'correlation_id': 'corr-123',
            'team_id': 'team_001',
            's3_bucket_name': 'my-bucket'
        }

        result = lambda_function.lambda_handler(event)
        body = json.loads(result['body'])
        assert len(body['mailboxes']) == 1
        assert body['mailboxes'][0]['teamID'] == 'team_001'

    @patch('lambda_function.handle_exception')
    @patch('lambda_function.set_extra_log_attributes')
    @patch('lambda_function.get_mailbox_configuration')
    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_mailboxes_sorted_by_priority(self, mock_get_config, mock_set_attrs, mock_handle):
        import lambda_function
        mock_get_config.return_value = {
            "mailboxes": [
                {
                    "mailboxName": "inbox1",
                    "mailboxType": "ops",
                    "teamID": "team_001",
                    "priority": 5
                },
                {
                    "mailboxName": "inbox2",
                    "mailboxType": "claims",
                    "teamID": "team_001",
                    "priority": 2
                }
            ]
        }

        event = {
            'team_id': 'team_001',
            's3_bucket_name': 'my-bucket'
        }

        result = lambda_function.lambda_handler(event)
        body = json.loads(result['body'])
        assert body['mailboxes'][0]['priority'] == 2
        assert body['mailboxes'][1]['priority'] == 5

    @patch('lambda_function.handle_exception')
    @patch('lambda_function.set_extra_log_attributes')
    @patch('lambda_function.get_mailbox_configuration')
    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_empty_s3_string_raises_exception(self, mock_get_config, mock_set_attrs, mock_handle):
        import lambda_function
        event = {
            's3_bucket_name': ''
        }

        with pytest.raises(lambda_function.SystemException) as exc_info:
            lambda_function.lambda_handler(event)
        assert "EAWS014" in str(exc_info.value)

    @patch('lambda_function.handle_exception')
    @patch('lambda_function.set_extra_log_attributes')
    @patch('lambda_function.get_mailbox_configuration')
    @patch('lambda_function.uki_constants', {'mail_box_file_path': 'config/mailboxes.json'})
    def test_response_includes_metadata(self, mock_get_config, mock_set_attrs, mock_handle):
        import lambda_function
        mock_get_config.return_value = {
            "mailboxes": [
                {
                    "mailboxName": "inbox1",
                    "mailboxType": "ops",
                    "teamID": "team_001"
                }
            ]
        }

        event = {'s3_bucket_name': 'my-bucket'}
        result = lambda_function.lambda_handler(event)
        body = json.loads(result['body'])
        assert "metadata" in body
        assert body["metadata"]["s3_bucket_name"] == "my-bucket"