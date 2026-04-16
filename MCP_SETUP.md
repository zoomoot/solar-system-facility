# 🤖 MCP Server Setup Guide

## What is This?

This MCP (Model Context Protocol) server allows AI assistants to **directly interact** with the Solar System Small Bodies Explorer backend. Instead of just building the application for humans to use, AI assistants can now query the data, analyze objects, and explore the solar system programmatically!

## 🎯 What Can AI Do With This?

With the MCP server, AI assistants can:
- ✅ Search for small solar system bodies
- ✅ Get detailed object information
- ✅ Analyze completeness statistics
- ✅ Find under-researched targets
- ✅ Analyze NEOs for planetary defense
- ✅ Find objects missing specific properties

## 📦 Installation

### 1. No Installation Required!

The MCP server (`mcp_server_simple.py`) uses only standard Python libraries that are already installed:
- `json` - JSON parsing
- `requests` - HTTP requests (already installed for Flask backend)
- `sys` - Standard I/O

### 2. Verify Setup

```bash
cd /Users/gwil/Cursor/Solar-System
python3 mcp_server_simple.py
# Server will wait for JSON-RPC requests on stdin
```

## 🚀 Running the MCP Server

### Method 1: Direct Execution

```bash
# Make sure Flask backend is running on port 5050
# Then start the MCP server:
python3 mcp_server_simple.py
```

### Method 2: Configure in Cursor/Claude Desktop

Add to your MCP configuration file (`~/Library/Application Support/Claude/claude_desktop_config.json` or similar):

```json
{
  "mcpServers": {
    "solar-system-explorer": {
      "command": "python3",
      "args": [
        "/Users/gwil/Cursor/Solar-System/mcp_server_simple.py"
      ],
      "env": {
        "PYTHONPATH": "/Users/gwil/Cursor/Solar-System"
      }
    }
  }
}
```

## 🔧 Available Tools

### 1. `search_objects`
Search for small solar system bodies

**Parameters:**
- `limit` (number): Number of objects to retrieve (10-500), default: 100
- `source` (string): Data source - "jpl" or "ssodnet", default: "jpl"

**Example:**
```json
{
  "limit": 100,
  "source": "jpl"
}
```

### 2. `get_object_details`
Get detailed information about a specific object

**Parameters:**
- `designation` (string, required): Object designation (e.g., "433" for Eros, "1" for Ceres)

**Example:**
```json
{
  "designation": "433"
}
```

### 3. `get_completeness_stats`
Get overall completeness statistics

**Parameters:** None

**Returns:**
- Total objects analyzed
- Property coverage percentages
- Priority distribution

### 4. `find_under_researched`
Find under-researched objects for observation

**Parameters:**
- `priority` (string): Minimum priority - "high", "medium", or "low", default: "medium"
- `limit` (number): Maximum results, default: 50

**Example:**
```json
{
  "priority": "high",
  "limit": 20
}
```

### 5. `analyze_neos`
Analyze Near-Earth Objects for planetary defense

**Parameters:**
- `limit` (number): Number of NEOs to analyze, default: 200

**Returns:**
- NEO statistics
- PHAs identified
- Missing critical properties
- High-priority targets

### 6. `find_objects_by_property`
Find objects missing specific properties

**Parameters:**
- `missing_property` (string): Property to filter by - "diameter", "albedo", "rot_per", "spec_B", "spec_T", "GM", "BV", "UB"
- `object_type` (string): Object type filter - "neo", "pha", "mba", or "all", default: "all"
- `limit` (number): Maximum results, default: 50

**Example:**
```json
{
  "missing_property": "spec_B",
  "object_type": "neo",
  "limit": 30
}
```

## 📊 Example Workflows

### Workflow 1: Find High-Priority NEO Targets

```
1. Call analyze_neos with limit=500
2. Review high-priority PHAs
3. Call find_under_researched with priority="high"
4. Get detailed info for top candidates
```

### Workflow 2: Spectroscopic Survey Planning

```
1. Call find_objects_by_property with missing_property="spec_B", object_type="neo"
2. Review list of NEOs without spectral classification
3. Export for telescope proposal
```

### Workflow 3: Data Quality Assessment

```
1. Call get_completeness_stats
2. Identify least-covered properties
3. Call find_objects_by_property for each gap
4. Generate observation campaign priorities
```

## 🔍 Testing the MCP Server

### Test 1: Basic Search

```python
# The AI assistant would call:
search_objects({"limit": 10, "source": "jpl"})
```

Expected output: List of 10 objects with completeness scores

### Test 2: Find Ceres

```python
get_object_details({"designation": "1"})
```

Expected output: Detailed information about (1) Ceres

### Test 3: Find Under-Researched PHAs

```python
find_under_researched({"priority": "high", "limit": 20})
```

Expected output: List of high-priority PHAs with missing properties

## 🛠️ Troubleshooting

### MCP Server Won't Start

**Problem:** `ImportError: No module named 'mcp'`

**Solution:**
```bash
source venv/bin/activate
pip install mcp
```

### Backend Connection Error

**Problem:** `Connection refused to localhost:5050`

**Solution:** Make sure Flask backend is running:
```bash
python app.py
```

### No Data Returned

**Problem:** Empty results from queries

**Solution:** 
1. Check Flask backend is running
2. Verify API endpoints work: `curl http://localhost:5050/api/objects/search?limit=10`
3. Check cache directory has data

## 🎓 How It Works

```
┌─────────────────┐
│   AI Assistant  │
│   (Claude/GPT)  │
└────────┬────────┘
         │ MCP Protocol
         ▼
┌─────────────────┐
│   MCP Server    │
│  (mcp_server.py)│
└────────┬────────┘
         │ HTTP Requests
         ▼
┌─────────────────┐
│  Flask Backend  │
│    (app.py)     │
└────────┬────────┘
         │ API Calls
         ▼
┌─────────────────┐
│  JPL SBDB API   │
│  SsODNet API    │
└─────────────────┘
```

## 🌟 Benefits

### For AI Assistants
- Direct access to solar system data
- Can analyze and explore autonomously
- Generate insights and recommendations
- Answer complex research questions

### For Users
- AI can help interpret data
- Automated analysis workflows
- Natural language queries
- Intelligent target selection

### For Research
- Rapid data exploration
- Systematic gap identification
- Automated prioritization
- Mission planning support

## 📚 Integration Examples

### Example 1: Ask AI to Find Targets

**User:** "Find me the top 10 NEOs that need spectroscopic observations"

**AI Uses:**
1. `find_objects_by_property({"missing_property": "spec_B", "object_type": "neo", "limit": 100})`
2. Analyzes results
3. Returns prioritized list with justifications

### Example 2: Data Quality Report

**User:** "Give me a report on data completeness for PHAs"

**AI Uses:**
1. `analyze_neos({"limit": 500})`
2. `get_completeness_stats()`
3. Generates comprehensive report

### Example 3: Mission Target Selection

**User:** "What are the best targets for a sample return mission?"

**AI Uses:**
1. `find_under_researched({"priority": "high"})`
2. Filters for accessible NEOs
3. `get_object_details()` for top candidates
4. Provides ranked recommendations

## 🚀 Next Steps

1. **Install MCP SDK**: `pip install mcp`
2. **Test the server**: Run `python mcp_server.py`
3. **Configure your AI client**: Add to MCP config
4. **Start exploring**: Ask AI to analyze solar system data!

## 📖 Additional Resources

- **MCP Documentation**: https://modelcontextprotocol.io/
- **Flask Backend**: See `app.py`
- **API Documentation**: See `README.md`
- **Example Queries**: See examples below

## 💡 Tips

- Keep Flask backend running while using MCP server
- Use specific designations for faster object lookups
- Start with small limits and increase as needed
- Combine multiple tool calls for complex analyses
- Cache is shared between web UI and MCP server

---

**Ready to let AI explore the solar system!** 🌌🤖

Run `pip install mcp` and then `python mcp_server.py` to get started!

