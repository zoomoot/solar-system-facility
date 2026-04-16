#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MCP Server for Solar System Small Bodies Explorer
Exposes the backend functionality through Model Context Protocol
"""

import json
import sys
from typing import Any, Sequence
import requests
import asyncio

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
except ImportError:
    print("Error: MCP SDK not installed. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Backend API configuration
BACKEND_URL = "http://localhost:5050"

# Initialize MCP server
app = Server("solar-system-explorer")


# ============================================================================
# MCP TOOLS
# ============================================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools for the Solar System Explorer"""
    return [
        Tool(
            name="search_objects",
            description="Search for small solar system bodies from JPL SBDB or SsODNet. Returns objects with completeness analysis and priority rankings.",
            inputSchema={
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
        ),
        Tool(
            name="get_object_details",
            description="Get detailed information about a specific solar system object by designation (e.g., '433' for Eros, '2023 DW' for a NEO)",
            inputSchema={
                "type": "object",
                "properties": {
                    "designation": {
                        "type": "string",
                        "description": "Object designation or number (e.g., '1' for Ceres, '433' for Eros)"
                    }
                },
                "required": ["designation"]
            }
        ),
        Tool(
            name="get_completeness_stats",
            description="Get overall completeness statistics for the dataset, including property coverage and priority distribution",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="find_under_researched",
            description="Find under-researched objects that are high-priority targets for observation or robotic missions",
            inputSchema={
                "type": "object",
                "properties": {
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Minimum priority level to filter by",
                        "default": "medium"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of objects to return",
                        "default": 50
                    }
                },
            }
        ),
        Tool(
            name="analyze_neos",
            description="Analyze Near-Earth Objects (NEOs) and identify those missing critical properties for planetary defense",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Number of NEOs to analyze",
                        "default": 200
                    }
                }
            }
        ),
        Tool(
            name="find_objects_by_property",
            description="Find objects missing specific properties (e.g., diameter, albedo, spectral type)",
            inputSchema={
                "type": "object",
                "properties": {
                    "missing_property": {
                        "type": "string",
                        "enum": ["diameter", "albedo", "rot_per", "spec_B", "spec_T", "GM", "BV", "UB"],
                        "description": "Property that should be missing"
                    },
                    "object_type": {
                        "type": "string",
                        "enum": ["neo", "pha", "mba", "all"],
                        "description": "Type of objects to filter",
                        "default": "all"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results",
                        "default": 50
                    }
                }
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls"""
    
    try:
        if name == "search_objects":
            return await search_objects(arguments)
        elif name == "get_object_details":
            return await get_object_details(arguments)
        elif name == "get_completeness_stats":
            return await get_completeness_stats(arguments)
        elif name == "find_under_researched":
            return await find_under_researched(arguments)
        elif name == "analyze_neos":
            return await analyze_neos(arguments)
        elif name == "find_objects_by_property":
            return await find_objects_by_property(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

async def search_objects(args: dict) -> Sequence[TextContent]:
    """Search for objects"""
    limit = args.get("limit", 100)
    source = args.get("source", "jpl")
    
    response = requests.get(
        f"{BACKEND_URL}/api/objects/search",
        params={"limit": limit, "source": source},
        timeout=30
    )
    response.raise_for_status()
    data = response.json()
    
    if not data.get("success"):
        return [TextContent(type="text", text=f"Error: {data.get('error', 'Unknown error')}")]
    
    objects = data.get("objects", [])
    
    # Format summary
    summary = f"Found {len(objects)} objects from {source.upper()}\n\n"
    
    # Statistics
    high_priority = sum(1 for obj in objects if obj.get('analysis', {}).get('research_priority') == 'high')
    avg_completeness = sum(obj.get('analysis', {}).get('completeness_score', 0) for obj in objects) / len(objects) if objects else 0
    
    summary += f"Statistics:\n"
    summary += f"  High Priority Objects: {high_priority}\n"
    summary += f"  Average Completeness: {avg_completeness:.1f}%\n\n"
    
    # Sample objects
    summary += "Sample Objects:\n"
    for i, obj in enumerate(objects[:10], 1):
        designation = obj.get('pdes', obj.get('spkid', 'Unknown'))
        name = obj.get('name', '-')
        neo = "NEO" if obj.get('neo') == 'Y' else "MBA"
        pha = " (PHA)" if obj.get('pha') == 'Y' else ""
        analysis = obj.get('analysis', {})
        completeness = analysis.get('completeness_score', 0)
        priority = analysis.get('research_priority', 'unknown')
        missing = ', '.join(analysis.get('missing_properties', [])[:3])
        
        summary += f"{i:2d}. {designation:15s} {name:20s} {neo}{pha:6s} "
        summary += f"Completeness: {completeness:5.1f}% Priority: {priority:8s} "
        summary += f"Missing: {missing}\n"
    
    if len(objects) > 10:
        summary += f"\n... and {len(objects) - 10} more objects\n"
    
    return [
        TextContent(type="text", text=summary),
        TextContent(type="text", text=f"\nFull data available. Total objects: {len(objects)}")
    ]


async def get_object_details(args: dict) -> Sequence[TextContent]:
    """Get details for a specific object"""
    designation = args.get("designation")
    
    if not designation:
        return [TextContent(type="text", text="Error: designation is required")]
    
    response = requests.get(
        f"{BACKEND_URL}/api/objects/{designation}",
        timeout=30
    )
    response.raise_for_status()
    data = response.json()
    
    # Format detailed information
    result = f"Object Details: {designation}\n"
    result += "=" * 60 + "\n\n"
    
    # JPL data
    if data.get('jpl'):
        jpl = data['jpl']
        if 'object' in jpl:
            obj = jpl['object']
            result += "Basic Information:\n"
            result += f"  Full Name: {obj.get('fullname', 'N/A')}\n"
            result += f"  Object Type: {obj.get('kind', 'N/A')}\n"
            result += f"  NEO: {obj.get('neo', 'N/A')}\n"
            result += f"  PHA: {obj.get('pha', 'N/A')}\n\n"
        
        if 'phys_par' in jpl:
            phys = jpl['phys_par']
            result += "Physical Properties:\n"
            for param in phys:
                result += f"  {param.get('name', 'Unknown')}: {param.get('value', 'N/A')} {param.get('units', '')}\n"
            result += "\n"
    
    # SsODNet data
    if data.get('ssodnet'):
        result += "SsODNet Data: Available\n"
    
    return [TextContent(type="text", text=result)]


async def get_completeness_stats(args: dict) -> Sequence[TextContent]:
    """Get completeness statistics"""
    response = requests.get(
        f"{BACKEND_URL}/api/stats/completeness",
        timeout=30
    )
    response.raise_for_status()
    data = response.json()
    
    if not data.get("success"):
        return [TextContent(type="text", text="Error getting statistics")]
    
    stats = data.get("stats", {})
    
    result = "Data Completeness Statistics\n"
    result += "=" * 60 + "\n\n"
    
    result += f"Total Objects Analyzed: {stats.get('total_objects', 0)}\n\n"
    
    # Property coverage
    result += "Property Coverage:\n"
    coverage = stats.get('property_coverage', {})
    total = stats.get('total_objects', 1)
    
    for prop, count in sorted(coverage.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total * 100) if total > 0 else 0
        bar_length = int(percentage / 2)
        bar = "█" * bar_length + "░" * (50 - bar_length)
        result += f"  {prop:12s} {bar} {percentage:5.1f}% ({count}/{total})\n"
    
    result += "\n"
    
    # Priority distribution
    result += "Research Priority Distribution:\n"
    priority_dist = stats.get('priority_distribution', {})
    for priority in ['high', 'medium', 'low', 'unknown']:
        count = priority_dist.get(priority, 0)
        percentage = (count / total * 100) if total > 0 else 0
        result += f"  {priority.capitalize():10s}: {count:4d} objects ({percentage:5.1f}%)\n"
    
    return [TextContent(type="text", text=result)]


async def find_under_researched(args: dict) -> Sequence[TextContent]:
    """Find under-researched objects"""
    priority = args.get("priority", "medium")
    limit = args.get("limit", 50)
    
    response = requests.get(
        f"{BACKEND_URL}/api/under-researched",
        params={"priority": priority, "limit": limit},
        timeout=30
    )
    response.raise_for_status()
    data = response.json()
    
    if not data.get("success"):
        return [TextContent(type="text", text=f"Error: {data.get('error', 'Unknown error')}")]
    
    objects = data.get("objects", [])
    
    result = f"Under-Researched Objects (Priority: {priority} and above)\n"
    result += "=" * 80 + "\n\n"
    result += f"Found {len(objects)} objects\n\n"
    
    result += f"{'Rank':<6} {'Designation':<15} {'Name':<20} {'Type':<10} {'Priority':<10} {'Complete':<10} {'Missing Properties'}\n"
    result += "-" * 80 + "\n"
    
    for i, obj in enumerate(objects, 1):
        designation = obj.get('pdes', obj.get('spkid', 'Unknown'))
        name = obj.get('name', '-')[:18]
        neo = "NEO" if obj.get('neo') == 'Y' else "MBA"
        pha = " (PHA)" if obj.get('pha') == 'Y' else ""
        obj_type = f"{neo}{pha}"
        
        analysis = obj.get('analysis', {})
        priority_val = analysis.get('research_priority', 'unknown').upper()
        completeness = analysis.get('completeness_score', 0)
        missing = ', '.join(analysis.get('missing_properties', [])[:3])
        
        result += f"#{i:<5d} {designation:<15s} {name:<20s} {obj_type:<10s} {priority_val:<10s} {completeness:5.1f}%     {missing}\n"
    
    result += "\n"
    result += "Recommendation: These objects are high-value targets for:\n"
    result += "  • Ground-based spectroscopic observations\n"
    result += "  • Radar characterization campaigns\n"
    result += "  • Space mission target selection\n"
    result += "  • Planetary defense assessments\n"
    
    return [TextContent(type="text", text=result)]


async def analyze_neos(args: dict) -> Sequence[TextContent]:
    """Analyze NEOs specifically"""
    limit = args.get("limit", 200)
    
    # Get objects
    response = requests.get(
        f"{BACKEND_URL}/api/objects/search",
        params={"limit": limit, "source": "jpl"},
        timeout=30
    )
    response.raise_for_status()
    data = response.json()
    
    objects = data.get("objects", [])
    
    # Filter for NEOs
    neos = [obj for obj in objects if obj.get('neo') == 'Y']
    phas = [obj for obj in neos if obj.get('pha') == 'Y']
    
    result = "Near-Earth Object (NEO) Analysis\n"
    result += "=" * 60 + "\n\n"
    
    result += f"Total Objects Analyzed: {len(objects)}\n"
    result += f"NEOs Found: {len(neos)}\n"
    result += f"PHAs (Potentially Hazardous): {len(phas)}\n\n"
    
    # Completeness analysis
    if neos:
        avg_completeness = sum(obj.get('analysis', {}).get('completeness_score', 0) for obj in neos) / len(neos)
        result += f"Average NEO Completeness: {avg_completeness:.1f}%\n\n"
    
    # Missing critical properties
    result += "NEOs Missing Critical Properties:\n"
    
    missing_diameter = [obj for obj in neos if 'diameter' in obj.get('analysis', {}).get('missing_properties', [])]
    missing_albedo = [obj for obj in neos if 'albedo' in obj.get('analysis', {}).get('missing_properties', [])]
    missing_spectral = [obj for obj in neos if 'spec_B' in obj.get('analysis', {}).get('missing_properties', []) or 'spec_T' in obj.get('analysis', {}).get('missing_properties', [])]
    
    result += f"  Missing Diameter: {len(missing_diameter)} NEOs\n"
    result += f"  Missing Albedo: {len(missing_albedo)} NEOs\n"
    result += f"  Missing Spectral Type: {len(missing_spectral)} NEOs\n\n"
    
    # High priority PHAs
    high_priority_phas = [obj for obj in phas if obj.get('analysis', {}).get('research_priority') == 'high']
    
    if high_priority_phas:
        result += f"High Priority PHAs ({len(high_priority_phas)}):\n"
        for i, obj in enumerate(high_priority_phas[:5], 1):
            designation = obj.get('pdes', obj.get('spkid', 'Unknown'))
            missing = ', '.join(obj.get('analysis', {}).get('missing_properties', [])[:3])
            result += f"  {i}. {designation} - Missing: {missing}\n"
    
    result += "\n"
    result += "Planetary Defense Recommendation:\n"
    result += "  Priority should be given to characterizing PHAs with missing\n"
    result += "  diameter and albedo data, as these are critical for impact\n"
    result += "  energy calculations and threat assessment.\n"
    
    return [TextContent(type="text", text=result)]


async def find_objects_by_property(args: dict) -> Sequence[TextContent]:
    """Find objects missing specific properties"""
    missing_property = args.get("missing_property")
    object_type = args.get("object_type", "all")
    limit = args.get("limit", 50)
    
    # Get objects
    response = requests.get(
        f"{BACKEND_URL}/api/objects/search",
        params={"limit": 500, "source": "jpl"},
        timeout=30
    )
    response.raise_for_status()
    data = response.json()
    
    objects = data.get("objects", [])
    
    # Filter by missing property
    filtered = []
    for obj in objects:
        missing_props = obj.get('analysis', {}).get('missing_properties', [])
        if missing_property in missing_props:
            # Filter by object type
            if object_type == "neo" and obj.get('neo') != 'Y':
                continue
            if object_type == "pha" and obj.get('pha') != 'Y':
                continue
            if object_type == "mba" and obj.get('neo') == 'Y':
                continue
            
            filtered.append(obj)
    
    # Limit results
    filtered = filtered[:limit]
    
    result = f"Objects Missing '{missing_property}' Property\n"
    result += "=" * 60 + "\n\n"
    result += f"Object Type Filter: {object_type.upper()}\n"
    result += f"Found {len(filtered)} objects\n\n"
    
    for i, obj in enumerate(filtered[:20], 1):
        designation = obj.get('pdes', obj.get('spkid', 'Unknown'))
        name = obj.get('name', '-')
        neo = "NEO" if obj.get('neo') == 'Y' else "MBA"
        pha = " (PHA)" if obj.get('pha') == 'Y' else ""
        completeness = obj.get('analysis', {}).get('completeness_score', 0)
        
        result += f"{i:2d}. {designation:15s} {name:20s} {neo}{pha:6s} Completeness: {completeness:5.1f}%\n"
    
    if len(filtered) > 20:
        result += f"\n... and {len(filtered) - 20} more objects\n"
    
    result += f"\nRecommendation: These objects would benefit from observations to measure {missing_property}.\n"
    
    return [TextContent(type="text", text=result)]


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

