"""
MPC MPCORB.DAT Parser and Loader
Parses the Minor Planet Center's MPCORB.DAT file and loads into MariaDB
"""

import pymysql
from pymysql.cursors import DictCursor
import re
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'admin',
    'password': 'qeuWerty-2345',
    'database': 'solar_system',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

def parse_mpcorb_line(line):
    """
    Parse a single line from MPCORB.DAT
    Format: http://www.minorplanetcenter.org/iau/info/MPOrbitFormat.html
    
    Fixed-width format:
    Columns  Format   Use
    1-7      A7       Designation
    9-13     F5.2     Absolute magnitude H
    15-19    F5.2     Slope parameter G
    21-25    A5       Epoch (packed form)
    27-35    F9.5     Mean anomaly (degrees)
    38-46    F9.5     Argument of perihelion (degrees)
    49-57    F9.5     Longitude of ascending node (degrees)
    60-68    F9.5     Inclination (degrees)
    71-79    F9.7     Eccentricity
    81-91    F11.8    Mean daily motion (degrees/day)
    93-103   F11.7    Semi-major axis (AU)
    106-116  A11      Reference
    118-122  I5       Number of observations
    124-126  I3       Number of oppositions
    129-136  A8       Arc of observations
    138-141  F4.2     RMS residual
    143-145  A3       Coarse indicator of perturbers
    147-149  A3       Precise indicator of perturbers
    151-160  A10      Computer name
    162-165  I4       4-digit flags
    167-194  A28      Readable designation
    196-202  I7       Last observation date (YYYYMMDD)
    """
    
    if len(line) < 160:
        return None
    
    try:
        # Extract fields using fixed positions
        designation = line[0:7].strip()
        h = float(line[8:13].strip()) if line[8:13].strip() else None
        g = float(line[14:19].strip()) if line[14:19].strip() else None
        epoch = line[20:25].strip()
        m = float(line[26:35].strip()) if line[26:35].strip() else None
        peri = float(line[37:46].strip()) if line[37:46].strip() else None
        node = float(line[48:57].strip()) if line[48:57].strip() else None
        incl = float(line[59:68].strip()) if line[59:68].strip() else None
        e = float(line[70:79].strip()) if line[70:79].strip() else None
        n = float(line[80:91].strip()) if line[80:91].strip() else None
        a = float(line[92:103].strip()) if line[92:103].strip() else None
        reference = line[105:116].strip()
        num_obs = int(line[117:122].strip()) if line[117:122].strip() else None
        num_opp = int(line[123:126].strip()) if line[123:126].strip() else None
        arc = line[127:136].strip()
        rms = float(line[137:141].strip()) if line[137:141].strip() else None
        perturbers_coarse = line[142:145].strip()
        perturbers_precise = line[146:149].strip()
        perturbers = f"{perturbers_coarse} {perturbers_precise}".strip()
        computer = line[150:160].strip()
        flags = line[161:165].strip() if len(line) > 165 else None
        name = line[166:194].strip() if len(line) > 194 else None
        
        return {
            'designation': designation,
            'h': h,
            'g': g,
            'epoch': epoch,
            'm': m,
            'peri': peri,
            'node': node,
            'incl': incl,
            'e': e,
            'n': n,
            'a': a,
            'reference': reference,
            'num_obs': num_obs,
            'num_opp': num_opp,
            'arc': arc,
            'rms': rms,
            'perturbers': perturbers,
            'computer': computer,
            'flags': flags,
            'name': name
        }
    except Exception as e:
        print(f"Error parsing line: {e}")
        print(f"Line: {line[:100]}")
        return None

def load_mpcorb(filename='MPCORB.DAT', batch_size=1000):
    """Load MPCORB.DAT into database"""
    
    print("="*60)
    print("MPC MPCORB.DAT Loader")
    print("="*60)
    
    conn = pymysql.connect(**DB_CONFIG)
    
    try:
        with conn.cursor() as cursor:
            # Start load tracking
            cursor.execute("""
                INSERT INTO load_history (SOURCE, LOAD_TYPE, STATUS, STARTED_AT)
                VALUES ('MPC', 'full', 'running', NOW())
            """)
            conn.commit()
            load_id = cursor.lastrowid
            
            print(f"Load ID: {load_id}")
            print(f"Reading {filename}...")
            
            added = 0
            updated = 0
            failed = 0
            skipped = 0
            batch = []
            
            with open(filename, 'r', encoding='latin-1') as f:
                for line_num, line in enumerate(f, 1):
                    # Skip header lines
                    if line_num < 44:
                        continue
                    
                    # Skip blank lines
                    if not line.strip():
                        continue
                    
                    # Parse line
                    obj = parse_mpcorb_line(line)
                    if not obj:
                        skipped += 1
                        continue
                    
                    batch.append(obj)
                    
                    # Insert batch
                    if len(batch) >= batch_size:
                        result = insert_batch(cursor, batch)
                        added += result['added']
                        updated += result['updated']
                        failed += result['failed']
                        
                        conn.commit()
                        
                        # Update progress
                        cursor.execute("""
                            UPDATE load_history 
                            SET OBJECTS_PROCESSED = %s,
                                OBJECTS_ADDED = %s,
                                OBJECTS_UPDATED = %s,
                                OBJECTS_FAILED = %s
                            WHERE ID = %s
                        """, (added + updated + failed, added, updated, failed, load_id))
                        conn.commit()
                        
                        print(f"Progress: {added + updated:,} objects loaded ({failed} failed, {skipped} skipped)")
                        
                        batch = []
                
                # Insert remaining batch
                if batch:
                    result = insert_batch(cursor, batch)
                    added += result['added']
                    updated += result['updated']
                    failed += result['failed']
                    conn.commit()
            
            # Complete load tracking
            cursor.execute("""
                UPDATE load_history 
                SET STATUS = 'completed',
                    COMPLETED_AT = NOW(),
                    DURATION_SECONDS = TIMESTAMPDIFF(SECOND, STARTED_AT, NOW()),
                    OBJECTS_PROCESSED = %s,
                    OBJECTS_ADDED = %s,
                    OBJECTS_UPDATED = %s,
                    OBJECTS_FAILED = %s
                WHERE ID = %s
            """, (added + updated + failed, added, updated, failed, load_id))
            conn.commit()
            
            print("="*60)
            print(f"✅ Load Complete!")
            print(f"   Added: {added:,}")
            print(f"   Updated: {updated:,}")
            print(f"   Failed: {failed:,}")
            print(f"   Skipped: {skipped:,}")
            print("="*60)
            
    finally:
        conn.close()

def insert_batch(cursor, batch):
    """Insert a batch of objects"""
    added = 0
    updated = 0
    failed = 0
    
    for obj in batch:
        try:
            cursor.execute("""
                INSERT INTO small_bodies (
                    MPC_DESIGNATION, MPC_H, MPC_G, MPC_EPOCH, MPC_M, MPC_PERI,
                    MPC_NODE, MPC_INCL, MPC_E, MPC_N, MPC_A, MPC_REFERENCE,
                    MPC_NUM_OBS, MPC_NUM_OPP, MPC_ARC, MPC_RMS, MPC_PERTURBERS,
                    MPC_COMPUTER, MPC_FLAGS, MPC_NAME, MPC_LAST_UPDATED
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )
                ON DUPLICATE KEY UPDATE
                    MPC_H = VALUES(MPC_H),
                    MPC_G = VALUES(MPC_G),
                    MPC_EPOCH = VALUES(MPC_EPOCH),
                    MPC_M = VALUES(MPC_M),
                    MPC_PERI = VALUES(MPC_PERI),
                    MPC_NODE = VALUES(MPC_NODE),
                    MPC_INCL = VALUES(MPC_INCL),
                    MPC_E = VALUES(MPC_E),
                    MPC_N = VALUES(MPC_N),
                    MPC_A = VALUES(MPC_A),
                    MPC_REFERENCE = VALUES(MPC_REFERENCE),
                    MPC_NUM_OBS = VALUES(MPC_NUM_OBS),
                    MPC_NUM_OPP = VALUES(MPC_NUM_OPP),
                    MPC_ARC = VALUES(MPC_ARC),
                    MPC_RMS = VALUES(MPC_RMS),
                    MPC_PERTURBERS = VALUES(MPC_PERTURBERS),
                    MPC_COMPUTER = VALUES(MPC_COMPUTER),
                    MPC_FLAGS = VALUES(MPC_FLAGS),
                    MPC_NAME = VALUES(MPC_NAME),
                    MPC_LAST_UPDATED = NOW()
            """, (
                obj['designation'], obj['h'], obj['g'], obj['epoch'], obj['m'], obj['peri'],
                obj['node'], obj['incl'], obj['e'], obj['n'], obj['a'], obj['reference'],
                obj['num_obs'], obj['num_opp'], obj['arc'], obj['rms'], obj['perturbers'],
                obj['computer'], obj['flags'], obj['name']
            ))
            
            if cursor.rowcount == 1:
                added += 1
            else:
                updated += 1
                
        except Exception as e:
            failed += 1
            if failed < 10:  # Only print first 10 errors
                print(f"Error inserting {obj.get('designation')}: {e}")
    
    return {'added': added, 'updated': updated, 'failed': failed}

if __name__ == '__main__':
    import sys
    filename = sys.argv[1] if len(sys.argv) > 1 else 'MPCORB.DAT'
    load_mpcorb(filename)




