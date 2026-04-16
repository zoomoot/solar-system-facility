"""
JPL ↔ MPC Designation Matcher and Merger
Matches JPL objects with MPC objects and merges them into unified rows
"""

import pymysql
from pymysql.cursors import DictCursor
import re
import os
from datetime import datetime


DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'admin'),
    'password': os.environ.get('DB_PASSWORD', 'qeuWerty-2345'),
    'database': os.environ.get('DB_NAME', 'solar_system'),
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}


def get_db_connection():
    """Create database connection"""
    return pymysql.connect(**DB_CONFIG)


def normalize_designation(designation):
    """
    Normalize a designation to a standard format for matching
    
    Examples:
        "433" -> "00433"
        "Eros" -> "00433"
        "433 Eros" -> "00433"
        "2000 AA1" -> "2000 AA1"
        "1999 AN10" -> "1999 AN10"
    """
    if not designation:
        return None
    
    designation = str(designation).strip()
    
    # Extract numbered asteroid (e.g., "433", "433 Eros", "(433) Eros")
    numbered_match = re.match(r'^\(?(\d+)\)?', designation)
    if numbered_match:
        number = numbered_match.group(1)
        # Pad to 5 digits for MPC format
        return number.zfill(5)
    
    # Provisional designation (e.g., "2000 AA1", "1999 AN10")
    provisional_match = re.match(r'^(\d{4}\s+[A-Z]{2}\d+)', designation)
    if provisional_match:
        return provisional_match.group(1)
    
    # Return as-is if no pattern matches
    return designation


def find_jpl_mpc_matches(limit=None):
    """
    Find JPL objects that match MPC objects by designation
    Returns list of (jpl_id, mpc_id, designation) tuples
    
    Args:
        limit: Maximum number of JPL objects to process (None = all)
    """
    conn = get_db_connection()
    matches = []
    
    try:
        with conn.cursor() as cursor:
            # Get JPL objects with designations (asteroids only, comets won't match MPC)
            limit_clause = f"LIMIT {limit}" if limit else ""
            cursor.execute(f"""
                SELECT ID, SPKID, JPL_DESIGNATION, JPL_NAME, JPL_FULL_NAME
                FROM small_bodies
                WHERE SPKID IS NOT NULL
                  AND MPC_DESIGNATION IS NULL
                  AND JPL_SB_KIND = 'a'
                {limit_clause}
            """)
            jpl_objects = cursor.fetchall()
            
            print(f"Found {len(jpl_objects)} JPL-only objects to match")
            
            # For each JPL object, try to find matching MPC object
            for i, jpl_obj in enumerate(jpl_objects, 1):
                if i % 100 == 0:
                    print(f"  Progress: {i}/{len(jpl_objects)} ({i*100//len(jpl_objects)}%)")
                jpl_id = jpl_obj['ID']
                
                # Try multiple designation fields
                designations_to_try = [
                    jpl_obj.get('JPL_DESIGNATION'),
                    jpl_obj.get('JPL_NAME'),
                ]
                
                # Also extract from full name
                if jpl_obj.get('JPL_FULL_NAME'):
                    # Extract number from full name like "(433) Eros" or "433 Eros"
                    full_name = jpl_obj['JPL_FULL_NAME']
                    numbered_match = re.match(r'^\(?(\d+)\)?', full_name)
                    if numbered_match:
                        designations_to_try.append(numbered_match.group(1))
                
                # Try to match each designation
                for des in designations_to_try:
                    if not des:
                        continue
                    
                    normalized = normalize_designation(des)
                    if not normalized:
                        continue
                    
                    # Try to find MPC object with matching designation
                    cursor.execute("""
                        SELECT ID, MPC_DESIGNATION, MPC_NAME
                        FROM small_bodies
                        WHERE MPC_DESIGNATION IS NOT NULL
                          AND SPKID IS NULL
                          AND (
                              MPC_DESIGNATION = %s
                              OR MPC_NAME = %s
                          )
                        LIMIT 1
                    """, (normalized, des))
                    
                    mpc_obj = cursor.fetchone()
                    if mpc_obj:
                        matches.append({
                            'jpl_id': jpl_id,
                            'mpc_id': mpc_obj['ID'],
                            'jpl_designation': des,
                            'mpc_designation': mpc_obj['MPC_DESIGNATION'],
                            'normalized': normalized
                        })
                        print(f"Match found: JPL '{des}' -> MPC '{mpc_obj['MPC_DESIGNATION']}'")
                        break  # Found a match, stop trying other designations
            
            print(f"\nTotal matches found: {len(matches)}")
            return matches
    
    finally:
        conn.close()


def merge_jpl_into_mpc(jpl_id, mpc_id):
    """
    Merge JPL object data into MPC object row
    Updates the MPC row with JPL fields and deletes the JPL-only row
    """
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            # Get JPL object data
            cursor.execute("""
                SELECT * FROM small_bodies WHERE ID = %s
            """, (jpl_id,))
            jpl_obj = cursor.fetchone()
            
            if not jpl_obj:
                print(f"Error: JPL object {jpl_id} not found")
                return False
            
            # Update MPC row with JPL data
            cursor.execute("""
                UPDATE small_bodies
                SET 
                    SPKID = %s,
                    JPL_FULL_NAME = %s,
                    JPL_DESIGNATION = %s,
                    JPL_NAME = %s,
                    JPL_PREFIX = %s,
                    JPL_NEO = %s,
                    JPL_PHA = %s,
                    JPL_H = %s,
                    JPL_DIAMETER = %s,
                    JPL_ALBEDO = %s,
                    JPL_ROT_PER = %s,
                    JPL_GM = %s,
                    JPL_BV = %s,
                    JPL_UB = %s,
                    JPL_SPEC_B = %s,
                    JPL_SPEC_T = %s,
                    JPL_CONDITION_CODE = %s,
                    JPL_RMS = %s,
                    JPL_SB_KIND = %s,
                    JPL_SB_CLASS = %s,
                    JPL_ORBIT_CLASS = %s,
                    JPL_LAST_UPDATED = %s
                WHERE ID = %s
            """, (
                jpl_obj['SPKID'],
                jpl_obj['JPL_FULL_NAME'],
                jpl_obj['JPL_DESIGNATION'],
                jpl_obj['JPL_NAME'],
                jpl_obj['JPL_PREFIX'],
                jpl_obj['JPL_NEO'],
                jpl_obj['JPL_PHA'],
                jpl_obj['JPL_H'],
                jpl_obj['JPL_DIAMETER'],
                jpl_obj['JPL_ALBEDO'],
                jpl_obj['JPL_ROT_PER'],
                jpl_obj['JPL_GM'],
                jpl_obj['JPL_BV'],
                jpl_obj['JPL_UB'],
                jpl_obj['JPL_SPEC_B'],
                jpl_obj['JPL_SPEC_T'],
                jpl_obj['JPL_CONDITION_CODE'],
                jpl_obj['JPL_RMS'],
                jpl_obj['JPL_SB_KIND'],
                jpl_obj['JPL_SB_CLASS'],
                jpl_obj['JPL_ORBIT_CLASS'],
                jpl_obj['JPL_LAST_UPDATED'],
                mpc_id
            ))
            
            # Delete the JPL-only row
            cursor.execute("DELETE FROM small_bodies WHERE ID = %s", (jpl_id,))
            
            conn.commit()
            return True
    
    except Exception as e:
        conn.rollback()
        print(f"Error merging JPL {jpl_id} into MPC {mpc_id}: {e}")
        return False
    
    finally:
        conn.close()


def run_merge(load_id=None, limit=None):
    """
    Run the complete JPL ↔ MPC merge process
    
    Args:
        load_id: Optional load tracking ID
        limit: Maximum number of JPL objects to process (None = all)
    """
    print("=" * 80)
    print("JPL ↔ MPC Designation Matcher and Merger")
    print("=" * 80)
    print()
    
    if limit:
        print(f"⚠️  TEST MODE: Processing only {limit} objects")
        print()
    
    start_time = datetime.now()
    
    # Step 1: Find matches
    print("Step 1: Finding JPL ↔ MPC matches...")
    matches = find_jpl_mpc_matches(limit=limit)
    
    if not matches:
        print("\nNo matches found. Nothing to merge.")
        return {
            'matches_found': 0,
            'merged': 0,
            'failed': 0,
            'duration_seconds': 0
        }
    
    # Step 2: Merge matches
    print(f"\nStep 2: Merging {len(matches)} matched objects...")
    merged = 0
    failed = 0
    
    for i, match in enumerate(matches, 1):
        if i % 100 == 0:
            print(f"  Merged {i}/{len(matches)}...")
        
        success = merge_jpl_into_mpc(match['jpl_id'], match['mpc_id'])
        if success:
            merged += 1
        else:
            failed += 1
    
    # Step 3: Report results
    duration = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 80)
    print("Merge Complete!")
    print("=" * 80)
    print(f"Matches found:    {len(matches)}")
    print(f"Successfully merged: {merged}")
    print(f"Failed:           {failed}")
    print(f"Duration:         {duration:.1f} seconds")
    print()
    
    return {
        'matches_found': len(matches),
        'merged': merged,
        'failed': failed,
        'duration_seconds': duration
    }


if __name__ == '__main__':
    """Run the merge from command line"""
    result = run_merge()
    
    if result['failed'] > 0:
        exit(1)
    else:
        exit(0)

