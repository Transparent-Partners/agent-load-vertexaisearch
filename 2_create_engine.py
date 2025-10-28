#!/usr/bin/env python3
"""
Create a Vertex AI Search engine (app).
This script is idempotent - it will skip creation if the engine already exists.
"""

import sys
from google.api_core import exceptions as gcp_exceptions
from google.cloud import discoveryengine_v1 as discoveryengine
from config import (
    PROJECT_ID, LOCATION, ENGINE_ID, DATA_STORE_ID, COLLECTION_ID,
    get_engine_client, get_collection_path, get_data_store_path,
    print_status, print_error, print_success
)

def check_engine_exists(client, engine_path):
    """Check if the engine already exists."""
    try:
        client.get_engine(name=engine_path)
        return True
    except gcp_exceptions.NotFound:
        return False
    except Exception as e:
        print_error(f"Error checking engine existence: {e}")
        return False

def check_data_store_exists():
    """Check if the required data store exists."""
    try:
        from config import get_data_store_client
        ds_client = get_data_store_client()
        ds_client.get_data_store(name=get_data_store_path())
        return True
    except gcp_exceptions.NotFound:
        print_error(f"Data store '{DATA_STORE_ID}' not found. Please run 1_create_data_store.py first.")
        return False
    except Exception as e:
        print_error(f"Error checking data store existence: {e}")
        return False

def create_engine():
    """Create the engine if it doesn't exist."""
    print_status("Initializing Discovery Engine client...")
    client = get_engine_client()
    
    # Check if data store exists first
    if not check_data_store_exists():
        sys.exit(1)
    
    # Check if engine already exists
    engine_path = f"{get_collection_path()}/engines/{ENGINE_ID}"
    print_status(f"Checking if engine '{ENGINE_ID}' already exists...")
    
    if check_engine_exists(client, engine_path):
        print_success(f"Engine '{ENGINE_ID}' already exists at: {engine_path}")
        return engine_path
    
    print_status(f"Creating engine '{ENGINE_ID}'...")
    
    # Create the engine
    parent = get_collection_path()
    engine = discoveryengine.Engine(
        display_name=ENGINE_ID,
        industry_vertical=discoveryengine.IndustryVertical.GENERIC,
        solution_type=discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH,
        search_engine_config=discoveryengine.Engine.SearchEngineConfig(
            search_tier=discoveryengine.SearchTier.SEARCH_TIER_ENTERPRISE,
            search_add_ons=[discoveryengine.SearchAddOn.SEARCH_ADD_ON_LLM],
        ),
        data_store_ids=[DATA_STORE_ID],
    )
    
    try:
        operation = client.create_engine(
            request=discoveryengine.CreateEngineRequest(
                parent=parent,
                engine=engine,
                engine_id=ENGINE_ID
            )
        )
        
        print_status(f"Engine creation operation started: {operation.operation.name}")
        print_status("Waiting for operation to complete...")
        
        # Wait for the operation to complete
        result = operation.result()
        print_success(f"Engine created successfully: {result.name}")
        return result.name
        
    except Exception as e:
        print_error(f"Failed to create engine: {e}")
        sys.exit(1)

def main():
    """Main function."""
    print_status("Starting Vertex AI Search engine creation...")
    print_status(f"Project: {PROJECT_ID}")
    print_status(f"Location: {LOCATION}")
    print_status(f"Engine ID: {ENGINE_ID}")
    print_status(f"Data Store ID: {DATA_STORE_ID}")
    
    try:
        engine_path = create_engine()
        print_success("Engine setup completed successfully!")
        print_status(f"Engine path: {engine_path}")
        
    except KeyboardInterrupt:
        print_error("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
