#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Probe Mission Analysis Tool
Calculate optimal targets for probe missions based on orbital mechanics and delta-v requirements
"""

import json
import math
import os
from collections import defaultdict


# Physical constants
G = 6.67430e-11  # Gravitational constant (m^3 kg^-1 s^-2)
AU = 149597870.7  # 1 AU in kilometers
MU_SUN = 1.32712440018e11  # Standard gravitational parameter of Sun (km^3/s^2)
MU_EARTH = 398600.4418  # Standard gravitational parameter of Earth (km^3/s^2)

# Earth orbital parameters
EARTH_A = 1.0  # Semi-major axis in AU
EARTH_E = 0.0167  # Eccentricity
EARTH_VELOCITY = 29.78  # Orbital velocity in km/s


def load_data():
    """Load object data from cache files"""
    # Try NEO mission data first (most complete for mission analysis)
    if os.path.exists('cache/neo_mission_data.json'):
        print("Loading cache/neo_mission_data.json...")
        with open('cache/neo_mission_data.json', 'r') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    
    # Try full cache
    if os.path.exists('data/full_sbdb_cache.json'):
        print("Loading data/full_sbdb_cache.json...")
        with open('data/full_sbdb_cache.json', 'r') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    
    # Try regular cache
    if os.path.exists('cache/jpl_sbdb_cache.json'):
        print("Loading cache/jpl_sbdb_cache.json...")
        with open('cache/jpl_sbdb_cache.json', 'r') as f:
            cache = json.load(f)
            # Extract data from cache structure
            objects = {}
            for key, value in cache.items():
                if isinstance(value, dict) and 'data' in value:
                    if isinstance(value['data'], list):
                        for obj in value['data']:
                            if isinstance(obj, dict):
                                spkid = obj.get('spkid', key)
                                objects[str(spkid)] = obj
                    elif isinstance(value['data'], dict):
                        objects[key] = value['data']
            return objects
    
    return {}


def calculate_hohmann_transfer_dv(a1, a2):
    """
    Calculate delta-v for Hohmann transfer orbit
    a1: Initial semi-major axis (AU)
    a2: Final semi-major axis (AU)
    Returns: total delta-v in km/s
    """
    a1_km = a1 * AU
    a2_km = a2 * AU
    
    # Velocity at initial orbit
    v1 = math.sqrt(MU_SUN / a1_km)
    
    # Velocity at transfer orbit perihelion
    v_transfer_peri = math.sqrt(MU_SUN * (2/a1_km - 1/((a1_km + a2_km)/2)))
    
    # Velocity at transfer orbit aphelion
    v_transfer_apo = math.sqrt(MU_SUN * (2/a2_km - 1/((a1_km + a2_km)/2)))
    
    # Velocity at final orbit
    v2 = math.sqrt(MU_SUN / a2_km)
    
    # Delta-v for departure and arrival
    dv1 = abs(v_transfer_peri - v1)
    dv2 = abs(v2 - v_transfer_apo)
    
    return dv1 + dv2


def calculate_orbit_insertion_dv(a, e):
    """
    Calculate delta-v needed to enter orbit around target
    Based on target's orbital velocity and escape velocity
    a: Semi-major axis (AU)
    e: Eccentricity
    Returns: orbit insertion delta-v estimate in km/s
    """
    a_km = a * AU
    
    # Orbital velocity at perihelion
    r_peri = a_km * (1 - e)
    v_peri = math.sqrt(MU_SUN * (2/r_peri - 1/a_km))
    
    # For orbit insertion, we need to match velocity
    # Estimate: about 20% of orbital velocity for capture
    return v_peri * 0.2


def calculate_landing_dv(diameter, mass=None):
    """
    Estimate delta-v needed to land on surface
    diameter: Object diameter in km
    mass: Object mass in kg (if known)
    Returns: landing delta-v estimate in km/s
    """
    if not diameter or diameter <= 0:
        return None
    
    radius_km = diameter / 2.0
    
    # If mass is known, calculate escape velocity
    if mass and mass > 0:
        radius_m = radius_km * 1000
        v_esc = math.sqrt(2 * G * mass / radius_m) / 1000  # km/s
        return v_esc
    
    # Otherwise estimate based on size (assume density ~2 g/cm³)
    # Smaller objects have negligible gravity
    if diameter < 1:
        return 0.001  # Essentially zero
    elif diameter < 10:
        return 0.01
    elif diameter < 100:
        return 0.1
    else:
        # Rough estimate: v_esc ≈ 0.5 * sqrt(diameter_in_km)
        return 0.5 * math.sqrt(diameter)


def analyze_mission_costs(objects):
    """Analyze all objects and calculate mission costs"""
    results = []
    
    for spkid, obj in objects.items():
        # Skip if no orbital data
        if not isinstance(obj, dict):
            continue
        
        # Get and convert values to appropriate types
        try:
            a = float(obj.get('a')) if obj.get('a') not in [None, ''] else None
            e = float(obj.get('e')) if obj.get('e') not in [None, ''] else 0.0
            i = float(obj.get('i')) if obj.get('i') not in [None, ''] else None
            diameter = float(obj.get('diameter')) if obj.get('diameter') not in [None, ''] else None
            H = float(obj.get('H')) if obj.get('H') not in [None, ''] else None
        except (ValueError, TypeError):
            continue
            
        full_name = obj.get('full_name', spkid)
        neo = obj.get('neo', 'N')
        pha = obj.get('pha', 'N')
        
        if not a or a <= 0:
            continue
        
        if e is None:
            e = 0.0
        
        # Calculate transfer delta-v
        try:
            transfer_dv = calculate_hohmann_transfer_dv(EARTH_A, a)
        except:
            continue
        
        # Add inclination penalty (rough estimate)
        if i:
            inclination_penalty = abs(i) * 0.05  # ~50 m/s per degree
        else:
            inclination_penalty = 0
        
        # Calculate orbit insertion delta-v
        try:
            orbit_dv = calculate_orbit_insertion_dv(a, e)
        except:
            orbit_dv = 1.0  # Default estimate
        
        # Calculate landing delta-v
        landing_dv = calculate_landing_dv(diameter)
        
        # Total delta-v for orbiting mission
        total_orbit_dv = transfer_dv + inclination_penalty + orbit_dv
        
        # Total delta-v for landing mission
        if landing_dv is not None:
            total_landing_dv = total_orbit_dv + landing_dv
        else:
            total_landing_dv = None
        
        # Calculate distance from Earth
        distance_from_earth = abs(a - EARTH_A)
        
        results.append({
            'name': full_name,
            'spkid': spkid,
            'neo': neo,
            'pha': pha,
            'H': H,
            'a': a,
            'e': e,
            'i': i,
            'diameter': diameter,
            'distance_au': distance_from_earth,
            'transfer_dv': transfer_dv,
            'orbit_insertion_dv': orbit_dv,
            'landing_dv': landing_dv,
            'total_orbit_dv': total_orbit_dv,
            'total_landing_dv': total_landing_dv
        })
    
    return results


def print_top_targets(results, mission_type='orbit', top_n=20):
    """Print the best targets for a given mission type"""
    
    if mission_type == 'orbit':
        dv_key = 'total_orbit_dv'
        print(f"\n{'='*80}")
        print(f"TOP {top_n} CHEAPEST TARGETS FOR ORBITAL MISSIONS")
        print(f"{'='*80}\n")
    else:
        dv_key = 'total_landing_dv'
        print(f"\n{'='*80}")
        print(f"TOP {top_n} CHEAPEST TARGETS FOR LANDING MISSIONS")
        print(f"{'='*80}\n")
        # Filter out objects without landing delta-v
        results = [r for r in results if r[dv_key] is not None]
    
    # Sort by delta-v
    sorted_results = sorted(results, key=lambda x: x[dv_key])
    
    print(f"{'Rank':<6}{'Object':<35}{'NEO':<5}{'Δv (km/s)':<12}{'Distance':<12}{'Diameter':<12}")
    print(f"{'':<6}{'Name':<35}{'PHA':<5}{'Total':<12}{'(AU)':<12}{'(km)':<12}")
    print("-" * 80)
    
    for i, obj in enumerate(sorted_results[:top_n], 1):
        name_display = obj['name'][:33] if len(obj['name']) > 33 else obj['name']
        neo_pha = f"{obj['neo']}/{obj['pha']}"
        dv_display = f"{obj[dv_key]:.3f}"
        dist_display = f"{obj['distance_au']:.3f}"
        diam_display = f"{obj['diameter']:.2f}" if obj['diameter'] else "Unknown"
        
        print(f"{i:<6}{name_display:<35}{neo_pha:<5}{dv_display:<12}{dist_display:<12}{diam_display:<12}")


def print_neo_analysis(results):
    """Print analysis specific to NEOs"""
    neos = [r for r in results if r['neo'] == 'Y']
    phas = [r for r in results if r['pha'] == 'Y']
    
    print(f"\n{'='*80}")
    print("NEAR-EARTH OBJECTS (NEO) ANALYSIS")
    print(f"{'='*80}\n")
    
    print(f"Total NEOs in dataset: {len(neos)}")
    print(f"Total PHAs in dataset: {len(phas)}")
    
    if neos:
        # Sort by orbit delta-v
        neos_by_orbit = sorted(neos, key=lambda x: x['total_orbit_dv'])
        
        print(f"\nCheapest NEO to orbit: {neos_by_orbit[0]['name']}")
        print(f"  Delta-v required: {neos_by_orbit[0]['total_orbit_dv']:.3f} km/s")
        print(f"  Distance: {neos_by_orbit[0]['distance_au']:.3f} AU from Earth's orbit")
        
        # Landing
        neos_with_landing = [n for n in neos if n['total_landing_dv'] is not None]
        if neos_with_landing:
            neos_by_landing = sorted(neos_with_landing, key=lambda x: x['total_landing_dv'])
            print(f"\nCheapest NEO to land on: {neos_by_landing[0]['name']}")
            print(f"  Delta-v required: {neos_by_landing[0]['total_landing_dv']:.3f} km/s")
            print(f"  Diameter: {neos_by_landing[0]['diameter']:.2f} km")


def print_summary_statistics(results):
    """Print overall summary statistics"""
    print(f"\n{'='*80}")
    print("MISSION FEASIBILITY SUMMARY")
    print(f"{'='*80}\n")
    
    total_objects = len(results)
    objects_with_diameter = len([r for r in results if r['diameter']])
    
    print(f"Total objects analyzed: {total_objects}")
    print(f"Objects with known diameter: {objects_with_diameter}")
    
    # Delta-v ranges
    if results:
        orbit_dvs = [r['total_orbit_dv'] for r in results]
        landing_dvs = [r['total_landing_dv'] for r in results if r['total_landing_dv']]
        
        print(f"\nOrbital missions:")
        print(f"  Minimum delta-v: {min(orbit_dvs):.3f} km/s")
        print(f"  Maximum delta-v: {max(orbit_dvs):.3f} km/s")
        print(f"  Average delta-v: {sum(orbit_dvs)/len(orbit_dvs):.3f} km/s")
        
        if landing_dvs:
            print(f"\nLanding missions:")
            print(f"  Minimum delta-v: {min(landing_dvs):.3f} km/s")
            print(f"  Maximum delta-v: {max(landing_dvs):.3f} km/s")
            print(f"  Average delta-v: {sum(landing_dvs)/len(landing_dvs):.3f} km/s")
        
        # Compare to reference missions
        print(f"\n--- Reference Delta-v Values ---")
        print(f"Low Earth Orbit (LEO):        ~9.4 km/s")
        print(f"Geostationary Transfer:      ~15.5 km/s")
        print(f"Moon orbit:                  ~13.5 km/s")
        print(f"Mars orbit:                  ~15-18 km/s")


def main():
    print("="*80)
    print("SOLAR SYSTEM PROBE MISSION ANALYSIS")
    print("Finding the cheapest objects to send probes to")
    print("="*80)
    
    # Load data
    objects = load_data()
    
    if not objects:
        print("\nERROR: No data found!")
        print("Please run the application first to load object data from JPL.")
        print("Try: python app.py or python streamlit_app.py")
        return
    
    print(f"\nLoaded {len(objects)} objects from cache")
    
    # Analyze mission costs
    print("\nAnalyzing orbital mechanics and calculating delta-v requirements...")
    results = analyze_mission_costs(objects)
    
    if not results:
        print("\nERROR: No objects with valid orbital data found!")
        return
    
    print(f"Successfully analyzed {len(results)} objects with orbital data")
    
    # Print results
    print_summary_statistics(results)
    print_top_targets(results, mission_type='orbit', top_n=20)
    print_top_targets(results, mission_type='landing', top_n=20)
    print_neo_analysis(results)
    
    # Export detailed results
    output_file = 'mission_analysis_results.json'
    with open(output_file, 'w') as f:
        json.dump(sorted(results, key=lambda x: x['total_orbit_dv'])[:100], f, indent=2)
    print(f"\n✓ Detailed results exported to {output_file}")
    print(f"  (Top 100 targets by orbital delta-v)")


if __name__ == '__main__':
    main()

