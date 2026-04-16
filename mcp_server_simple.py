#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple MCP-Compatible Server for Solar System Small Bodies Explorer
Uses JSON-RPC 2.0 over stdio for MCP compatibility
"""

import json
import sys
import requests
from typing import Dict, List, Any

# Backend API configuration
BACKEND_URL = "http://localhost:5050"

# Tool definitions
TOOLS = [
    {
        "name": "search_objects",
        "description": "Search for small solar system bodies from JPL SBDB. Returns objects with completeness analysis and priority rankings.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Number of objects to retrieve (10-500)",
                    "default": 100
                },
                "source": {
                    "type": "string",
                    "enum": ["jpl", "ssodnet"],
                    "description": "Data source to query",
                    "default": "jpl"
                }
            }
        }
    },
    {
        "name": "get_object_details",
        "description": "Get detailed information about a specific solar system object by designation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "designation": {
                    "type": "string",
                    "description": "Object designation (e.g., '1' for Ceres, '433' for Eros)"
                }
            },
            "required": ["designation"]
        }
    },
    {
        "name": "get_completeness_stats",
        "description": "Get overall completeness statistics including property coverage and priority distribution",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "find_under_researched",
        "description": "Find under-researched objects that are high-priority targets for observation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "priority": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Minimum priority level",
                    "default": "medium"
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum results",
                    "default": 50
                }
            }
        }
    },
    {
        "name": "analyze_neos",
        "description": "Analyze Near-Earth Objects and identify those missing critical properties",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Number of NEOs to analyze",
                    "default": 200
                }
            }
        }
    }
]


def log(message: str):
    """Log to stderr (stdout is reserved for JSON-RPC)"""
    print(f"[MCP Server] {message}", file=sys.stderr, flush=True)


def search_objects(args: Dict) -> str:
    """Search for objects"""
    limit = args.get("limit", 100)
    source = args.get("source", "jpl")
    
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/objects/search",
            params={"limit": limit, "source": source},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        if not data.get("success"):
            return f"Error: {data.get('error', 'Unknown error')}"
        
        objects = data.get("objects", [])
        
        # Format summary
        result = f"Found {len(objects)} objects from {source.upper()}\n\n"
        
        # Statistics
        high_priority = sum(1 for obj in objects if obj.get('analysis', {}).get('research_priority') == 'high')
        avg_completeness = sum(obj.get('analysis', {}).get('completeness_score', 0) for obj in objects) / len(objects) if objects else 0
        
        result += f"Statistics:\n"
        result += f"  High Priority: {high_priority}\n"
        result += f"  Avg Completeness: {avg_completeness:.1f}%\n\n"
        
        # Sample objects
        result += "Sample Objects:\n"
        for i, obj in enumerate(objects[:10], 1):
            designation = obj.get('pdes', obj.get('spkid', 'Unknown'))
            name = obj.get('name', '-')
            neo = "NEO" if obj.get('neo') == 'Y' else "MBA"
            pha = " (PHA)" if obj.get('pha') == 'Y' else ""
            analysis = obj.get('analysis', {})
            completeness = analysis.get('completeness_score', 0)
            priority = analysis.get('research_priority', 'unknown')
            missing = ', '.join(analysis.get('missing_properties', [])[:3])
            
            result += f"{i:2d}. {designation:15s} {name:20s} {neo}{pha:6s} "
            result += f"{completeness:5.1f}% {priority:8s} Missing: {missing}\n"
        
        if len(objects) > 10:
            result += f"\n... and {len(objects) - 10} more\n"
        
        return result
        
    except Exception as e:
        return f"Error: {str(e)}"


def get_object_details(args: Dict) -> str:
    """Get details for specific object"""
    designation = args.get("designation")
    
    if not designation:
        return "Error: designation required"
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/objects/{designation}", timeout=30)
        response.raise_for_status()
        data = response.json()
        
        result = f"Object: {designation}\n" + "=" * 60 + "\n\n"
        
        if data.get('jpl') and 'object' in data['jpl']:
            obj = data['jpl']['object']
            result += f"Name: {obj.get('fullname', 'N/A')}\n"
            result += f"Type: {obj.get('kind', 'N/A')}\n"
            result += f"NEO: {obj.get('neo', 'N/A')}\n"
            result += f"PHA: {obj.get('pha', 'N/A')}\n\n"
        
        if data.get('jpl') and 'phys_par' in data['jpl']:
            result += "Physical Properties:\n"
            for param in data['jpl']['phys_par']:
                result += f"  {param.get('name')}: {param.get('value')} {param.get('units', '')}\n"
        
        return result
        
    except Exception as e:
        return f"Error: {str(e)}"


def get_completeness_stats(args: Dict) -> str:
    """Get completeness statistics"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/stats/completeness", timeout=30)
        response.raise_for_status()
        data = response.json()
        
        stats = data.get("stats", {})
        result = "Completeness Statistics\n" + "=" * 60 + "\n\n"
        result += f"Total Objects: {stats.get('total_objects', 0)}\n\n"
        
        result += "Property Coverage:\n"
        coverage = stats.get('property_coverage', {})
        total = stats.get('total_objects', 1)
        
        for prop, count in sorted(coverage.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total * 100) if total > 0 else 0
            result += f"  {prop:12s} {pct:5.1f}% ({count}/{total})\n"
        
        result += "\nPriority Distribution:\n"
        priority_dist = stats.get('priority_distribution', {})
        for priority in ['high', 'medium', 'low']:
            count = priority_dist.get(priority, 0)
            pct = (count / total * 100) if total > 0 else 0
            result += f"  {priority.capitalize():10s}: {count:4d} ({pct:5.1f}%)\n"
        
        return result
        
    except Exception as e:
        return f"Error: {str(e)}"


def find_under_researched(args: Dict) -> str:
    """Find under-researched objects"""
    priority = args.get("priority", "medium")
    limit = args.get("limit", 50)
    
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/under-researched",
            params={"priority": priority, "limit": limit},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        objects = data.get("objects", [])
        result = f"Under-Researched Objects (Priority: {priority}+)\n" + "=" * 80 + "\n\n"
        result += f"Found {len(objects)} objects\n\n"
        
        for i, obj in enumerate(objects[:20], 1):
            designation = obj.get('pdes', obj.get('spkid', 'Unknown'))
            name = obj.get('name', '-')[:18]
            neo = "NEO" if obj.get('neo') == 'Y' else "MBA"
            pha = " (PHA)" if obj.get('pha') == 'Y' else ""
            
            analysis = obj.get('analysis', {})
            priority_val = analysis.get('research_priority', 'unknown').upper()
            completeness = analysis.get('completeness_score', 0)
            missing = ', '.join(analysis.get('missing_properties', [])[:3])
            
            result += f"#{i:<3d} {designation:15s} {name:20s} {neo}{pha:6s} "
            result += f"{priority_val:8s} {completeness:5.1f}% Missing: {missing}\n"
        
        if len(objects) > 20:
            result += f"\n... and {len(objects) - 20} more\n"
        
        return result
        
    except Exception as e:
        return f"Error: {str(e)}"


def analyze_neos(args: Dict) -> str:
    """Analyze NEOs"""
    limit = args.get("limit", 200)
    
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/objects/search",
            params={"limit": limit, "source": "jpl"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        objects = data.get("objects", [])
        neos = [obj for obj in objects if obj.get('neo') == 'Y']
        phas = [obj for obj in neos if obj.get('pha') == 'Y']
        
        result = "NEO Analysis\n" + "=" * 60 + "\n\n"
        result += f"Total Objects: {len(objects)}\n"
        result += f"NEOs: {len(neos)}\n"
        result += f"PHAs: {len(phas)}\n\n"
        
        if neos:
            avg = sum(obj.get('analysis', {}).get('completeness_score', 0) for obj in neos) / len(neos)
            result += f"Avg NEO Completeness: {avg:.1f}%\n\n"
        
        missing_diameter = [obj for obj in neos if 'diameter' in obj.get('analysis', {}).get('missing_properties', [])]
        missing_albedo = [obj for obj in neos if 'albedo' in obj.get('analysis', {}).get('missing_properties', [])]
        missing_spectral = [obj for obj in neos if 'spec_B' in obj.get('analysis', {}).get('missing_properties', [])]
        
        result += "Missing Critical Properties:\n"
        result += f"  Diameter: {len(missing_diameter)} NEOs\n"
        result += f"  Albedo: {len(missing_albedo)} NEOs\n"
        result += f"  Spectral: {len(missing_spectral)} NEOs\n"
        
        return result
        
    except Exception as e:
        return f"Error: {str(e)}"


# Tool dispatch
TOOL_HANDLERS = {
    "search_objects": search_objects,
    "get_object_details": get_object_details,
    "get_completeness_stats": get_completeness_stats,
    "find_under_researched": find_under_researched,
    "analyze_neos": analyze_neos
}


def handle_request(request: Dict) -> Dict:
    """Handle JSON-RPC request"""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    
    log(f"Received request: {method}")
    
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": TOOLS}
        }
    
    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        if tool_name in TOOL_HANDLERS:
            try:
                result_text = TOOL_HANDLERS[tool_name](tool_args)
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": result_text}]
                    }
                }
            except Exception as e:
                log(f"Error executing tool: {e}")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32603, "message": str(e)}
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
            }
    
    elif method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "0.1.0",
                "serverInfo": {
                    "name": "solar-system-explorer",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"}
        }


def main():
    """Main server loop"""
    log("Solar System Explorer MCP Server starting...")
    log(f"Backend URL: {BACKEND_URL}")
    log("Waiting for requests on stdin...")
    
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            log(f"JSON decode error: {e}")
        except Exception as e:
            log(f"Error: {e}")


if __name__ == "__main__":
    main()

