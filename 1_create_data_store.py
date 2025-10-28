#!/usr/bin/env python3
"""
Create a Vertex AI Search data store.
This script is idempotent - it will skip creation if the data store already exists.
"""

import sys
import time
from google.api_core import exceptions as gcp_exceptions
from google.cloud import discoveryengine_v1 as discoveryengine
from config import (
    PROJECT_ID, LOCATION, DATA_STORE_ID, COLLECTION_ID,
    get_data_store_client, get_collection_path,
    print_status, print_error, print_success
)

def check_data_store_exists(client, data_store_path):
    """Check if the data store already exists."""
    try:
        client.get_data_store(name=data_store_path)
        return True
    except gcp_exceptions.NotFound:
        return False
    except Exception as e:
        print_error(f"Error checking data store existence: {e}")
        return False

def create_data_store():
    """Create the data store if it doesn't exist."""
    print_status("Initializing Discovery Engine client...")
    client = get_data_store_client()
    
    # Check if data store already exists
    data_store_path = f"{get_collection_path()}/dataStores/{DATA_STORE_ID}"
    print_status(f"Checking if data store '{DATA_STORE_ID}' already exists...")
    
    if check_data_store_exists(client, data_store_path):
        print_success(f"Data store '{DATA_STORE_ID}' already exists at: {data_store_path}")
        return data_store_path
    
    print_status(f"Creating data store '{DATA_STORE_ID}'...")
    
    # Create the data store
    parent = get_collection_path()
    data_store = discoveryengine.DataStore(
        display_name=DATA_STORE_ID,
        industry_vertical=discoveryengine.IndustryVertical.GENERIC,
        solution_types=[discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH],
        content_config=discoveryengine.DataStore.ContentConfig.CONTENT_REQUIRED,
    )
    
    try:
        operation = client.create_data_store(
            request=discoveryengine.CreateDataStoreRequest(
                parent=parent,
                data_store_id=DATA_STORE_ID,
                data_store=data_store
            )
        )
        
        print_status(f"Data store creation operation started: {operation.operation.name}")
        print_status("Waiting for operation to complete...")
        
        # Wait for the operation to complete
        result = operation.result()
        print_success(f"Data store created successfully: {result.name}")
        return result.name
        
    except Exception as e:
        print_error(f"Failed to create data store: {e}")
        sys.exit(1)

def main():
    """Main function."""
    print_status("Starting Vertex AI Search data store creation...")
    print_status(f"Project: {PROJECT_ID}")
    print_status(f"Location: {LOCATION}")
    print_status(f"Data Store ID: {DATA_STORE_ID}")
    
    try:
        data_store_path = create_data_store()
        print_success("Data store setup completed successfully!")
        print_status(f"Data store path: {data_store_path}")
        
    except KeyboardInterrupt:
        print_error("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
