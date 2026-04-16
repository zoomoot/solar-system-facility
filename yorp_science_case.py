#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scientific Case for Orbiting Asteroid 54509 YORP
Why this small asteroid is scientifically important
"""

# YORP Physical Properties (from observations)
YORP_PROPERTIES = {
    'name': '54509 YORP (2000 PH5)',
    'diameter': 0.13,  # km (130 meters)
    'rotation_period': 0.2027,  # hours (12.1 minutes) - VERY FAST!
    'rotation_acceleration': 2.0e-4,  # deg/day² - MEASURED SPIN-UP!
    'shape': 'Highly irregular, angular',
    'spectral_type': 'Q-type (ordinary chondrite)',
    'albedo': 0.24,  # Moderately bright
    'density_estimate': 2.5,  # g/cm³ (estimated)
    'surface_features': 'Angular facets, possible boulder fields',
    
    # Orbital characteristics
    'orbit_class': 'Aten (Earth-crossing)',
    'discovery': '2000 (LINEAR survey)',
}

def print_science_case():
    """Print the comprehensive scientific case for YORP mission"""
    
    print("="*100)
    print(" " * 30 + "SCIENTIFIC CASE FOR ORBITING YORP")
    print(" " * 28 + "Why This Small Asteroid Matters")
    print("="*100)
    
    print("\n" + "="*100)
    print("1. YORP IS THE NAMESAKE OF THE 'YORP EFFECT' - A FUNDAMENTAL DISCOVERY")
    print("="*100)
    
    print("""
★★★ YORP is SCIENTIFICALLY FAMOUS ★★★

This asteroid is named for the scientists who discovered the YORP effect:
  • Yarkovsky–O'Keefe–Radzievskii–Paddack Effect

What is the YORP Effect?
  → Sunlight hitting an irregularly-shaped asteroid creates tiny torques
  → These torques can spin up or slow down the asteroid's rotation
  → Over time, this can dramatically change the asteroid's spin state
  
Why is this important?
  ✓ Affects asteroid evolution over millions of years
  ✓ Can cause asteroids to split apart (creating binary systems)
  ✓ Changes orbital paths slightly (related to Yarkovsky effect)
  ✓ Critical for understanding asteroid populations
  
YORP (the asteroid) was the FIRST object where this effect was MEASURED!
  • Rotation period: 12.1 minutes (very fast!)
  • Spin-up rate: 2×10⁻⁴ deg/day² (measurable over years)
  • Confirmed predictions from theoretical models
  
This made asteroid 2000 PH5 famous enough to be renamed "54509 YORP"!
""")

    print("\n" + "="*100)
    print("2. PRIMARY SCIENCE OBJECTIVES FOR YORP ORBITER MISSION")
    print("="*100)
    
    objectives = [
        {
            'title': 'Measure YORP Effect in Detail',
            'priority': 'PRIMARY',
            'description': [
                'Precisely track rotation changes over mission duration',
                'Map surface thermal properties to understand torque distribution',
                'Validate/refine theoretical models of YORP effect',
                'Determine if spin-up will eventually cause asteroid to shed mass',
            ],
            'instruments': ['High-precision tracking', 'Thermal IR camera', 'Laser altimeter'],
            'value': 'Fundamental physics - applicable to ALL small asteroids'
        },
        {
            'title': 'Study Fast Rotator Dynamics',
            'priority': 'PRIMARY',
            'description': [
                'YORP rotates every 12.1 minutes - one of the fastest known',
                'Understand how rubble pile asteroids hold together at high spin',
                'Measure changes in shape due to centrifugal forces',
                'Look for mass shedding from equatorial bulge',
            ],
            'instruments': ['Shape model camera', 'Gravity field mapper', 'Dust detector'],
            'value': 'Critical for understanding asteroid internal structure'
        },
        {
            'title': 'Search for Binary Formation',
            'priority': 'PRIMARY',
            'description': [
                'YORP spinning up may eventually fission into binary system',
                'Look for early signs: mass shedding, satellite formation',
                'Monitor for debris or dust release from surface',
                'Could witness binary asteroid birth!',
            ],
            'instruments': ['Wide-field camera', 'Particle detectors', 'Long-term monitoring'],
            'value': 'Rare opportunity to study binary asteroid formation in real-time'
        },
        {
            'title': 'Characterize Small Asteroid Properties',
            'priority': 'HIGH',
            'description': [
                'Mass and density determination (gravity measurements)',
                'Surface composition (spectroscopy)',
                'Shape and morphology (high-res imaging)',
                'Thermal properties and regolith characterization',
            ],
            'instruments': ['Spectrometer', 'Thermal mapper', 'Camera suite', 'Radio science'],
            'value': '130m asteroids are poorly studied - fills major knowledge gap'
        },
        {
            'title': 'Planetary Defense Applications',
            'priority': 'HIGH',
            'description': [
                'YORP is potentially hazardous (Aten orbit crosses Earth)',
                'Understanding spin dynamics critical for deflection planning',
                'Small size typical of most threatening objects',
                'Test technologies for future deflection missions',
            ],
            'instruments': ['All science instruments contribute'],
            'value': 'Directly applicable to defending Earth from asteroid impacts'
        },
        {
            'title': 'Test In-Situ Resource Utilization (ISRU)',
            'priority': 'MEDIUM',
            'description': [
                'Small NEO is ideal testbed for mining/resource extraction',
                'Low gravity makes landing/sampling easy',
                'Q-type composition suggests water-bearing minerals',
                'Could deploy experimental mining equipment',
            ],
            'instruments': ['Sample collection arm', 'Chemical analyzer', 'Landing probe'],
            'value': 'Technology development for asteroid mining industry'
        },
    ]
    
    for i, obj in enumerate(objectives, 1):
        print(f"\n{'─'*100}")
        print(f"Objective {i}: {obj['title']}")
        print(f"Priority: {obj['priority']}")
        print(f"{'─'*100}")
        print("\nGoals:")
        for desc in obj['description']:
            print(f"  • {desc}")
        print(f"\nKey Instruments: {', '.join(obj['instruments'])}")
        print(f"Scientific Value: {obj['value']}")
    
    print("\n\n" + "="*100)
    print("3. UNIQUE ADVANTAGES OF YORP AS A TARGET")
    print("="*100)
    
    advantages = [
        ("Low Delta-v", "7.7 km/s - easier to reach than the Moon!", "Reduces cost, increases payload capacity"),
        ("Annual Close Approaches", "Returns near Earth every year", "Frequent data downlink opportunities, mission flexibility"),
        ("Small Size", "Only 130 meters across", "Easy to orbit, low risk, thorough characterization possible"),
        ("Fast Rotation", "Spins every 12 minutes", "Observe entire surface in short time, study dynamics"),
        ("Active Evolution", "Measurably spinning up!", "Rare chance to observe asteroid changing in real-time"),
        ("Q-type Composition", "Fresh, unweathered surface", "Reveals pristine asteroid interior material"),
        ("Already Well-Studied", "Ground observations since 2000", "Excellent baseline data, reduce risk"),
        ("Safe Orbit", "PHAs need monitoring", "Dual purpose: science + planetary defense tracking"),
    ]
    
    print()
    for i, (title, description, benefit) in enumerate(advantages, 1):
        print(f"{i}. {title:.<25} {description}")
        print(f"   {'Benefit:':<25} {benefit}\n")
    
    print("\n" + "="*100)
    print("4. MISSION SCIENCE PAYLOAD (Proposed)")
    print("="*100)
    
    instruments = [
        {
            'name': 'High-Resolution Camera Suite',
            'mass': 8,  # kg
            'power': 15,  # W
            'purpose': 'Shape modeling, surface features, monitoring changes',
            'resolution': '<10 cm/pixel',
        },
        {
            'name': 'Thermal Infrared Mapper',
            'mass': 12,
            'power': 25,
            'purpose': 'Surface temperature, thermal inertia, YORP torque mapping',
            'resolution': '1 meter thermal resolution',
        },
        {
            'name': 'Visible/Near-IR Spectrometer',
            'mass': 6,
            'power': 20,
            'purpose': 'Composition, mineralogy, water detection',
            'resolution': '400-2500 nm wavelength range',
        },
        {
            'name': 'Laser Altimeter (LIDAR)',
            'mass': 5,
            'power': 30,
            'purpose': 'Precise shape model, topography, ranging',
            'resolution': '5 cm vertical accuracy',
        },
        {
            'name': 'Radio Science Package',
            'mass': 3,
            'power': 10,
            'purpose': 'Gravity field, mass determination, orbit tracking',
            'resolution': 'Mass accurate to ~1%',
        },
        {
            'name': 'Dust/Particle Detector',
            'mass': 2,
            'power': 5,
            'purpose': 'Detect mass shedding, ejecta, dust cloud',
            'resolution': 'Particles >1 micron',
        },
        {
            'name': 'X-band Communication System',
            'mass': 8,
            'power': 50,
            'purpose': 'Data downlink, precision tracking',
            'resolution': '1-10 kbps at 1 AU',
        },
        {
            'name': 'Optional: Landing Probe',
            'mass': 15,
            'power': 0,
            'purpose': 'Surface contact science, sample analysis',
            'resolution': 'In-situ measurements',
        },
    ]
    
    total_mass = sum(i['mass'] for i in instruments)
    total_power = sum(i['power'] for i in instruments[:-1])  # Exclude optional lander
    
    print()
    print(f"{'Instrument':<35}{'Mass':<10}{'Power':<10}{'Primary Purpose'}")
    print(f"{'Name':<35}{'(kg)':<10}{'(W)':<10}{''}")
    print("─"*100)
    
    for inst in instruments[:-1]:  # All except optional
        print(f"{inst['name']:<35}{inst['mass']:<10}{inst['power']:<10}{inst['purpose']}")
    
    print("─"*100)
    print(f"{'TOTAL CORE PAYLOAD':<35}{total_mass:<10}{total_power:<10}")
    print(f"\n{'OPTIONAL: Landing Probe':<35}{instruments[-1]['mass']:<10}{'N/A':<10}{instruments[-1]['purpose']}")
    
    print("\n\n" + "="*100)
    print("5. EXPECTED SCIENTIFIC DISCOVERIES")
    print("="*100)
    
    discoveries = [
        ("YORP Effect Validation", "Confirm theoretical models with unprecedented precision"),
        ("Binary Formation Mechanism", "First direct observation of asteroid fission process"),
        ("Internal Structure", "Rubble pile vs monolithic - crucial for deflection"),
        ("Surface Evolution", "How fast rotation reshapes small asteroids"),
        ("Mass Shedding Events", "Capture actual moments of material ejection"),
        ("Thermal Properties", "How surface texture affects YORP torques"),
        ("Regolith Behavior", "How dust behaves in micro-gravity + high spin"),
        ("Composition Details", "Pristine Q-type material analysis"),
    ]
    
    print("\nAnticipated Major Results:\n")
    for i, (discovery, description) in enumerate(discoveries, 1):
        print(f"  {i}. {discovery}")
        print(f"     → {description}\n")
    
    print("\n" + "="*100)
    print("6. COMPARISON TO OTHER ASTEROID MISSIONS")
    print("="*100)
    
    missions = [
        ("NEAR Shoemaker", "433 Eros", "17 km", "First asteroid orbit & landing", "$212M"),
        ("Hayabusa", "25143 Itokawa", "0.3 km", "Sample return from small NEO", "$170M"),
        ("Dawn", "Vesta & Ceres", "525/940 km", "First ion drive to asteroids", "$467M"),
        ("OSIRIS-REx", "101955 Bennu", "0.5 km", "Sample return, detailed study", "$800M"),
        ("Hayabusa2", "162173 Ryugu", "0.9 km", "Sample return, landers", "$260M"),
        ("DART", "Dimorphos", "0.16 km", "Kinetic impactor test", "$324M"),
        ("Psyche", "16 Psyche", "226 km", "Metal asteroid orbiter", "$850M"),
        ("YORP MISSION", "54509 YORP", "0.13 km", "YORP effect & fast rotator", "$350M est."),
    ]
    
    print()
    print(f"{'Mission':<20}{'Target':<20}{'Size':<12}{'Purpose':<35}{'Cost'}")
    print("─"*100)
    
    for mission, target, size, purpose, cost in missions:
        if mission == "YORP MISSION":
            print("─"*100)
        print(f"{mission:<20}{target:<20}{size:<12}{purpose:<35}{cost}")
    
    print("\n★ YORP mission would be Discovery-class (~$350M) - competitive with Hayabusa, Dawn")
    
    print("\n\n" + "="*100)
    print("7. BROADER IMPACT & LEGACY")
    print("="*100)
    
    print("""
Scientific Impact:
  • Validate fundamental theory affecting ALL small asteroids
  • Improve models used for orbital predictions (planetary defense)
  • Understand evolution of asteroid families
  • Provide ground truth for remote observations
  
Practical Applications:
  • Refine asteroid deflection techniques (YORP affects trajectories)
  • Test technologies for asteroid mining missions
  • Demonstrate low-cost NEO exploration architecture
  • Train next generation of asteroid mission scientists
  
Public Engagement:
  • Named asteroid with interesting story (YORP effect namesake)
  • Fast rotation = dramatic images (full rotation every 12 minutes!)
  • Potential to witness rare events (binary formation, mass shedding)
  • Clear planetary defense relevance (PHA monitoring)
  
Technology Heritage:
  • Prove ion drive + solar for ultra-cheap NEO missions
  • Test autonomous navigation for small body proximity ops
  • Develop techniques for fast-rotator orbiting
  • Pathfinder for future swarm missions to multiple NEOs
""")
    
    print("\n" + "="*100)
    print("MISSION PRIORITY ASSESSMENT")
    print("="*100)
    
    print("""
Scientific Priority:    ★★★★★ (5/5) - Fundamental physics discovery
Technical Feasibility:  ★★★★★ (5/5) - Low delta-v, proven technology
Cost Effectiveness:     ★★★★☆ (4/5) - Discovery-class, high return
Risk Level:             ★★★★☆ (4/5) - Low (small, accessible, well-known)
Public Interest:        ★★★★☆ (4/5) - Named asteroid, clear purpose
Planetary Defense:      ★★★★☆ (4/5) - PHA characterization, deflection testing

OVERALL MISSION VALUE:  ★★★★★ (HIGHLY RECOMMENDED)

Recommendation:
  → YORP should be a HIGH PRIORITY target for the next Discovery-class mission
  → Unique combination of accessibility, scientific importance, and practical value
  → Low cost enables potential for additional objectives (sample return, lander, etc.)
  → Time-sensitive: YORP is actively evolving - better to study now than later!
""")
    
    print("\n" + "="*100)
    print("BOTTOM LINE")
    print("="*100)
    
    print("""
Why orbit YORP?

1. It's the MOST FAMOUS small asteroid for a fundamental physics discovery
2. It's CHANGING RIGHT NOW - rare opportunity to observe evolution
3. It's CHEAP to reach - more science per dollar
4. It fills a CRITICAL gap - we know little about 100m-class asteroids
5. It's RELEVANT - potential impact threat, deflection testing, mining testbed
6. It's ACTIVE - may witness binary formation or mass shedding events

YORP is not just another rock - it's a natural laboratory for understanding
how ALL small asteroids work, evolve, and potentially threaten Earth.

And we can get there for less energy than going to the Moon! 🚀✨
""")


if __name__ == '__main__':
    print_science_case()


