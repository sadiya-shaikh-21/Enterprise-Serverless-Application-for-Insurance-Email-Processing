"""
Inbox Lister Lambda - Lists and validates available mailboxes for email processing.
"""

import json
import os
from typing import Dict, List, Optional, Any
from aiaa_logging_utility import set_extra_log_attributes
from common_utils import download_json_from_s3
from common_error_utils import SystemException
from common_logging_utils import get_common_logger
from common_exception_handler import handle_exception
from uki_constants import uki_constants

function_name = os.path.basename(os.path.dirname(__file__))
correlation_id = "NO_CORRELATION_ID"
email_id = "NO_EMAIL_ID"
team_id = "NO_TEAM_ID"

extra_log_attributes = {
    'correlation_id': '%(correlation_id)s',
    'email_id': '%(email_id)s',
    'team_id': '%(team_id)s'
}

logger = get_common_logger(function_name=function_name, extra_log_attributes=extra_log_attributes)


def get_mailbox_configuration(
    s3_bucket_name: str,
    correlation_id: str,
    team_id: str = "NO_TEAM_ID"
) -> Dict[str, Any]:
    """
    Retrieve mailbox configuration from S3.
    
    Args:
        s3_bucket_name: Name of S3 bucket containing configuration
        correlation_id: Correlation ID for logging
        team_id: Team ID for logging
        
    Returns:
        Dictionary containing mailbox configuration
        
    Raises:
        SystemException: If configuration not found or invalid
    """
    try:
        logger.info(f"Retrieving mailbox configuration from S3 bucket: {s3_bucket_name}")
        
        # Download mailbox configuration file from S3
        config_file = uki_constants["mail_box_file_path"]
        mailbox_config = download_json_from_s3(
            s3_bucket_name=s3_bucket_name,
            full_file_name=config_file,
            correlation_id=correlation_id,
            email_id="NO_EMAIL_ID",  # No specific email for inbox listing
            team_id=team_id
        )
        
        if not mailbox_config:
            raise SystemException("EAWS008: Mailbox configuration not found in S3")
        
        logger.info(f"Successfully retrieved mailbox configuration")
        return mailbox_config
        
    except Exception as e:
        logger.exception(f"Error retrieving mailbox configuration: {e}")
        raise SystemException(f"EAWS008: Failed to retrieve mailbox configuration: {str(e)}")


def validate_mailbox_configuration(mailbox_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Validate mailbox configuration structure and content.
    
    Args:
        mailbox_config: Raw mailbox configuration from S3
        
    Returns:
        List of validated mailbox configurations
        
    Raises:
        SystemException: If configuration validation fails
    """
    try:
        logger.info("Validating mailbox configuration structure")
        
        # Check if configuration has required structure
        if not isinstance(mailbox_config, dict) and not isinstance(mailbox_config, list):
            raise SystemException("EAWS009: Invalid mailbox configuration format")
        
        mailboxes = []
        
        # Handle both list and dictionary formats
        if isinstance(mailbox_config, list):
            mailboxes = mailbox_config
        elif isinstance(mailbox_config, dict) and "mailboxes" in mailbox_config:
            mailboxes = mailbox_config["mailboxes"]
        else:
            # Try to extract from other possible keys
            for key in ["inboxes", "boxes", "mailbox_list"]:
                if key in mailbox_config:
                    mailboxes = mailbox_config[key]
                    break
        
        if not mailboxes:
            raise SystemException("EAWS010: No mailboxes found in configuration")
        
        # Validate each mailbox
        validated_mailboxes = []
        for idx, mailbox in enumerate(mailboxes):
            try:
                validated_mailbox = _validate_single_mailbox(mailbox, idx)
                validated_mailboxes.append(validated_mailbox)
            except SystemException as e:
                logger.warning(f"Skipping mailbox {idx}: {str(e)}")
                continue
        
        if not validated_mailboxes:
            raise SystemException("EAWS011: No valid mailboxes found after validation")
        
        logger.info(f"Found {len(validated_mailboxes)} valid mailboxes")
        return validated_mailboxes
        
    except Exception as e:
        logger.exception(f"Error validating mailbox configuration: {e}")
        raise SystemException(f"EAWS009: Mailbox configuration validation failed: {str(e)}")


def _validate_single_mailbox(mailbox: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Validate individual mailbox configuration.
    
    Args:
        mailbox: Single mailbox configuration
        index: Index of mailbox in list
        
    Returns:
        Validated mailbox configuration
        
    Raises:
        SystemException: If mailbox validation fails
    """
    required_fields = ["mailboxName", "mailboxType", "teamID"]
    
    # Check required fields
    missing_fields = []
    for field in required_fields:
        if field not in mailbox or not mailbox[field]:
            missing_fields.append(field)
    
    if missing_fields:
        raise SystemException(
            f"EAWS012: Mailbox {index} missing required fields: {', '.join(missing_fields)}"
        )
    
    # Validate mailbox type
    mailbox_type = mailbox["mailboxType"].lower()
    if mailbox_type not in ["ops", "claims"]:
        raise SystemException(
            f"EAWS015: Mailbox {mailbox['mailboxName']} has unsupported type: {mailbox_type}"
        )
    
    # Validate team ID format
    team_id = mailbox["teamID"]
    if not isinstance(team_id, str) or not team_id.startswith("team_"):
        logger.warning(f"Mailbox {mailbox['mailboxName']} has non-standard team ID: {team_id}")
    
    # Add default values for optional fields
    validated_mailbox = {
        "mailboxName": str(mailbox["mailboxName"]).strip(),
        "mailboxType": mailbox_type,
        "teamID": str(team_id).strip(),
        "isActive": mailbox.get("isActive", True),
        "priority": mailbox.get("priority", 5),  # Default priority 5 (medium)
        "processingLimit": mailbox.get("processingLimit", 75),  # Default 75 emails
        "retryCount": mailbox.get("retryCount", 3),
        "description": mailbox.get("description", ""),
        "category": mailbox.get("category", "default")
    }
    
    # Validate processing limit
    if validated_mailbox["processingLimit"] > 100:
        logger.warning(f"Mailbox {validated_mailbox['mailboxName']} has high processing limit: {validated_mailbox['processingLimit']}")
        validated_mailbox["processingLimit"] = min(validated_mailbox["processingLimit"], 100)
    
    return validated_mailbox


def filter_mailboxes_by_team(
    mailboxes: List[Dict[str, Any]],
    team_id_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Filter mailboxes by team ID if specified.
    
    Args:
        mailboxes: List of validated mailboxes
        team_id_filter: Optional team ID to filter by
        
    Returns:
        Filtered list of mailboxes
    """
    if not team_id_filter or team_id_filter == "NO_TEAM_ID":
        logger.info("No team filter specified, returning all mailboxes")
        return mailboxes
    
    logger.info(f"Filtering mailboxes for team: {team_id_filter}")
    
    filtered_mailboxes = [
        mailbox for mailbox in mailboxes 
        if mailbox["teamID"] == team_id_filter
    ]
    
    logger.info(f"Found {len(filtered_mailboxes)} mailboxes for team {team_id_filter}")
    return filtered_mailboxes


def sort_mailboxes_by_priority(mailboxes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort mailboxes by priority (lower number = higher priority).
    
    Args:
        mailboxes: List of mailboxes to sort
        
    Returns:
        Sorted list of mailboxes
    """
    # Sort by priority (ascending), then by mailbox name
    sorted_mailboxes = sorted(
        mailboxes,
        key=lambda x: (x.get("priority", 5), x["mailboxName"])
    )
    
    # Log priority distribution
    priority_counts = {}
    for mailbox in sorted_mailboxes:
        priority = mailbox.get("priority", 5)
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
    logger.info(f"Mailbox priority distribution: {priority_counts}")
    return sorted_mailboxes


def prepare_mailbox_list_output(
    mailboxes: List[Dict[str, Any]],
    correlation_id: str,
    s3_bucket_name: str
) -> Dict[str, Any]:
    """
    Prepare final output structure for mailbox list.
    
    Args:
        mailboxes: List of validated and filtered mailboxes
        correlation_id: Correlation ID for the operation
        s3_bucket_name: S3 bucket name
        
    Returns:
        Structured output with mailbox list
    """
    output = {
        "status": "success",
        "correlation_id": correlation_id,
        "function_name": function_name,
        "timestamp": None,  # Will be set by handler
        "summary": {
            "total_mailboxes": len(mailboxes),
            "ops_mailboxes": len([m for m in mailboxes if m["mailboxType"] == "ops"]),
            "claims_mailboxes": len([m for m in mailboxes if m["mailboxType"] == "claims"]),
            "active_mailboxes": len([m for m in mailboxes if m.get("isActive", True)]),
            "average_priority": sum(m.get("priority", 5) for m in mailboxes) / len(mailboxes) if mailboxes else 0
        },
        "mailboxes": mailboxes,
        "metadata": {
            "s3_bucket_name": s3_bucket_name,
            "config_file": uki_constants["mail_box_file_path"],
            "processing_limit_default": 75,
            "max_processing_limit": 100
        }
    }
    
    return output


def lambda_handler(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    """
    AWS Lambda handler for Inbox Lister.
    
    Args:
        event: Lambda event containing configuration
        context: Lambda context
        
    Returns:
        Dictionary with mailbox list and metadata
    """
    try:
        # Extract parameters from event
        correlation_id = event.get('correlation_id', 'NO_CORRELATION_ID')
        team_id = event.get('team_id', 'NO_TEAM_ID')
        s3_bucket_name = event.get('s3_bucket_name')
        
        # Set logging attributes
        set_extra_log_attributes({
            'correlation_id': correlation_id,
            'email_id': 'NO_EMAIL_ID',
            'team_id': team_id
        })
        
        logger.info(f"Inbox Lister Lambda started")
        logger.debug(f"Event data: {json.dumps(event, default=str)}")
        
        # Validate required parameters
        if not s3_bucket_name:
            raise SystemException("EAWS014: S3 Bucket Name Not Found")
        
        # Step 1: Get mailbox configuration from S3
        mailbox_config = get_mailbox_configuration(
            s3_bucket_name=s3_bucket_name,
            correlation_id=correlation_id,
            team_id=team_id
        )
        
        # Step 2: Validate configuration
        validated_mailboxes = validate_mailbox_configuration(mailbox_config)
        
        # Step 3: Filter by team if specified
        filtered_mailboxes = filter_mailboxes_by_team(validated_mailboxes, team_id)
        
        # Step 4: Sort by priority
        sorted_mailboxes = sort_mailboxes_by_priority(filtered_mailboxes)
        
        # Step 5: Prepare output
        output = prepare_mailbox_list_output(
            mailboxes=sorted_mailboxes,
            correlation_id=correlation_id,
            s3_bucket_name=s3_bucket_name
        )
        
        # Add timestamp
        import datetime
        output["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
        
        logger.info(f"Inbox Lister completed successfully. Found {len(sorted_mailboxes)} mailboxes")
        
        return {
            'statusCode': 200,
            'body': json.dumps(output, default=str)
        }
        
    except SystemException as sys_err:
        logger.exception(f"System Exception in Inbox Lister: {sys_err}")
        raise
        
    except Exception as err:
        logger.exception(f"Unexpected error in Inbox Lister: {err}")
        handle_exception(
            err=err,
            correlation_id=event.get('correlation_id', 'NO_CORRELATION_ID'),
            function_name=function_name,
            logger=logger,
            s3_bucket_name=event.get('s3_bucket_name', ''),
            email_id='NO_EMAIL_ID',
            team_id=event.get('team_id', 'NO_TEAM_ID')
        )