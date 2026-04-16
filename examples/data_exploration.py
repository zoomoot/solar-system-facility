#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example script for exploring solar system small bodies data
This demonstrates how to use the API programmatically
"""

import requests
import json
from collections import Counter
import statistics

# API Base URL
BASE_URL = "http://localhost:5050"

def get_objects(limit=100, source='jpl'):
    """Fetch objects from the API"""
    url = f"{BASE_URL}/api/objects/search"
    params = {'limit': limit, 'source': source}
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data['success']:
        return data['objects']
    else:
        print(f"Error: {data.get('error', 'Unknown error')}")
        return []

def get_under_researched(priority='high', limit=50):
    """Get under-researched objects"""
    url = f"{BASE_URL}/api/under-researched"
    params = {'priority': priority, 'limit': limit}
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data['success']:
        return data['objects']
    else:
        print(f"Error: {data.get('error', 'Unknown error')}")
        return []

def analyze_completeness(objects):
    """Analyze completeness statistics"""
    if not objects:
        print("No objects to analyze")
        return
    
    scores = [obj['analysis']['completeness_score'] for obj in objects if 'analysis' in obj]
    
    print("\n" + "="*60)
    print("COMPLETENESS ANALYSIS")
    print("="*60)
    print(f"Total objects: {len(objects)}")
    print(f"Average completeness: {statistics.mean(scores):.1f}%")
    print(f"Median completeness: {statistics.median(scores):.1f}%")
    print(f"Min completeness: {min(scores):.1f}%")
    print(f"Max completeness: {max(scores):.1f}%")
    print(f"Std deviation: {statistics.stdev(scores):.1f}%")

def analyze_missing_properties(objects):
    """Analyze which properties are most commonly missing"""
    if not objects:
        print("No objects to analyze")
        return
    
    all_missing = []
    for obj in objects:
        if 'analysis' in obj:
            all_missing.extend(obj['analysis']['missing_properties'])
    
    missing_counts = Counter(all_missing)
    
    print("\n" + "="*60)
    print("MISSING PROPERTIES ANALYSIS")
    print("="*60)
    print(f"Total missing property instances: {len(all_missing)}")
    print("\nMost commonly missing properties:")
    for prop, count in missing_counts.most_common(10):
        percentage = (count / len(objects)) * 100
        print(f"  {prop:15s}: {count:4d} objects ({percentage:5.1f}%)")

def analyze_priority_distribution(objects):
    """Analyze priority distribution"""
    if not objects:
        print("No objects to analyze")
        return
    
    priorities = [obj['analysis']['research_priority'] for obj in objects if 'analysis' in obj]
    priority_counts = Counter(priorities)
    
    print("\n" + "="*60)
    print("RESEARCH PRIORITY DISTRIBUTION")
    print("="*60)
    for priority in ['high', 'medium', 'low', 'unknown']:
        count = priority_counts.get(priority, 0)
        percentage = (count / len(objects)) * 100
        print(f"  {priority.capitalize():10s}: {count:4d} objects ({percentage:5.1f}%)")

def find_neos_without_spectra(objects):
    """Find NEOs missing spectral classification"""
    neos_no_spec = []
    
    for obj in objects:
        is_neo = obj.get('neo') == 'Y'
        if is_neo and 'analysis' in obj:
            missing = obj['analysis']['missing_properties']
            if 'spec_B' in missing or 'spec_T' in missing:
                neos_no_spec.append(obj)
    
    print("\n" + "="*60)
    print("NEOs WITHOUT SPECTRAL CLASSIFICATION")
    print("="*60)
    print(f"Found {len(neos_no_spec)} NEOs missing spectral data\n")
    
    for i, obj in enumerate(neos_no_spec[:10], 1):
        designation = obj.get('pdes', obj.get('spkid', 'Unknown'))
        name = obj.get('name', '-')
        h_mag = obj.get('H', 'N/A')
        completeness = obj['analysis']['completeness_score']
        print(f"{i:2d}. {designation:15s} {name:20s} H={h_mag:6s} Completeness={completeness:5.1f}%")
    
    if len(neos_no_spec) > 10:
        print(f"\n... and {len(neos_no_spec) - 10} more")

def find_large_objects_without_diameter(objects):
    """Find bright objects (likely large) without measured diameter"""
    bright_no_diameter = []
    
    for obj in objects:
        h_mag = obj.get('H')
        has_diameter = obj.get('diameter') not in [None, '', 'null', 'N/A']
        
        if h_mag and not has_diameter:
            try:
                if float(h_mag) < 15.0:  # Bright = likely large
                    bright_no_diameter.append(obj)
            except (ValueError, TypeError):
                pass
    
    print("\n" + "="*60)
    print("BRIGHT OBJECTS WITHOUT DIAMETER MEASUREMENT")
    print("="*60)
    print(f"Found {len(bright_no_diameter)} bright objects (H<15) without diameter\n")
    
    # Sort by H magnitude (brightest first)
    bright_no_diameter.sort(key=lambda x: float(x.get('H', 99)))
    
    for i, obj in enumerate(bright_no_diameter[:10], 1):
        designation = obj.get('pdes', obj.get('spkid', 'Unknown'))
        name = obj.get('name', '-')
        h_mag = obj.get('H', 'N/A')
        neo = "NEO" if obj.get('neo') == 'Y' else "MBA"
        print(f"{i:2d}. {designation:15s} {name:20s} H={h_mag:6s} Type={neo}")
    
    if len(bright_no_diameter) > 10:
        print(f"\n... and {len(bright_no_diameter) - 10} more")

def export_high_priority_targets(objects, filename='high_priority_targets.json'):
    """Export high-priority targets to JSON file"""
    high_priority = [
        obj for obj in objects 
        if 'analysis' in obj and obj['analysis']['research_priority'] == 'high'
    ]
    
    export_data = []
    for obj in high_priority:
        export_data.append({
            'designation': obj.get('pdes', obj.get('spkid', 'Unknown')),
            'name': obj.get('name', ''),
            'neo': obj.get('neo') == 'Y',
            'pha': obj.get('pha') == 'Y',
            'H': obj.get('H'),
            'completeness': obj['analysis']['completeness_score'],
            'missing_properties': obj['analysis']['missing_properties'],
        })
    
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"\n✓ Exported {len(export_data)} high-priority targets to {filename}")

def main():
    """Main exploration workflow"""
    print("\n" + "="*60)
    print("SOLAR SYSTEM SMALL BODIES DATA EXPLORATION")
    print("="*60)
    
    # Fetch data
    print("\nFetching objects from JPL SBDB...")
    objects = get_objects(limit=500, source='jpl')
    
    if not objects:
        print("Failed to fetch objects. Is the server running?")
        return
    
    print(f"✓ Loaded {len(objects)} objects")
    
    # Run analyses
    analyze_completeness(objects)
    analyze_missing_properties(objects)
    analyze_priority_distribution(objects)
    find_neos_without_spectra(objects)
    find_large_objects_without_diameter(objects)
    
    # Export high-priority targets
    export_high_priority_targets(objects)
    
    print("\n" + "="*60)
    print("EXPLORATION COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("  1. Review high_priority_targets.json")
    print("  2. Cross-reference with observation schedules")
    print("  3. Submit telescope proposals")
    print("  4. Plan robotic missions to top targets")
    print()

if __name__ == '__main__':
    main()

