#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analysis: Repurposing Existing Satellites for YORP Mission
Evaluate feasibility of converting operational or end-of-life satellites
"""

import math

# Physical constants
MU_EARTH = 398600.4418  # km³/s²
EARTH_RADIUS = 6371  # km
LEO_ALTITUDE = 400  # km (typical)
GEO_ALTITUDE = 35786  # km

def calculate_escape_velocity(altitude_km):
    """Calculate escape velocity from Earth orbit"""
    r = EARTH_RADIUS + altitude_km
    v_orbit = math.sqrt(MU_EARTH / r)
    v_escape = math.sqrt(2 * MU_EARTH / r)
    delta_v_escape = v_escape - v_orbit
    return v_orbit, v_escape, delta_v_escape


def print_header():
    print("="*100)
    print(" " * 30 + "REPURPOSING SATELLITES FOR YORP MISSION")
    print(" " * 35 + "Feasibility Analysis")
    print("="*100)


def analyze_orbit_requirements():
    """Analyze delta-v from various Earth orbits"""
    print("\n" + "="*100)
    print("1. DELTA-V REQUIREMENTS FROM EARTH ORBIT")
    print("="*100)
    
    print("\nYORP Mission Requirements:")
    print(f"  • Delta-v from Earth orbit to YORP: 7.675 km/s")
    print(f"  • Plus: Escape from Earth orbit")
    print(f"  • Total: ~11-12 km/s depending on starting orbit\n")
    
    orbits = [
        ("Low Earth Orbit (LEO)", 400, "Earth observation, some science"),
        ("Medium Earth Orbit (MEO)", 20000, "GPS, navigation satellites"),
        ("Geostationary (GEO)", 35786, "Communications, weather"),
        ("Highly Elliptical (HEO)", 40000, "Some communication, science"),
    ]
    
    print(f"{'Orbit Type':<30}{'Altitude':<15}{'Escape Δv':<15}{'Total to YORP':<15}")
    print(f"{'Name':<30}{'(km)':<15}{'(km/s)':<15}{'(km/s)':<15}")
    print("-"*100)
    
    for name, altitude, purpose in orbits:
        v_orbit, v_escape, dv_escape = calculate_escape_velocity(altitude)
        total_dv = dv_escape + 7.675
        print(f"{name:<30}{altitude:<15}{dv_escape:<15.3f}{total_dv:<15.3f}")
        print(f"  Purpose: {purpose}\n")
    
    print("\n⚠️  CHALLENGE: Most satellites lack the propulsion for 11+ km/s delta-v!")


def analyze_candidate_satellites():
    """Analyze specific satellite types that might be repurposed"""
    print("\n" + "="*100)
    print("2. CANDIDATE SATELLITE TYPES FOR REPURPOSING")
    print("="*100)
    
    candidates = [
        {
            'category': 'Earth Observation Satellites',
            'examples': ['Landsat-9', 'Sentinel-2', 'WorldView-4', 'Terra/Aqua'],
            'orbit': 'LEO (400-800 km)',
            'mass': '2000-6000 kg',
            'propulsion': 'Chemical (hydrazine)',
            'typical_dv': '0.1-0.5 km/s (station-keeping only)',
            'instruments': 'High-res cameras, multispectral, radar',
            'power': 'Solar panels: 2-10 kW',
            'pros': [
                '✓ Good cameras (surface imaging)',
                '✓ Excellent solar panels',
                '✓ Sophisticated pointing/navigation',
            ],
            'cons': [
                '✗ Insufficient propulsion (need ~11 km/s)',
                '✗ Instruments optimized for Earth, not asteroids',
                '✗ No deep space communications',
            ],
            'feasibility': '⭐☆☆☆☆ (1/5) - INFEASIBLE without major propulsion upgrade',
            'cost': 'Retrofit propulsion: $200-300M (defeats purpose)',
        },
        {
            'category': 'Communication Satellites',
            'examples': ['Intelsat', 'Starlink (individual)', 'O3b', 'Iridium NEXT'],
            'orbit': 'GEO (35,786 km) or LEO (550 km)',
            'mass': '2000-6500 kg (GEO), 260 kg (Starlink)',
            'propulsion': 'Ion/plasma (GEO), Hall thrusters (Starlink)',
            'typical_dv': '0.5-1.5 km/s (station-keeping)',
            'instruments': 'Transponders, antennas (no science payload)',
            'power': 'Solar panels: 5-20 kW (GEO), 5 kW (Starlink)',
            'pros': [
                '✓ Some have electric propulsion',
                '✓ Excellent solar panels and power systems',
                '✓ Good communication systems',
                '✓ Autonomous operations capability',
            ],
            'cons': [
                '✗ Still insufficient delta-v (~10x too little)',
                '✗ NO science instruments at all',
                '✗ Wrong communication frequency/power',
                '✗ Heavy (payload adapter issues)',
            ],
            'feasibility': '⭐⭐☆☆☆ (2/5) - MARGINAL, would need complete science retrofit',
            'cost': 'Add instruments + propulsion: $150-250M',
        },
        {
            'category': 'Military/Reconnaissance Satellites',
            'examples': ['KH-11 (Keyhole)', 'NRO satellites', 'Space Force assets'],
            'orbit': 'Various (LEO to GEO)',
            'mass': 'Classified (estimated 13,000-19,600 kg)',
            'propulsion': 'Chemical + possibly ion',
            'typical_dv': 'Unknown (likely <2 km/s)',
            'instruments': 'Extremely high-res imaging, signals intelligence',
            'power': 'Solar panels: Likely 10-20 kW',
            'pros': [
                '✓ Sophisticated imaging (excellent for YORP)',
                '✓ Advanced pointing and tracking',
                '✓ Robust power systems',
                '✓ Autonomous operations',
            ],
            'cons': [
                '✗ Classified - politically impossible',
                '✗ Insufficient propulsion for deep space',
                '✗ Instruments classified/cannot be disclosed',
                '✗ Very heavy (propellant requirements)',
            ],
            'feasibility': '⭐☆☆☆☆ (1/5) - POLITICALLY INFEASIBLE',
            'cost': 'N/A - not available for civilian science',
        },
        {
            'category': 'Failed/Stranded Deep Space Probes',
            'examples': ['Beresheet (Moon lander)', 'Omotenashi (Moon)', 'Lost Mars probes'],
            'orbit': 'Various (some in heliocentric)',
            'mass': '100-600 kg',
            'propulsion': 'Chemical or ion (if working)',
            'typical_dv': 'Varies - may have reserve propellant',
            'instruments': 'Science cameras, spectrometers',
            'power': 'Solar panels: 0.5-2 kW',
            'pros': [
                '✓✓ Already in deep space trajectory (some)',
                '✓✓ Designed for planetary science',
                '✓ Appropriate instruments',
                '✓ Deep space communications',
            ],
            'cons': [
                '✗ Usually failed = non-functional',
                '✗ May have communication issues',
                '✗ Unknown propellant reserves',
                '✗ Trajectory may be wrong',
            ],
            'feasibility': '⭐⭐⭐☆☆ (3/5) - DEPENDS on specific failure mode',
            'cost': 'Depends on what failed - could be low if fixable',
        },
        {
            'category': 'Excess Rideshare/Secondary Payloads',
            'examples': ['ESPA ring satellites', 'Secondary payload buses'],
            'orbit': 'Various (depends on primary mission)',
            'mass': '100-500 kg',
            'propulsion': 'Usually minimal',
            'typical_dv': '0.1-0.5 km/s',
            'instruments': 'Varies - often technology demos',
            'power': 'Solar panels: 0.3-1 kW',
            'pros': [
                '✓ Potentially available',
                '✓ Lower mass = lower propellant needs',
                '✓ Some have modular designs',
            ],
            'cons': [
                '✗ Minimal propulsion',
                '✗ Limited power',
                '✗ Usually no science instruments',
                '✗ Not designed for deep space',
            ],
            'feasibility': '⭐☆☆☆☆ (1/5) - Would need complete rebuild',
            'cost': '$100-200M in modifications',
        },
        {
            'category': 'Commercial Deep Space Missions (Future)',
            'examples': ['iSpace landers', 'Astrobotic Peregrine', 'Firefly Blue Ghost'],
            'orbit': 'Lunar or planned planetary',
            'mass': '300-1500 kg',
            'propulsion': 'Chemical + possibly ion',
            'typical_dv': '3-5 km/s capability',
            'instruments': 'Science payloads, cameras',
            'power': 'Solar panels: 1-3 kW',
            'pros': [
                '✓✓ Designed for deep space',
                '✓✓ Appropriate propulsion systems',
                '✓ Can carry science payloads',
                '✓ Lower cost than traditional spacecraft',
            ],
            'cons': [
                '⚠ Still need propulsion upgrade',
                '⚠ May lack specific YORP instruments',
                '⚠ Need trajectory modification',
            ],
            'feasibility': '⭐⭐⭐⭐☆ (4/5) - MOST PROMISING OPTION',
            'cost': '$50-150M (modify existing commercial platform)',
        },
    ]
    
    for i, cat in enumerate(candidates, 1):
        print(f"\n{'─'*100}")
        print(f"Category {i}: {cat['category']}")
        print(f"Examples: {', '.join(cat['examples'])}")
        print(f"{'─'*100}")
        print(f"\nSpecs:")
        print(f"  Orbit: {cat['orbit']}")
        print(f"  Mass: {cat['mass']}")
        print(f"  Propulsion: {cat['propulsion']}")
        print(f"  Delta-v capability: {cat['typical_dv']}")
        print(f"  Instruments: {cat['instruments']}")
        print(f"  Power: {cat['power']}")
        
        print(f"\nPros:")
        for pro in cat['pros']:
            print(f"  {pro}")
        
        print(f"\nCons:")
        for con in cat['cons']:
            print(f"  {con}")
        
        print(f"\nFeasibility: {cat['feasibility']}")
        print(f"Estimated retrofit cost: {cat['cost']}")


def analyze_specific_opportunities():
    """Look at specific real satellites that might be candidates"""
    print("\n\n" + "="*100)
    print("3. SPECIFIC REPURPOSING OPPORTUNITIES")
    print("="*100)
    
    opportunities = [
        {
            'name': 'Hubble Space Telescope',
            'status': 'Operational but aging (launched 1990)',
            'orbit': 'LEO (540 km)',
            'mass': '11,110 kg',
            'instruments': 'World-class optical/UV imaging',
            'propulsion': 'None (was serviced by Shuttle)',
            'assessment': 'IMPOSSIBLE',
            'reasons': [
                '✗ No propulsion system at all',
                '✗ National treasure - politically impossible',
                '✗ Still doing valuable science',
                '✗ Far too massive',
            ],
        },
        {
            'name': 'James Webb Space Telescope',
            'status': 'Operational (launched 2021)',
            'orbit': 'L2 halo orbit (1.5M km from Earth)',
            'mass': '6,200 kg',
            'instruments': 'Infrared telescope',
            'propulsion': 'Minimal (station-keeping)',
            'assessment': 'ABSOLUTELY NOT',
            'reasons': [
                '✗ $10 BILLION mission - would never risk it',
                '✗ Doing revolutionary astrophysics',
                '✗ Wrong instruments (IR optimized for deep space)',
                '✗ At L2 - wrong location for YORP',
            ],
        },
        {
            'name': 'Dawn Spacecraft (Retired)',
            'status': 'End of life, in orbit around Ceres (2018)',
            'orbit': 'Heliocentric - orbiting Ceres (2.8 AU)',
            'mass': '1,240 kg',
            'instruments': 'Cameras, spectrometers - PERFECT for asteroids',
            'propulsion': 'Ion drive (xenon depleted)',
            'assessment': '★★★ THEORETICALLY IDEAL (but out of propellant)',
            'reasons': [
                '✓✓✓ Perfect spacecraft for asteroid missions',
                '✓✓ Already proved ion + solar works',
                '✓✓ Right instruments for YORP',
                '✗✗✗ OUT OF PROPELLANT (mission ended)',
                '✗ At Ceres (2.8 AU) - would need ~5 km/s to leave',
                '✗ No fuel reserves',
            ],
        },
        {
            'name': 'Lunar Gateway (Under Construction)',
            'status': 'Being built - launch 2025+',
            'orbit': 'Lunar NRHO (near-rectilinear halo orbit)',
            'mass': '~40,000 kg (full station)',
            'instruments': 'Would need complete science package',
            'propulsion': 'Electric (PPE module) + chemical',
            'assessment': '⭐⭐☆☆☆ INTERESTING but impractical',
            'reasons': [
                '✓ Has substantial propulsion (PPE: 11.5 kW ion)',
                '✓ Modular - could detach components',
                '✓ Near Moon - lower escape delta-v',
                '✗ Far too massive for YORP mission',
                '✗ Primary mission is lunar operations',
                '✗ Would need custom science module',
            ],
        },
        {
            'name': 'Commercial Lunar Landers (Spare/Test Units)',
            'status': 'Available - companies have backups',
            'orbit': 'Not yet launched (ground-based)',
            'mass': '300-1,500 kg',
            'instruments': 'Cameras, payload adapters',
            'propulsion': 'Chemical (3-5 km/s capability)',
            'assessment': '★★★★☆ BEST PRACTICAL OPTION',
            'reasons': [
                '✓✓ Actually available for purchase',
                '✓✓ Designed for deep space already',
                '✓ Reasonable cost ($20-50M base)',
                '✓ Can add ion propulsion module',
                '✓ Modify instruments for asteroids',
                '⚠ Still need propulsion upgrade (add ion stage)',
                '⚠ Would cost $100-200M total',
            ],
        },
        {
            'name': 'Starship (SpaceX) - Use as Tug',
            'status': 'In testing',
            'orbit': 'Can reach anywhere',
            'mass': 'Can carry 100-150 tons',
            'instruments': 'N/A - would be carrier vehicle',
            'propulsion': 'Chemical - massive capability',
            'assessment': '★★★★★ GAME-CHANGING OPTION',
            'reasons': [
                '✓✓✓ Could deliver complete YORP mission directly',
                '✓✓ Massive payload capacity (100+ tons)',
                '✓✓ Refuelable in orbit = huge delta-v',
                '✓ Could deliver multiple probes to multiple asteroids',
                '✓ Dramatically lower cost per kg',
                '⚠ Still in development',
                '⚠ Would need small probe that separates at YORP',
            ],
        },
    ]
    
    for opp in opportunities:
        print(f"\n{'─'*100}")
        print(f"Spacecraft: {opp['name']}")
        print(f"Status: {opp['status']}")
        print(f"Assessment: {opp['assessment']}")
        print(f"{'─'*100}")
        print(f"  Orbit: {opp['orbit']}")
        print(f"  Mass: {opp['mass']}")
        print(f"  Instruments: {opp['instruments']}")
        print(f"  Propulsion: {opp['propulsion']}")
        print(f"\nReasons:")
        for reason in opp['reasons']:
            print(f"  {reason}")


def print_recommendations():
    """Print final recommendations"""
    print("\n\n" + "="*100)
    print("4. RECOMMENDATIONS: CAN WE REPURPOSE A SATELLITE?")
    print("="*100)
    
    print("""
SHORT ANSWER: Not really - but there are creative alternatives!

═══════════════════════════════════════════════════════════════════════════════

❌ EXISTING EARTH SATELLITES: NOT FEASIBLE

Problem: Satellites in Earth orbit lack the propulsion for 11+ km/s delta-v
  • Earth observation satellites: 0.1-0.5 km/s capability (need 20x more!)
  • Communication satellites: 0.5-1.5 km/s capability (need 7x more!)
  • Even GEO satellites: Insufficient for deep space mission
  
Adding propulsion would cost $200-300M - defeats purpose of repurposing!

═══════════════════════════════════════════════════════════════════════════════

✅ BETTER ALTERNATIVES: USE COMMERCIAL SPACECRAFT

1. ★★★★★ PURCHASE COMMERCIAL LUNAR LANDER PLATFORM
   
   Who: iSpace, Astrobotic, Firefly Aerospace, Intuitive Machines
   Cost: $50-150M (complete spacecraft with modifications)
   
   Approach:
     • Buy spare/test unit lunar lander (~$30M)
     • Add ion propulsion stage (~$40M)
     • Add/modify science instruments (~$30M)
     • Integration and testing (~$20M)
     
   Total: ~$120-150M
   
   Advantages:
     ✓ Already designed for deep space
     ✓ Flight-proven systems (some already flown)
     ✓ Commercial rates (much cheaper than custom)
     ✓ Can negotiate customization
     ✓ Multiple vendors available
   
   This is essentially "buying off the shelf + upgrades"

═══════════════════════════════════════════════════════════════════════════════

2. ★★★★☆ RIDE-SHARE WITH STARSHIP TO LUNAR ORBIT
   
   Who: SpaceX Starship
   Cost: $10-30M for ride + $80M for small YORP probe
   
   Approach:
     • Book payload slot on Starship lunar mission (~$10-20M)
     • Build small YORP-specific probe (~$80M)
     • Starship delivers to lunar orbit or escape trajectory
     • Probe uses own propulsion for YORP transfer
   
   Total: ~$90-110M
   
   Advantages:
     ✓ Extremely low launch cost (Starship economics)
     ✓ Massive payload capacity (could send big probe)
     ✓ Can start closer to escape velocity
     ✓ Could piggyback on Artemis program missions
   
   Risk: Starship still in testing (but progressing fast)

═══════════════════════════════════════════════════════════════════════════════

3. ★★★☆☆ MODIFY A CUBESAT CONSTELLATION UNIT
   
   Who: Planet Labs, Spire, others
   Cost: $30-60M (heavy modification)
   
   Approach:
     • Start with large CubeSat platform (12U-27U)
     • Add ion propulsion module
     • Miniaturize science instruments
     • Accept limited capability
   
   Total: ~$50M
   
   Advantages:
     ✓ Lowest cost option
     ✓ Rapid development (commercial components)
     ✓ Could launch as secondary payload
   
   Disadvantages:
     ⚠ Limited science return (small instruments)
     ⚠ High risk (less redundancy)
     ⚠ May not achieve all objectives

═══════════════════════════════════════════════════════════════════════════════

4. ★★★★☆ PARTNER WITH ONGOING MISSION
   
   Example: Add YORP objective to existing NEO mission
   Cost: $20-50M (instrument package + trajectory modification)
   
   Approach:
     • Find mission already going to NEO region
     • Add YORP as secondary target
     • Share spacecraft bus and propulsion
     • Add specific YORP instruments
   
   This is how many discoveries happen!

═══════════════════════════════════════════════════════════════════════════════

RECOMMENDATION: COMMERCIAL LUNAR LANDER + ION STAGE

Best balance of cost, capability, and feasibility:
  • Total cost: ~$150-200M (vs $350M new build)
  • Savings: ~$150-200M (43-57% reduction)
  • Timeline: 3-4 years (vs 5-6 for new spacecraft)
  • Risk: Moderate (proven platforms, new integration)

Vendors to approach:
  1. Astrobotic (Peregrine platform) - Already flown
  2. Intuitive Machines (Nova-C) - Already flown
  3. iSpace (HAKUTO-R) - Platform exists
  4. Firefly Aerospace (Blue Ghost) - In development

═══════════════════════════════════════════════════════════════════════════════

BOTTOM LINE:

❌ Can't repurpose existing Earth satellites (wrong propulsion)
✅ CAN repurpose/modify commercial deep space platforms
✅ CAN use new launch paradigm (Starship) to reduce costs
✅ CAN partner with existing missions

Result: YORP mission for ~$100-200M instead of $350M! 🚀
""")


def main():
    print_header()
    analyze_orbit_requirements()
    analyze_candidate_satellites()
    analyze_specific_opportunities()
    print_recommendations()
    
    print("\n" + "="*100)
    print("FINAL VERDICT")
    print("="*100)
    print("""
You can't directly repurpose an existing Earth satellite...

BUT you CAN use the commercial space revolution to build YORP mission cheaper:
  • Buy commercial lunar lander bus: ~$30M
  • Add ion propulsion: ~$40M  
  • Add science payload: ~$30M
  • Integration & testing: ~$20M
  • Launch: ~$30M
  • Operations: ~$20M
  
TOTAL: ~$170M (less than half of traditional mission cost!)

The "repurposing" is really "buying commercial off-the-shelf + customization"
This is the NEW way asteroid missions will be done in the 2020s-2030s! 🌟
""")


if __name__ == '__main__':
    main()


