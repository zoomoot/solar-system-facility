"""
Test script for Visual Survey Search system
Demonstrates how to use the new survey search components
"""

from surveys import get_survey_client, SURVEY_REGISTRY, get_available_surveys
from ephemeris_generator import EphemerisGenerator
from datetime import datetime, timedelta


def test_panstarrs_single_position():
    """Test Pan-STARRS cutout retrieval for a single position"""
    print("=" * 70)
    print("TEST 1: Pan-STARRS Single Position Cutout")
    print("=" * 70)
    
    # Get Pan-STARRS client
    ps_client = get_survey_client('panstarrs')
    
    if ps_client is None:
        print("❌ Pan-STARRS client not available")
        return
    
    print(f"✓ Client: {ps_client.name}")
    print(f"✓ Coverage: δ > -30°")
    print(f"✓ Depth: {ps_client.limiting_magnitude} mag")
    print()
    
    # Test position: 433 Eros current position (approximate)
    ra = 45.123  # degrees
    dec = 15.456  # degrees
    
    print(f"Testing position: RA={ra}°, Dec={dec}°")
    
    # Check coverage
    in_footprint = ps_client.check_coverage(ra, dec)
    print(f"In footprint: {in_footprint}")
    
    if in_footprint:
        # Request cutout
        print("\nRequesting r-band cutout...")
        cutout = ps_client.get_cutout(ra, dec, size=60.0, band='r')
        
        if cutout:
            print("✓ Cutout retrieved!")
            print(f"  URL: {cutout['image_url']}")
            print(f"  Filter: {cutout['filter']}")
            print(f"  Size: {cutout['size_arcsec']} arcsec")
        else:
            print("❌ No cutout available")
    
    print()


def test_ephemeris_generation():
    """Test ephemeris generation for 433 Eros"""
    print("=" * 70)
    print("TEST 2: Ephemeris Generation (JPL Horizons)")
    print("=" * 70)
    
    ephem_gen = EphemerisGenerator()
    
    # Generate ephemeris for 433 Eros in 2020
    print("Generating ephemeris for 433 Eros (2020)")
    print("Time range: 2020-01-01 to 2020-12-31")
    print("Step: 7 days")
    print()
    
    ephemeris = ephem_gen.generate(
        designation='433',
        start_date='2020-01-01',
        end_date='2020-12-31',
        step='7d'
    )
    
    if ephemeris:
        print(f"✓ Generated {len(ephemeris)} ephemeris points")
        print("\nSample (first 3 points):")
        for point in ephemeris[:3]:
            print(f"  {point['time']}: RA={point['ra']:.4f}°, Dec={point['dec']:.4f}°, Vmag={point['vmag']}")
    else:
        print("❌ Failed to generate ephemeris")
    
    print()
    return ephemeris


def test_survey_search():
    """Test full survey search workflow"""
    print("=" * 70)
    print("TEST 3: Full Survey Search for 433 Eros")
    print("=" * 70)
    
    # Generate ephemeris
    print("Step 1: Generate ephemeris...")
    ephem_gen = EphemerisGenerator()
    ephemeris = ephem_gen.generate(
        designation='433',
        start_date='2020-06-01',
        end_date='2020-06-07',
        step='1d'
    )
    
    if not ephemeris:
        print("❌ Failed to generate ephemeris")
        return
    
    print(f"✓ Generated {len(ephemeris)} positions")
    print()
    
    # Search Pan-STARRS
    print("Step 2: Search Pan-STARRS...")
    ps_client = get_survey_client('panstarrs')
    
    if ps_client:
        results = ps_client.search_ephemeris(ephemeris, sample_rate=1)
        print(f"✓ Found {len(results)} potential images")
        
        if results:
            print("\nSample results:")
            for i, result in enumerate(results[:3]):
                print(f"  {i+1}. {result['filter']}-band at RA={result['ra']:.4f}°, Dec={result['dec']:.4f}°")
                print(f"     URL: {result['image_url']}")
    else:
        print("❌ Pan-STARRS client not available")
    
    print()


def test_survey_registry():
    """Test survey registry"""
    print("=" * 70)
    print("TEST 4: Survey Registry")
    print("=" * 70)
    
    available = get_available_surveys()
    
    print(f"Available surveys: {len(available)}")
    for survey in available:
        print(f"\n  • {survey['name']} ({survey['id']})")
        print(f"    Years: {survey['years'][0]}-{survey['years'][1]}")
        print(f"    Bands: {', '.join(survey['bands'])}")
        print(f"    Priority: {survey['priority']}/5")
        print(f"    Status: {survey['status']}")
    
    print(f"\nPlanned surveys: {len(SURVEY_REGISTRY) - len(available)}")
    for survey_id, info in SURVEY_REGISTRY.items():
        if info['client_class'] is None:
            print(f"  • {info['name']} (coming soon)")
    
    print()


if __name__ == '__main__':
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║      Visual Survey Search System - Test Suite                     ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Run tests
    test_survey_registry()
    test_panstarrs_single_position()
    
    # Uncomment to test ephemeris generation (requires internet)
    # test_ephemeris_generation()
    
    # Uncomment to test full survey search (requires internet)
    # test_survey_search()
    
    print("=" * 70)
    print("Tests complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Uncomment ephemeris tests and run with internet connection")
    print("  2. Test with real objects (433, 99942, 1I, etc.)")
    print("  3. Integrate into Streamlit app")
    print("  4. Add ZTF support")
    print()
