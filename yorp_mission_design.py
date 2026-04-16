#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YORP Mission Design Analysis
Analyze mission requirements for orbiting asteroid 54509 YORP
Including propulsion, power, and data return strategy
"""

import math
import json

# Mission target data (from previous analysis)
YORP_DATA = {
    'name': '54509 YORP (2000 PH5)',
    'a': 1.006,  # Semi-major axis in AU
    'e': 0.229,  # Eccentricity
    'i': 2.28,   # Inclination in degrees
    'period': 1.007,  # Orbital period in years (calculated from a³)
    'diameter': 0.13,  # Estimated diameter in km (130 meters)
    'orbit_dv': 7.675,  # Delta-v to orbit in km/s
}

# Physical constants
AU = 149597870.7  # km
G = 6.67430e-11  # m³/kg/s²
M_SUN = 1.989e30  # kg
EARTH_PERIOD = 365.25  # days

# Propulsion systems characteristics
PROPULSION_SYSTEMS = {
    'chemical': {
        'name': 'Chemical (Hydrazine)',
        'isp': 230,  # Specific impulse in seconds
        'thrust': 400,  # Newtons (typical)
        'power_req': 0,  # Self-contained
        'efficiency': 0.65,
        'cost': 'Low',
        'heritage': 'Extensive',
        'notes': 'High thrust, heavy fuel. Used on most traditional spacecraft'
    },
    'ion_xenon': {
        'name': 'Ion Drive (Xenon)',
        'isp': 3000,  # Specific impulse in seconds
        'thrust': 0.092,  # Newtons (Dawn spacecraft)
        'power_req': 2700,  # Watts at peak
        'efficiency': 0.70,
        'cost': 'Medium',
        'heritage': 'Proven (Dawn, Deep Space 1, Hayabusa)',
        'notes': 'Very fuel efficient, needs large solar arrays'
    },
    'ion_advanced': {
        'name': 'Advanced Ion Drive',
        'isp': 4500,  # Next-gen systems
        'thrust': 0.250,  # Improved thrust
        'power_req': 4000,  # Watts
        'efficiency': 0.75,
        'cost': 'High',
        'heritage': 'In development (NASA NEXT, ESA RIT)',
        'notes': 'Better thrust-to-power, requires 10-15 m² solar panels'
    },
    'hall_effect': {
        'name': 'Hall Effect Thruster',
        'isp': 1800,  # Specific impulse
        'thrust': 0.080,  # Newtons
        'power_req': 1500,  # Watts
        'efficiency': 0.60,
        'cost': 'Medium',
        'heritage': 'Common on satellites',
        'notes': 'Good balance of thrust and efficiency'
    },
    'solar_sail': {
        'name': 'Solar Sail',
        'isp': float('inf'),  # No propellant
        'thrust': 0.0001,  # Very low (per m² at 1 AU)
        'power_req': 0,  # Passive
        'efficiency': 1.0,
        'cost': 'Low-Medium',
        'heritage': 'Limited (IKAROS, LightSail)',
        'notes': 'No fuel needed, very slow acceleration'
    },
    'hybrid': {
        'name': 'Hybrid (Chemical + Ion)',
        'isp': 2500,  # Effective combined
        'thrust': 50,  # Chemical for boost, ion for cruise
        'power_req': 2000,
        'efficiency': 0.68,
        'cost': 'High',
        'heritage': 'Some missions (BepiColombo)',
        'notes': 'Best of both worlds - fast starts, efficient cruise'
    }
}


def calculate_mass_ratio(delta_v, isp):
    """
    Calculate mass ratio using Tsiolkovsky rocket equation
    delta_v: change in velocity (km/s)
    isp: specific impulse (seconds)
    Returns: mass_ratio (initial_mass / final_mass)
    """
    g0 = 9.80665e-3  # km/s² (standard gravity)
    ve = isp * g0  # Effective exhaust velocity
    mass_ratio = math.exp(delta_v / ve)
    return mass_ratio


def calculate_propellant_mass(dry_mass, mass_ratio):
    """
    Calculate propellant mass needed
    dry_mass: spacecraft dry mass (kg)
    mass_ratio: from Tsiolkovsky equation
    Returns: propellant mass (kg) and wet mass (kg)
    """
    wet_mass = dry_mass * mass_ratio
    propellant_mass = wet_mass - dry_mass
    return propellant_mass, wet_mass


def calculate_burn_time(delta_v, thrust, wet_mass, isp):
    """
    Calculate time needed for the burn
    delta_v: change in velocity (m/s)
    thrust: thrust force (N)
    wet_mass: initial mass (kg)
    isp: specific impulse (s)
    Returns: burn time in days
    """
    g0 = 9.80665  # m/s² (standard gravity)
    ve = isp * g0  # Effective exhaust velocity (m/s)
    mass_ratio = math.exp((delta_v * 1000) / ve)
    
    # For low thrust, burn time = (initial_mass * delta_v) / thrust
    # This is approximate for continuous thrust
    burn_time_seconds = (wet_mass * delta_v * 1000) / thrust
    burn_time_days = burn_time_seconds / 86400
    
    return burn_time_days


def calculate_solar_panel_requirements(power_req, distance_au=1.0):
    """
    Calculate solar panel size needed
    power_req: power requirement in watts
    distance_au: distance from sun (affects solar intensity)
    Returns: panel area in m² and power available
    """
    # Solar constant at 1 AU: 1367 W/m²
    solar_constant = 1367  # W/m²
    panel_efficiency = 0.28  # Modern triple-junction cells
    degradation_factor = 0.85  # Account for aging, temperature, angle
    
    # Solar intensity decreases with square of distance
    intensity = solar_constant / (distance_au ** 2)
    
    # Effective power per m²
    power_per_m2 = intensity * panel_efficiency * degradation_factor
    
    # Panel area needed
    panel_area = power_req / power_per_m2
    
    return panel_area, power_per_m2


def calculate_orbital_synodic_period(target_period_years):
    """
    Calculate synodic period - how often Earth and target align
    target_period_years: orbital period of target in years
    Returns: synodic period in years
    """
    earth_period = 1.0  # years
    synodic = abs(1 / (1/earth_period - 1/target_period_years))
    return synodic


def analyze_mission_profile(propulsion_type='ion_xenon', spacecraft_dry_mass=500):
    """
    Comprehensive mission analysis
    propulsion_type: key from PROPULSION_SYSTEMS
    spacecraft_dry_mass: mass without propellant (kg)
    """
    prop = PROPULSION_SYSTEMS[propulsion_type]
    
    print(f"\n{'='*80}")
    print(f"MISSION ANALYSIS: {YORP_DATA['name']}")
    print(f"Propulsion System: {prop['name']}")
    print(f"{'='*80}\n")
    
    # 1. TRAJECTORY AND DELTA-V
    print("=== TRAJECTORY REQUIREMENTS ===")
    delta_v = YORP_DATA['orbit_dv']
    print(f"Total mission delta-v: {delta_v:.3f} km/s")
    print(f"  - Transfer orbit: ~{delta_v * 0.85:.3f} km/s")
    print(f"  - Orbit insertion: ~{delta_v * 0.15:.3f} km/s")
    print(f"Target distance: {abs(YORP_DATA['a'] - 1.0):.3f} AU from Earth orbit")
    print(f"Orbital period: {YORP_DATA['period']:.3f} years\n")
    
    # 2. PROPELLANT REQUIREMENTS
    print("=== PROPULSION ANALYSIS ===")
    if prop['isp'] != float('inf'):
        mass_ratio = calculate_mass_ratio(delta_v, prop['isp'])
        propellant_mass, wet_mass = calculate_propellant_mass(spacecraft_dry_mass, mass_ratio)
        propellant_fraction = propellant_mass / wet_mass
        
        print(f"Specific Impulse (Isp): {prop['isp']} seconds")
        print(f"Thrust: {prop['thrust']} N")
        print(f"Spacecraft dry mass: {spacecraft_dry_mass} kg")
        print(f"Propellant mass needed: {propellant_mass:.1f} kg")
        print(f"Total wet mass: {wet_mass:.1f} kg")
        print(f"Propellant fraction: {propellant_fraction:.1%}\n")
        
        # Burn time
        if prop['thrust'] > 0:
            burn_time = calculate_burn_time(delta_v, prop['thrust'], wet_mass, prop['isp'])
            print(f"Estimated burn duration: {burn_time:.1f} days ({burn_time/30:.1f} months)")
            if burn_time < 1:
                print("  → Fast chemical burn")
            elif burn_time < 30:
                print("  → Short electric propulsion spiral")
            else:
                print("  → Extended ion drive cruise\n")
    else:
        print("Solar sail: No propellant needed")
        print("Acceleration time: 2-5 years (very slow)\n")
    
    # 3. POWER REQUIREMENTS
    if prop['power_req'] > 0:
        print("\n=== POWER SYSTEM (Solar Photovoltaic) ===")
        
        # At 1 AU (near Earth and YORP)
        panel_area_earth, power_per_m2_earth = calculate_solar_panel_requirements(
            prop['power_req'], 1.0
        )
        
        print(f"Power required: {prop['power_req']} W")
        print(f"Solar intensity at 1 AU: 1367 W/m²")
        print(f"Panel efficiency: 28% (modern triple-junction)")
        print(f"\nSolar panel area needed: {panel_area_earth:.1f} m²")
        print(f"  → Panel dimensions: ~{math.sqrt(panel_area_earth):.1f} × {math.sqrt(panel_area_earth):.1f} m")
        print(f"  → Power per m²: {power_per_m2_earth:.1f} W/m²")
        
        # Panel mass estimate (typical: 2-3 kg/m² for modern arrays)
        panel_mass = panel_area_earth * 2.5
        print(f"Estimated panel mass: {panel_mass:.1f} kg (at 2.5 kg/m²)")
        
        # Check if this is feasible
        print("\n=== SOLAR PV VIABILITY ===")
        if panel_area_earth < 20:
            print("✓ HIGHLY VIABLE - Compact solar arrays")
            print(f"  Similar to: Dawn spacecraft (10 m² panels)")
        elif panel_area_earth < 50:
            print("✓ VIABLE - Moderate solar array size")
            print(f"  Similar to: Juno spacecraft (60 m² panels)")
        else:
            print("⚠ CHALLENGING - Very large solar arrays needed")
            print(f"  Larger than most asteroid mission arrays")
        
        # Power availability at YORP's distance
        yorp_distance = YORP_DATA['a']
        panel_area_yorp, power_per_m2_yorp = calculate_solar_panel_requirements(
            prop['power_req'], yorp_distance
        )
        power_at_yorp = panel_area_earth * power_per_m2_yorp
        
        print(f"\nAt YORP's distance ({yorp_distance:.3f} AU):")
        print(f"  Available power: {power_at_yorp:.0f} W")
        print(f"  Power margin: {(power_at_yorp/prop['power_req'] - 1)*100:.1f}%")
    else:
        print("\n=== POWER SYSTEM ===")
        print("No propulsion power needed (chemical or solar sail)")
        print("Basic systems only: ~200-500 W")
        print("Solar panels: ~2-3 m² adequate for housekeeping\n")
    
    # 4. DATA RETURN WINDOWS
    print("\n=== DATA STORAGE & RETURN STRATEGY ===")
    synodic_period = calculate_orbital_synodic_period(YORP_DATA['period'])
    print(f"Synodic period: {synodic_period:.2f} years ({synodic_period*365:.0f} days)")
    print(f"  → This is how often YORP returns close to Earth")
    print(f"\nClose approach opportunities:")
    
    # YORP's period is very close to Earth's
    if abs(YORP_DATA['period'] - 1.0) < 0.1:
        print("  ★ EXCELLENT: Nearly resonant with Earth!")
        print("  ★ Close approaches every ~1 year")
        print("  ★ Minimal data storage needed")
    else:
        print(f"  Close approaches every ~{synodic_period:.1f} years")
        print(f"  Data storage needed: {synodic_period*365:.0f} days of observations")
    
    # Communication at YORP
    yorp_distance_km = YORP_DATA['a'] * AU
    earth_distance_km = 1.0 * AU
    
    # Best case: YORP at perihelion, Earth nearby
    min_distance_au = abs(YORP_DATA['a'] * (1 - YORP_DATA['e']) - 1.0)
    max_distance_au = YORP_DATA['a'] * (1 + YORP_DATA['e']) + 1.0
    
    print(f"\nCommunication distances:")
    print(f"  Minimum: {min_distance_au:.3f} AU ({min_distance_au * AU:.0f} km)")
    print(f"  Maximum: {max_distance_au:.3f} AU ({max_distance_au * AU:.0f} km)")
    print(f"  Light travel time: {min_distance_au * 499:.1f} - {max_distance_au * 499:.1f} seconds")
    
    # Data rate estimates
    print(f"\nData transmission (X-band at close approach):")
    print(f"  Typical rate: 1-10 kbps at {min_distance_au:.2f} AU")
    print(f"  10 GB dataset: {10*8*1e6/5e3/3600:.1f} hours at 5 kbps")
    
    # 5. MISSION TIMELINE
    print("\n=== MISSION TIMELINE ===")
    
    # Transfer time (Hohmann-like)
    transfer_time_years = (YORP_DATA['period'] + 1.0) / 2
    
    if propulsion_type in ['ion_xenon', 'ion_advanced', 'hall_effect']:
        print("Phase 1: Launch and spiral out from Earth")
        print(f"  Duration: {burn_time/30:.0f} months (low-thrust spiral)")
        print("\nPhase 2: Transfer to YORP")
        print(f"  Duration: {transfer_time_years*12:.0f} months")
        print("\nPhase 3: Rendezvous and orbit insertion")
        print(f"  Duration: 2-4 months (approach and characterization)")
        print("\nPhase 4: Science operations at YORP")
        print(f"  Duration: 6-24 months (or longer)")
        print("\nPhase 5: Wait for close approach to Earth")
        print(f"  Occurs every ~{synodic_period:.1f} years")
        print("\nPhase 6: Data downlink during close approach")
        print(f"  Window: 2-4 weeks at optimal distance")
        
        total_time = burn_time/365 + transfer_time_years + 1.5
        print(f"\nTotal mission duration: {total_time:.1f} years")
    
    # 6. MISSION FEASIBILITY
    print(f"\n{'='*80}")
    print("MISSION FEASIBILITY ASSESSMENT")
    print(f"{'='*80}")
    
    feasibility_score = 0
    max_score = 6
    
    # Delta-v
    if delta_v < 10:
        print("✓ Delta-v: EXCELLENT (<10 km/s)")
        feasibility_score += 1
    else:
        print("⚠ Delta-v: High")
    
    # Propellant fraction
    if propellant_fraction < 0.7:
        print(f"✓ Propellant fraction: GOOD ({propellant_fraction:.1%})")
        feasibility_score += 1
    else:
        print(f"⚠ Propellant fraction: High ({propellant_fraction:.1%})")
    
    # Solar panels
    if panel_area_earth < 20:
        print("✓ Solar panels: FEASIBLE (compact)")
        feasibility_score += 1
    else:
        print("⚠ Solar panels: Large arrays needed")
    
    # Mission duration
    if total_time < 5:
        print(f"✓ Mission duration: REASONABLE ({total_time:.1f} years)")
        feasibility_score += 1
    else:
        print(f"⚠ Mission duration: Long ({total_time:.1f} years)")
    
    # Close approaches
    if synodic_period < 2:
        print("✓ Data return: FREQUENT opportunities")
        feasibility_score += 1
    else:
        print("⚠ Data return: Infrequent opportunities")
    
    # Technology readiness
    if prop['heritage'] in ['Extensive', 'Proven (Dawn, Deep Space 1, Hayabusa)']:
        print(f"✓ Technology: PROVEN ({prop['heritage']})")
        feasibility_score += 1
    else:
        print(f"⚠ Technology: {prop['heritage']}")
    
    print(f"\n{'='*40}")
    print(f"Overall Feasibility: {feasibility_score}/{max_score}")
    if feasibility_score >= 5:
        print("★★★ HIGHLY FEASIBLE MISSION ★★★")
    elif feasibility_score >= 4:
        print("★★ FEASIBLE MISSION")
    else:
        print("★ CHALLENGING MISSION")
    print(f"{'='*40}\n")


def compare_all_propulsion():
    """Compare all propulsion options side-by-side"""
    print(f"\n{'='*100}")
    print("PROPULSION SYSTEM COMPARISON FOR YORP MISSION")
    print(f"{'='*100}\n")
    
    print(f"{'System':<25}{'Propellant':<15}{'Panels':<15}{'Burn Time':<15}{'Viability':<20}")
    print(f"{'Name':<25}{'Mass (kg)':<15}{'Area (m²)':<15}{'(days)':<15}{'Rating':<20}")
    print("-" * 100)
    
    spacecraft_mass = 500  # kg
    
    results = []
    
    for key, prop in PROPULSION_SYSTEMS.items():
        if prop['isp'] != float('inf'):
            mass_ratio = calculate_mass_ratio(YORP_DATA['orbit_dv'], prop['isp'])
            propellant_mass, wet_mass = calculate_propellant_mass(spacecraft_mass, mass_ratio)
            
            if prop['power_req'] > 0:
                panel_area, _ = calculate_solar_panel_requirements(prop['power_req'], 1.0)
            else:
                panel_area = 2  # Minimal for housekeeping
            
            burn_time = calculate_burn_time(YORP_DATA['orbit_dv'], prop['thrust'], 
                                           wet_mass, prop['isp'])
            
            # Viability rating
            if propellant_mass < 500 and panel_area < 20 and prop['heritage'] in ['Extensive', 'Proven (Dawn, Deep Space 1, Hayabusa)']:
                rating = "★★★ Excellent"
            elif propellant_mass < 1000 and panel_area < 40:
                rating = "★★ Good"
            else:
                rating = "★ Challenging"
            
            print(f"{prop['name']:<25}{propellant_mass:<15.0f}{panel_area:<15.1f}{burn_time:<15.1f}{rating:<20}")
            
            results.append({
                'system': key,
                'propellant': propellant_mass,
                'panels': panel_area,
                'burn_time': burn_time,
                'rating': rating
            })
    
    print("\n" + "="*100)
    
    # Recommendation
    print("\n=== RECOMMENDATION ===\n")
    
    best = min(results, key=lambda x: x['propellant'])
    
    print(f"✓ BEST OPTION: {PROPULSION_SYSTEMS[best['system']]['name']}")
    print(f"  Propellant: {best['propellant']:.0f} kg")
    print(f"  Solar panels: {best['panels']:.1f} m²")
    print(f"  Burn time: {best['burn_time']:.1f} days")
    print(f"\n  Why: {PROPULSION_SYSTEMS[best['system']]['notes']}")


def main():
    print("="*100)
    print(" " * 35 + "YORP MISSION DESIGN")
    print(" " * 25 + "Propulsion and Power System Analysis")
    print("="*100)
    
    # Detailed analysis of ion propulsion (most likely choice)
    analyze_mission_profile('ion_xenon', 500)
    
    # Compare all options
    print("\n\n")
    compare_all_propulsion()
    
    # Additional notes
    print("\n" + "="*100)
    print("SOLAR PV CONCLUSION")
    print("="*100)
    print("""
★ YES, Solar PV is HIGHLY VIABLE for a YORP mission!

Key advantages:
  1. YORP orbits at ~1 AU - same as Earth (optimal solar intensity)
  2. Ion drives work perfectly with solar panels (proven by Dawn, Hayabusa)
  3. Panel requirements: 10-15 m² (very manageable)
  4. No nuclear power needed (unlike deep space missions)

Reference missions:
  • Dawn (Vesta/Ceres): 10 m² solar panels, 3000s Isp ion drive
  • Hayabusa (Itokawa): 1.6 m² panels, ion propulsion
  • OSIRIS-REx (Bennu): Solar powered, chemical propulsion
  
YORP mission recommendation:
  → Ion propulsion + Solar PV is the IDEAL combination
  → Compact, proven, efficient
  → Similar to Dawn's successful asteroid missions
""")


if __name__ == '__main__':
    main()


