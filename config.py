"""
Configuration file for Vertex AI Search setup scripts.
Centralized configuration and client initialization functions.
"""

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine
from google.auth import default
from googleapiclient.discovery import build
import os
import logging

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, will use environment variables or defaults

# Configuration constants (supports environment variable override)
PROJECT_ID = os.getenv("VERTEX_AI_PROJECT_ID", "transparent-agent-dev")
LOCATION = os.getenv("LOCATION", "global")
DATA_STORE_ID = os.getenv("DATA_STORE_ID", "chr_project_agent_v2")
ENGINE_ID = os.getenv("ENGINE_ID", "chr_project_agent_app_v2")
FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "1WoXWc_PA19tc-PWmVtiKMXyFvV0BK3g3")

# Collection and branch names
COLLECTION_ID = "default_collection"
BRANCH_ID = "default_branch"

def get_data_store_client():
    """Initialize and return a DataStoreServiceClient."""
    client_options = None if LOCATION == "global" else ClientOptions(
        api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com"
    )
    return discoveryengine.DataStoreServiceClient(client_options=client_options)

def get_engine_client():
    """Initialize and return an EngineServiceClient."""
    client_options = None if LOCATION == "global" else ClientOptions(
        api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com"
    )
    return discoveryengine.EngineServiceClient(client_options=client_options)

def get_document_client():
    """Initialize and return a DocumentServiceClient."""
    client_options = None if LOCATION == "global" else ClientOptions(
        api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com"
    )
    return discoveryengine.DocumentServiceClient(client_options=client_options)

def get_search_client():
    """Initialize and return a SearchServiceClient."""
    client_options = None if LOCATION == "global" else ClientOptions(
        api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com"
    )
    return discoveryengine.SearchServiceClient(client_options=client_options)

def get_rest_client():
    """Initialize and return a REST API client for Discovery Engine."""
    credentials, _ = default()
    return build('discoveryengine', 'v1', credentials=credentials)

def get_collection_path():
    """Get the collection path for the project and location."""
    return f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/{COLLECTION_ID}"

def get_data_store_path():
    """Get the data store path."""
    return f"{get_collection_path()}/dataStores/{DATA_STORE_ID}"

def get_engine_path():
    """Get the engine path."""
    return f"{get_collection_path()}/engines/{ENGINE_ID}"

def get_branch_path():
    """Get the branch path for the data store."""
    return f"{get_data_store_path()}/branches/{BRANCH_ID}"

# Logging configuration
def setup_logging(log_file=None, log_level=logging.INFO):
    """
    Configure logging for the application.
    
    Args:
        log_file: Optional path to log file. If None, only logs to console.
        log_level: Logging level (default: INFO)
    """
    handlers = [logging.StreamHandler()]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=log_level,
        format='[%(levelname)s] %(message)s',
        handlers=handlers
    )

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

def print_status(message):
    """Print a status message with consistent formatting."""
    logger.info(message)

def print_error(message):
    """Print an error message with consistent formatting."""
    logger.error(message)

def print_success(message):
    """Print a success message with consistent formatting."""
    logger.info(f"✓ {message}")

# GCS Configuration for Drive sync
GCS_BUCKET_NAME = f"{PROJECT_ID}-vertex-ai-search-docs"
SYNC_STATE_FILE = "drive_sync_state.json"

def get_gcs_bucket_name():
    """Get the GCS bucket name for document storage."""
    return GCS_BUCKET_NAME

def get_sync_state_file():
    """Get the sync state file path."""
    return SYNC_STATE_FILE
