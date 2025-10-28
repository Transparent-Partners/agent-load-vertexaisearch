#!/usr/bin/env python3
"""
Test the Vertex AI Search functionality by performing a search query.
This script validates that the setup is working correctly.
"""

import sys
from google.api_core import exceptions as gcp_exceptions
from google.cloud import discoveryengine_v1 as discoveryengine
from config import (
    PROJECT_ID, LOCATION, ENGINE_ID, COLLECTION_ID,
    get_search_client, get_collection_path,
    print_status, print_error, print_success
)

def check_engine_exists():
    """Check if the required engine exists."""
    try:
        from config import get_engine_client
        client = get_engine_client()
        engine_path = f"{get_collection_path()}/engines/{ENGINE_ID}"
        client.get_engine(name=engine_path)
        return True
    except gcp_exceptions.NotFound:
        print_error(f"Engine '{ENGINE_ID}' not found. Please run 2_create_engine.py first.")
        return False
    except Exception as e:
        print_error(f"Error checking engine existence: {e}")
        return False

def perform_search(query, max_results=5):
    """Perform a search query against the engine."""
    print_status("Initializing Search client...")
    client = get_search_client()
    
    # Check if engine exists first
    if not check_engine_exists():
        sys.exit(1)
    
    # Prepare the search request
    serving_config = f"{get_collection_path()}/engines/{ENGINE_ID}/servingConfigs/default_config"
    
    search_request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=max_results,
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
        ),
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO,
        ),
    )
    
    try:
        print_status(f"Performing search query: '{query}'")
        print_status(f"Serving config: {serving_config}")
        
        # Execute the search
        response = client.search(request=search_request)
        
        print_success(f"Search completed! Found {len(response.results)} results")
        
        # Display results
        if response.results:
            print_status("\n--- Search Results ---")
            for i, result in enumerate(response.results, 1):
                print_status(f"\nResult {i}:")
                print_status(f"  Title: {result.document.derived_struct_data.get('title', 'No title')}")
                print_status(f"  URI: {result.document.derived_struct_data.get('uri', 'No URI')}")
                
                # Extract snippet if available
                snippet = ""
                if hasattr(result, 'document') and hasattr(result.document, 'derived_struct_data'):
                    snippet_data = result.document.derived_struct_data
                    if 'snippets' in snippet_data:
                        snippets = snippet_data['snippets']
                        if snippets and len(snippets) > 0:
                            snippet = snippets[0].get('snippet', '')
                    elif 'extractive_segments' in snippet_data:
                        segments = snippet_data['extractive_segments']
                        if segments and len(segments) > 0:
                            snippet = segments[0].get('content', '')
                
                if snippet:
                    # Truncate long snippets
                    if len(snippet) > 200:
                        snippet = snippet[:200] + "..."
                    print_status(f"  Snippet: {snippet}")
                else:
                    print_status("  Snippet: No snippet available")
        else:
            print_status("No results found. This could mean:")
            print_status("1. The Google Drive folder is empty or has no supported file types")
            print_status("2. The sync hasn't completed yet (check the console)")
            print_status("3. The search query doesn't match any content")
        
        return response
        
    except Exception as e:
        print_error(f"Search failed: {e}")
        sys.exit(1)

def interactive_search():
    """Run interactive search mode."""
    print_status("Starting interactive search mode...")
    print_status("Type 'quit' or 'exit' to stop")
    
    while True:
        try:
            query = input("\nEnter search query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print_status("Exiting...")
                break
                
            if not query:
                print_error("Please enter a search query")
                continue
                
            perform_search(query)
            
        except KeyboardInterrupt:
            print_status("\nExiting...")
            break
        except EOFError:
            print_status("\nExiting...")
            break

def main():
    """Main function."""
    print_status("Starting Vertex AI Search test...")
    print_status(f"Project: {PROJECT_ID}")
    print_status(f"Location: {LOCATION}")
    print_status(f"Engine ID: {ENGINE_ID}")
    
    try:
        # Check if engine exists
        if not check_engine_exists():
            sys.exit(1)
        
        # Perform a test search
        test_query = "test"
        print_status(f"Performing test search with query: '{test_query}'")
        perform_search(test_query)
        
        # Ask if user wants to continue with interactive search
        print_status("\nTest search completed!")
        response = input("Would you like to continue with interactive search? (y/n): ").strip().lower()
        
        if response in ['y', 'yes']:
            interactive_search()
        else:
            print_success("Search test completed successfully!")
        
    except KeyboardInterrupt:
        print_error("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
