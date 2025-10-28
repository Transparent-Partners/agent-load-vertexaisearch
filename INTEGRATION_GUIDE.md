# Vertex AI Search Integration Guide

## Overview

This guide provides everything external teams need to integrate with the Vertex AI Search instance for the CHR Project Agent.

---

## 🔑 Required Configuration

### **Essential IDs**

```yaml
Project ID:       transparent-agent-dev
Location:         global
Engine ID:        chr_project_agent_app_v2
Data Store ID:    chr_project_agent_v2
```

### **Serving Config Path** (Primary endpoint)

```
projects/transparent-agent-dev/locations/global/collections/default_collection/engines/chr_project_agent_app_v2/servingConfigs/default_config
```

---

## 💻 Integration Examples

### **Python Integration**

#### Install Dependencies
```bash
pip install google-cloud-discoveryengine
```

#### Basic Search Example
```python
from google.cloud import discoveryengine_v1 as discoveryengine

# Initialize the search client
client = discoveryengine.SearchServiceClient()

# Configure the serving config
serving_config = (
    "projects/transparent-agent-dev/locations/global/"
    "collections/default_collection/engines/chr_project_agent_app_v2/"
    "servingConfigs/default_config"
)

# Perform a search
def search_documents(query, page_size=10):
    """
    Search documents in Vertex AI Search.
    
    Args:
        query: Search query string
        page_size: Number of results to return (default: 10)
        
    Returns:
        SearchResponse object with results
    """
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=page_size,
        # Optional: Enable query expansion
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
        ),
        # Optional: Enable spell correction
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO,
        ),
    )
    
    response = client.search(request=request)
    return response

# Example usage
results = search_documents("Paytronix validation")

for i, result in enumerate(results.results, 1):
    print(f"\nResult {i}:")
    print(f"  Title: {result.document.derived_struct_data.get('title', 'No title')}")
    
    # Extract snippets if available
    snippets = result.document.derived_struct_data.get('snippets', [])
    if snippets:
        print(f"  Snippet: {snippets[0].get('snippet', 'No snippet')}")
```

#### Advanced Search with Filters
```python
def advanced_search(query, filters=None, order_by=None):
    """
    Perform advanced search with filters and sorting.
    
    Args:
        query: Search query string
        filters: Optional filter string (e.g., "mimeType:application/pdf")
        order_by: Optional sort order (e.g., "modifiedTime desc")
    """
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=20,
    )
    
    if filters:
        request.filter = filters
    if order_by:
        request.order_by = order_by
    
    response = client.search(request=request)
    return response
```

---

### **REST API Integration**

#### Using cURL
```bash
# Set your access token
ACCESS_TOKEN=$(gcloud auth print-access-token)

# Perform a search
curl -X POST \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  "https://discoveryengine.googleapis.com/v1/projects/transparent-agent-dev/locations/global/collections/default_collection/engines/chr_project_agent_app_v2/servingConfigs/default_config:search" \
  -d '{
    "query": "CHR tokenization pilot",
    "pageSize": 10
  }'
```

#### Using JavaScript/Node.js
```javascript
const {SearchServiceClient} = require('@google-cloud/discoveryengine').v1;

const client = new SearchServiceClient();

const servingConfig = 
  'projects/transparent-agent-dev/locations/global/' +
  'collections/default_collection/engines/chr_project_agent_app_v2/' +
  'servingConfigs/default_config';

async function searchDocuments(query) {
  const request = {
    servingConfig: servingConfig,
    query: query,
    pageSize: 10,
  };

  const response = await client.search(request);
  return response;
}

// Example usage
searchDocuments('Paytronix validation')
  .then(results => {
    results[0].results.forEach((result, i) => {
      console.log(`Result ${i + 1}:`);
      console.log(`  Title: ${result.document.derivedStructData.title}`);
    });
  });
```

---

## 🔐 Required IAM Permissions

### **For Service Accounts**

Grant the service account one of these roles:

**Option 1: Viewer Role (Recommended)**
```bash
gcloud projects add-iam-policy-binding transparent-agent-dev \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@project.iam.gserviceaccount.com" \
  --role="roles/discoveryengine.viewer"
```

**Option 2: Custom Role (Minimal Permissions)**
```bash
# Create custom role with only search permission
gcloud iam roles create vertexAISearchUser \
  --project=transparent-agent-dev \
  --title="Vertex AI Search User" \
  --description="Can perform searches only" \
  --permissions="discoveryengine.servingConfigs.search"

# Assign the custom role
gcloud projects add-iam-policy-binding transparent-agent-dev \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@project.iam.gserviceaccount.com" \
  --role="projects/transparent-agent-dev/roles/vertexAISearchUser"
```

### **For User Accounts**

```bash
gcloud projects add-iam-policy-binding transparent-agent-dev \
  --member="user:USER_EMAIL@domain.com" \
  --role="roles/discoveryengine.viewer"
```

### **Required Permission**

Minimum permission needed:
- `discoveryengine.servingConfigs.search`

---

## 📋 Quick Reference Card

```
═══════════════════════════════════════════════════════════
            VERTEX AI SEARCH - CHR PROJECT AGENT
═══════════════════════════════════════════════════════════

PROJECT:          transparent-agent-dev
LOCATION:         global
ENGINE:           chr_project_agent_app_v2
DATA STORE:       chr_project_agent_v2

SERVING CONFIG:   
projects/transparent-agent-dev/locations/global/
collections/default_collection/engines/chr_project_agent_app_v2/
servingConfigs/default_config

API ENDPOINT:     
https://discoveryengine.googleapis.com/v1/

PYTHON PACKAGE:   google-cloud-discoveryengine
VERSION:          v1

IAM ROLE:         roles/discoveryengine.viewer
MIN PERMISSION:   discoveryengine.servingConfigs.search

DOCUMENTATION:    
https://cloud.google.com/generative-ai-app-builder/docs/apis
═══════════════════════════════════════════════════════════
```

---

## 🔍 Search Features

### **Supported Features**

✅ Full-text search across documents  
✅ Natural language queries  
✅ Query expansion (automatic synonyms)  
✅ Spell correction  
✅ Relevance ranking  
✅ LLM-enhanced search  
✅ Enterprise-grade results  

### **Document Types Indexed**

- PDF documents
- Microsoft Word (.docx)
- Microsoft PowerPoint (.pptx)
- Google Docs (exported as PDF)
- Google Slides (exported as PDF)
- Plain text files

### **Current Data Set**

- **Source**: Google Drive Shared Folder (Project_Agent_Docs)
- **Documents**: ~17 files (as of last sync)
- **Topics**: CHR Project documentation, SOWs, reports, meeting summaries
- **Update Frequency**: On-demand sync (not real-time)

---

## 🚀 Getting Started Checklist

- [ ] Install required SDK (`google-cloud-discoveryengine`)
- [ ] Configure authentication (service account or user credentials)
- [ ] Request IAM permissions from admin
- [ ] Copy serving config path to your code
- [ ] Test basic search query
- [ ] Implement error handling
- [ ] Deploy to your application

---

## 💡 Best Practices

### **1. Error Handling**
```python
from google.api_core import exceptions

try:
    results = search_documents(query)
except exceptions.PermissionDenied:
    print("Access denied - check IAM permissions")
except exceptions.NotFound:
    print("Search endpoint not found - check serving config")
except Exception as e:
    print(f"Search error: {e}")
```

### **2. Result Pagination**
```python
def search_with_pagination(query, page_size=10):
    page_token = None
    all_results = []
    
    while True:
        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=page_size,
            page_token=page_token
        )
        
        response = client.search(request=request)
        all_results.extend(response.results)
        
        if not response.next_page_token:
            break
        page_token = response.next_page_token
    
    return all_results
```

### **3. Caching Results**
Consider caching search results for frequently-used queries to reduce API calls and improve performance.

### **4. Monitoring**
Track your search API usage in Google Cloud Console:
- Navigate to: Vertex AI Search → Data Stores → chr_project_agent_v2
- Check "Analytics" tab for search metrics

---

## 📞 Support & Contact

**For Integration Issues:**
- Check IAM permissions first
- Verify serving config path is correct
- Test with basic query before complex ones

**For Data Updates:**
- Documents sync from Google Drive on-demand
- Contact data store admin for sync requests
- Check `drive_sync_state.json` for last sync time

**Documentation:**
- API Reference: https://cloud.google.com/generative-ai-app-builder/docs/reference
- Python SDK: https://cloud.google.com/python/docs/reference/discoveryengine/latest

---

## 🔄 Version History

- **v1.0** (Oct 2025) - Initial setup with GCS-based sync
  - 17 documents indexed
  - Shared Drive support
  - Enterprise tier with LLM add-on

