"""
Test viewing merged data from solar_system database
Shows a few sample objects with both JPL and MPC data
"""

import pymysql
from pymysql.cursors import DictCursor

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'admin',
    'password': 'qeuWerty-2345',
    'database': 'solar_system',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

def view_sample_objects():
    conn = pymysql.connect(**DB_CONFIG)
    
    try:
        with conn.cursor() as cursor:
            print("=" * 100)
            print("DATABASE: solar_system")
            print("=" * 100)
            
            # Check what we have
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN SPKID IS NOT NULL THEN 1 ELSE 0 END) as jpl_only,
                    SUM(CASE WHEN MPC_DESIGNATION IS NOT NULL AND SPKID IS NULL THEN 1 ELSE 0 END) as mpc_only,
                    SUM(CASE WHEN SPKID IS NOT NULL AND MPC_DESIGNATION IS NOT NULL THEN 1 ELSE 0 END) as merged
                FROM small_bodies
            """)
            stats = cursor.fetchone()
            
            print(f"\n📊 DATABASE STATISTICS:")
            print(f"  Total rows: {stats['total']:,}")
            print(f"  JPL only: {stats['jpl_only']:,}")
            print(f"  MPC only: {stats['mpc_only']:,}")
            print(f"  Both (merged): {stats['merged']:,}")
            
            # Show sample JPL objects
            print(f"\n\n🔭 SAMPLE JPL OBJECTS (First 5):")
            print("-" * 100)
            cursor.execute("""
                SELECT 
                    SPKID,
                    JPL_FULL_NAME,
                    JPL_DESIGNATION,
                    JPL_DIAMETER,
                    JPL_NEO,
                    JPL_PHA,
                    JPL_SB_CLASS,
                    MPC_DESIGNATION,
                    MPC_A,
                    MPC_E,
                    MPC_INCL
                FROM small_bodies
                WHERE SPKID IS NOT NULL
                LIMIT 5
            """)
            
            for obj in cursor.fetchall():
                print(f"\nSPKID: {obj['SPKID']}")
                print(f"  Name: {obj['JPL_FULL_NAME']}")
                print(f"  Designation: {obj['JPL_DESIGNATION']}")
                print(f"  Diameter: {obj['JPL_DIAMETER']} km" if obj['JPL_DIAMETER'] else "  Diameter: Unknown")
                print(f"  NEO: {obj['JPL_NEO']}, PHA: {obj['JPL_PHA']}")
                print(f"  Class: {obj['JPL_SB_CLASS']}")
                print(f"  MPC Match: {obj['MPC_DESIGNATION']}" if obj['MPC_DESIGNATION'] else "  MPC Match: None")
                if obj['MPC_A']:
                    print(f"  Orbital Elements: a={obj['MPC_A']}, e={obj['MPC_E']}, i={obj['MPC_INCL']}°")
            
            # Show sample MPC objects
            print(f"\n\n📊 SAMPLE MPC OBJECTS (First 5):")
            print("-" * 100)
            cursor.execute("""
                SELECT 
                    MPC_DESIGNATION,
                    MPC_NAME,
                    MPC_A,
                    MPC_E,
                    MPC_INCL,
                    MPC_H
                FROM small_bodies
                WHERE MPC_DESIGNATION IS NOT NULL
                LIMIT 5
            """)
            
            for obj in cursor.fetchall():
                print(f"\nMPC Designation: {obj['MPC_DESIGNATION']}")
                print(f"  Name: {obj['MPC_NAME']}" if obj['MPC_NAME'] else "  Name: Unnamed")
                print(f"  Semi-major axis: {obj['MPC_A']} AU")
                print(f"  Eccentricity: {obj['MPC_E']}")
                print(f"  Inclination: {obj['MPC_INCL']}°")
                print(f"  Absolute magnitude: {obj['MPC_H']}")
            
            # Check for famous objects
            print(f"\n\n⭐ FAMOUS OBJECTS:")
            print("-" * 100)
            
            famous = ['433', 'Eros', 'Ceres', 'Vesta', 'Pallas', 'Bennu', 'Apophis', '99942']
            
            for name in famous:
                cursor.execute("""
                    SELECT 
                        SPKID,
                        JPL_FULL_NAME,
                        JPL_DIAMETER,
                        JPL_NEO,
                        MPC_DESIGNATION,
                        MPC_A,
                        MPC_E
                    FROM small_bodies
                    WHERE JPL_FULL_NAME LIKE %s 
                       OR JPL_DESIGNATION LIKE %s
                       OR JPL_NAME LIKE %s
                    LIMIT 1
                """, (f'%{name}%', f'%{name}%', f'%{name}%'))
                
                obj = cursor.fetchone()
                if obj:
                    print(f"\n{obj['JPL_FULL_NAME']}:")
                    print(f"  SPKID: {obj['SPKID']}")
                    print(f"  Diameter: {obj['JPL_DIAMETER']} km" if obj['JPL_DIAMETER'] else "  Diameter: Unknown")
                    print(f"  NEO: {obj['JPL_NEO']}")
                    print(f"  MPC: {obj['MPC_DESIGNATION']}" if obj['MPC_DESIGNATION'] else "  MPC: Not matched")
                    if obj['MPC_A']:
                        print(f"  Orbit: a={obj['MPC_A']} AU, e={obj['MPC_E']}")
            
    finally:
        conn.close()

if __name__ == '__main__':
    view_sample_objects()
