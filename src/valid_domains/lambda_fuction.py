"""
Valid Domains Lambda - Fetches and validates approved email domains for processing.
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from aiaa_logging_utility import set_extra_log_attributes
from common_db_utils import run_stored_procedure
from common_get_parameters_utils import get_all_parameters
from common_utils import upload_to_s3, download_json_from_s3
from common_error_utils import SystemException
from uki_constants import uki_constants
from common_logging_utils import get_common_logger
from common_exception_handler import handle_exception

function_name = os.path.basename(os.path.dirname(__file__))
correlation_id = "NO_CORRELATION_ID"
email_id = "NO_EMAIL_ID"

extra_log_attributes = {
    'correlation_id': '%(correlation_id)s',
    'email_id': '%(email_id)s'
}

logger = get_common_logger(function_name=function_name, extra_log_attributes=extra_log_attributes)


def get_parameters(correlation_id: str) -> Dict[str, Any]:
    """
    Get all parameters from AWS Parameter Store.
    
    Args:
        correlation_id: Correlation ID for logging
        
    Returns:
        Dictionary of parameters including S3 bucket name
        
    Raises:
        SystemException: If parameters cannot be retrieved
    """
    try:
        logger.info("Retrieving parameters from Parameter Store")
        
        parameters = get_all_parameters()
        
        if not parameters:
            raise SystemException("EAWS006: No Parameters Found.")
        
        logger.info(f"Successfully retrieved {len(parameters)} parameters")
        return parameters
        
    except Exception as e:
        logger.exception(f"Error retrieving parameters: {e}")
        raise SystemException(f"EAWS006: Failed to retrieve parameters: {str(e)}")


def load_mailbox_configuration(
    parameters: Dict[str, Any],
    correlation_id: str
) -> Dict[str, Any]:
    """
    Load mailbox configuration from S3.
    
    Args:
        parameters: Dictionary containing S3 configuration
        correlation_id: Correlation ID for logging
        
    Returns:
        Dictionary containing mailbox configuration
        
    Raises:
        SystemException: If configuration cannot be loaded
    """
    try:
        logger.info("Loading mailbox configuration from S3")
        
        s3_bucket_name = parameters.get("s3_bucket_name")
        if not s3_bucket_name:
            raise SystemException("EAWS014: S3 Bucket Name Not Found in parameters")
        
        # Download mailbox configuration from S3
        mailboxes = download_json_from_s3(
            s3_bucket_name=s3_bucket_name,
            full_file_name=uki_constants["mail_box_file_path"],
            correlation_id=correlation_id
        )
        
        parameters["inboxes"] = mailboxes
        logger.info(f"Successfully loaded mailbox configuration")
        
        return parameters
        
    except Exception as e:
        logger.exception(f"Error loading mailbox configuration: {e}")
        raise SystemException(f"EAWS008: Failed to load mailbox configuration: {str(e)}")


def save_configuration_to_s3(
    parameters: Dict[str, Any],
    correlation_id: str
) -> str:
    """
    Save compiled configuration to S3.
    
    Args:
        parameters: Complete configuration dictionary
        correlation_id: Correlation ID for logging
        
    Returns:
        S3 bucket name where configuration was saved
        
    Raises:
        SystemException: If configuration cannot be saved
    """
    try:
        logger.info("Saving configuration to S3")
        
        s3_bucket_name = parameters.get("s3_bucket_name")
        if not s3_bucket_name:
            raise SystemException("EAWS014: S3 Bucket Name Not Found")
        
        # Save parameters to S3 as config.json
        s3_file_path = uki_constants["config_json_file"]
        upload_to_s3(
            string_file_contents=json.dumps(parameters, default=str, indent=2),
            s3_bucket_name=s3_bucket_name,
            s3_file_path=s3_file_path,
            correlation_id=correlation_id
        )
        
        logger.info(f"Configuration saved to S3: s3://{s3_bucket_name}/{s3_file_path}")
        return s3_bucket_name
        
    except Exception as e:
        logger.exception(f"Error saving configuration to S3: {e}")
        raise SystemException(f"EAWS016: Failed to save configuration to S3: {str(e)}")


def fetch_valid_domains_from_database(
    parameters: Dict[str, Any],
    correlation_id: str
) -> Tuple[List[Tuple], Dict[str, int]]:
    """
    Fetch valid email domains from SQL Server database.
    
    Args:
        parameters: Configuration dictionary
        correlation_id: Correlation ID for logging
        
    Returns:
        Tuple of (rows, column_map) from database
        
    Raises:
        SystemException: If database query fails or no domains found
    """
    try:
        logger.info("Fetching valid domains from database")
        
        # Execute stored procedure to get approved email domains
        rows, column_map = run_stored_procedure(
            parameters=parameters,
            correlation_id=correlation_id,
            procedure_name="select_approved_emails_sp_name",
            column_required=["ID", "From", "Category"]
        )
        
        if not rows:
            raise SystemException("EAWS007: No Domains Found in DB.")
        
        logger.info(f"Successfully retrieved {len(rows)} domains from database")
        return rows, column_map
        
    except Exception as e:
        logger.exception(f"Error fetching domains from database: {e}")
        raise SystemException(f"EAWS007: Failed to fetch domains from database: {str(e)}")


def process_domain_data(
    rows: List[Tuple],
    column_map: Dict[str, int]
) -> List[Dict[str, Any]]:
    """
    Process raw database rows into structured domain data.
    
    Args:
        rows: Raw rows from database
        column_map: Mapping of column names to indices
        
    Returns:
        List of structured domain dictionaries
    """
    try:
        logger.info("Processing domain data")
        
        domains = []
        for row in rows:
            try:
                domain_entry = {
                    "id": str(row[column_map["ID"]]),
                    "from": str(row[column_map["From"]]).lower().strip(),
                    "category": str(row[column_map["Category"]]),
                    "is_active": True,
                    "validation_date": None  # Will be set later
                }
                domains.append(domain_entry)
            except (IndexError, KeyError) as e:
                logger.warning(f"Skipping invalid domain row: {row}, Error: {e}")
                continue
        
        logger.info(f"Processed {len(domains)} valid domain entries")
        return domains
        
    except Exception as e:
        logger.exception(f"Error processing domain data: {e}")
        raise SystemException(f"EAWS017: Failed to process domain data: {str(e)}")


def validate_and_filter_domains(
    domains: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Validate domain format and filter invalid entries.
    
    Args:
        domains: List of domain dictionaries
        
    Returns:
        Filtered list of valid domains
    """
    try:
        logger.info("Validating and filtering domains")
        
        valid_domains = []
        invalid_domains = []
        
        for domain in domains:
            email_from = domain.get("from", "")
            
            # Basic email format validation
            if not email_from or "@" not in email_from:
                invalid_domains.append(domain)
                logger.warning(f"Invalid domain format: {email_from}")
                continue
            
            # Extract domain part
            domain_part = email_from.split("@")[-1]
            
            # Validate domain format
            if not domain_part or "." not in domain_part:
                invalid_domains.append(domain)
                logger.warning(f"Invalid domain part: {domain_part}")
                continue
            
            # Add validated domain with additional metadata
            validated_domain = domain.copy()
            validated_domain["domain_part"] = domain_part
            validated_domain["is_valid_format"] = True
            validated_domain["validation_timestamp"] = None  # Will be set later
            
            valid_domains.append(validated_domain)
        
        if invalid_domains:
            logger.warning(f"Found {len(invalid_domains)} invalid domain formats")
            # Log invalid domains for manual review
            for invalid in invalid_domains:
                logger.debug(f"Invalid domain entry: {invalid}")
        
        logger.info(f"Validated {len(valid_domains)} domains, {len(invalid_domains)} invalid")
        return valid_domains
        
    except Exception as e:
        logger.exception(f"Error validating domains: {e}")
        raise SystemException(f"EAWS018: Failed to validate domains: {str(e)}")


def save_domains_to_s3(
    domains: List[Dict[str, Any]],
    s3_bucket_name: str,
    correlation_id: str
) -> None:
    """
    Save validated domains to S3.
    
    Args:
        domains: List of validated domain dictionaries
        s3_bucket_name: S3 bucket name
        correlation_id: Correlation ID for logging
        
    Raises:
        SystemException: If domains cannot be saved
    """
    try:
        logger.info("Saving validated domains to S3")
        
        if not domains:
            raise SystemException("EAWS007: No valid domains to save")
        
        # Create structured domains JSON
        domains_json = {
            "domains": domains,
            "metadata": {
                "total_domains": len(domains),
                "generated_at": None,  # Will be set later
                "correlation_id": correlation_id,
                "function_name": function_name,
                "version": "1.0"
            }
        }
        
        # Save to S3
        s3_file_path = uki_constants["domains_json_file"]
        upload_to_s3(
            string_file_contents=json.dumps(domains_json, default=str, indent=2),
            s3_bucket_name=s3_bucket_name,
            s3_file_path=s3_file_path,
            correlation_id=correlation_id
        )
        
        logger.info(f"Domains saved to S3: s3://{s3_bucket_name}/{s3_file_path}")
        
    except Exception as e:
        logger.exception(f"Error saving domains to S3: {e}")
        raise SystemException(f"EAWS019: Failed to save domains to S3: {str(e)}")


def prepare_final_response(
    domains: List[Dict[str, Any]],
    s3_bucket_name: str,
    correlation_id: str
) -> Dict[str, Any]:
    """
    Prepare final response for Lambda handler.
    
    Args:
        domains: List of validated domains
        s3_bucket_name: S3 bucket name
        correlation_id: Correlation ID
        
    Returns:
        Final response dictionary
    """
    import datetime
    
    response = {
        "status": "success",
        "correlation_id": correlation_id,
        "function_name": function_name,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "summary": {
            "total_domains": len(domains),
            "s3_bucket_name": s3_bucket_name,
            "domains_file": uki_constants["domains_json_file"],
            "config_file": uki_constants["config_json_file"]
        },
        "domain_categories": {},
        "top_domains": []
    }
    
    # Calculate domain categories
    categories = {}
    for domain in domains:
        category = domain.get("category", "uncategorized")
        categories[category] = categories.get(category, 0) + 1
    
    response["domain_categories"] = categories
    
    # Extract top domains (by frequency if available, otherwise sample)
    sample_size = min(10, len(domains))
    response["top_domains"] = [
        {
            "domain": domain["domain_part"],
            "category": domain["category"],
            "source": domain["from"]
        }
        for domain in domains[:sample_size]
    ]
    
    return response


def lambda_handler(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    """
    AWS Lambda handler for Valid Domains.
    
    Args:
        event: Lambda event containing correlation_id
        context: Lambda context
        
    Returns:
        Dictionary with validation results and metadata
    """
    try:
        # Extract correlation_id from event
        correlation_id = event.get('id') or event.get('correlation_id')
        if not correlation_id:
            raise SystemException("EAWS001: correlation_id should not be empty.")
        
        set_extra_log_attributes({
            'correlation_id': correlation_id,
            "email_id": "NO_EMAIL_ID"
        })
        
        logger.info(f"Valid Domains Lambda started")
        logger.info(f"Event data: {json.dumps(event, default=str)}")
        
        # Step 1: Get parameters from Parameter Store
        parameters = get_parameters(correlation_id)
        
        # Step 2: Load mailbox configuration from S3
        parameters = load_mailbox_configuration(parameters, correlation_id)
        
        # Step 3: Save complete configuration to S3
        s3_bucket_name = save_configuration_to_s3(parameters, correlation_id)
        
        # Step 4: Fetch valid domains from database
        rows, column_map = fetch_valid_domains_from_database(parameters, correlation_id)
        
        # Step 5: Process domain data
        domains = process_domain_data(rows, column_map)
        
        # Step 6: Validate and filter domains
        validated_domains = validate_and_filter_domains(domains)
        
        # Step 7: Save domains to S3
        save_domains_to_s3(validated_domains, s3_bucket_name, correlation_id)
        
        # Step 8: Prepare final response
        response = prepare_final_response(
            domains=validated_domains,
            s3_bucket_name=s3_bucket_name,
            correlation_id=correlation_id
        )
        
        logger.info(f"Valid Domains Lambda completed successfully")
        logger.info(f"Processed {len(validated_domains)} domains")
        
        return {
            "correlation_id": correlation_id,
            "s3_bucket_name": s3_bucket_name,
            "domain_count": len(validated_domains),
            "status": "success"
        }
        
    except SystemException as sys_err:
        logger.exception(f"System Exception in Valid Domains: {sys_err}")
        raise
        
    except Exception as err:
        # Use local correlation_id if it exists and is valid, otherwise extract from event
        if 'correlation_id' in locals() and correlation_id:
            safe_correlation_id = correlation_id
        else:
            safe_correlation_id = event.get('id', 'NO_CORRELATION_ID') if event else 'NO_CORRELATION_ID'
        
        handle_exception(
            err=err,
            correlation_id=safe_correlation_id,
            function_name=function_name,
            logger=logger,
            s3_bucket_name=parameters.get("s3_bucket_name") if 'parameters' in locals() and "s3_bucket_name" in parameters else "None",
            email_id=email_id
        )