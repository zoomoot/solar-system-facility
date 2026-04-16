"""
Solar System Small Bodies Database Loader
Separate application for loading and merging data from multiple sources into MariaDB
Port: 5060 (separate from main app on 5050)
"""

import os
import sys
import time
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import pymysql
from pymysql.cursors import DictCursor
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

app = Flask(__name__)
CORS(app)

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'admin'),
    'password': os.environ.get('DB_PASSWORD', 'qeuWerty-2345'),
    'database': os.environ.get('DB_NAME', 'solar_system'),
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

# Global state for tracking loads
current_loads = {}

def get_db_connection():
    """Create database connection"""
    return pymysql.connect(**DB_CONFIG)

def start_load_tracking(source, load_type):
    """Start tracking a load operation"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO load_history (SOURCE, LOAD_TYPE, STATUS, STARTED_AT)
                VALUES (%s, %s, 'running', NOW())
            """, (source, load_type))
            conn.commit()
            return cursor.lastrowid
    finally:
        conn.close()

def update_load_tracking(load_id, **kwargs):
    """Update load tracking record"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            updates = []
            values = []
            
            for key, value in kwargs.items():
                updates.append(f"{key} = %s")
                values.append(value)
            
            if updates:
                values.append(load_id)
                sql = f"UPDATE load_history SET {', '.join(updates)} WHERE ID = %s"
                cursor.execute(sql, values)
                conn.commit()
    finally:
        conn.close()

def complete_load_tracking(load_id, status='completed', error_message=None):
    """Complete a load operation"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE load_history 
                SET STATUS = %s, 
                    COMPLETED_AT = NOW(),
                    DURATION_SECONDS = TIMESTAMPDIFF(SECOND, STARTED_AT, NOW()),
                    ERROR_MESSAGE = %s
                WHERE ID = %s
            """, (status, error_message, load_id))
            conn.commit()
    finally:
        conn.close()

class JPLLoader:
    """Loader for JPL SBDB data"""
    
    def __init__(self):
        self.base_url = "https://ssd-api.jpl.nasa.gov"
        self.session = requests.Session()
        self.session.verify = False  # SSL cert issue workaround
    
    def load_objects(self, sb_kind='a', sb_class=None, limit=100000, load_id=None):
        """Load objects from JPL SBDB"""
        try:
            # Build query URL
            url = f"{self.base_url}/sbdb_query.api"
            params = {
                'sb-kind': sb_kind,
                'limit': limit,
                'fields': 'spkid,full_name,pdes,name,prefix,neo,pha,H,diameter,albedo,rot_per,GM,BV,UB,spec_B,spec_T,condition_code,rms,a,e,i,om,w,ma,tp'
            }
            
            if sb_class:
                params['sb-class'] = sb_class
            
            print(f"Fetching from JPL: {sb_kind} {sb_class or 'all'} (limit={limit})")
            response = self.session.get(url, params=params, timeout=120)
            response.raise_for_status()
            data = response.json()
            
            if 'data' not in data:
                return {'success': False, 'error': 'No data in response', 'count': 0}
            
            objects = data['data']
            fields = data['fields']
            total_count = data.get('count', len(objects))
            
            print(f"Got {len(objects)} objects from JPL (total available: {total_count})")
            
            # Insert into database
            conn = get_db_connection()
            added = 0
            updated = 0
            failed = 0
            
            try:
                with conn.cursor() as cursor:
                    for i, obj in enumerate(objects):
                        try:
                            # Map fields to database columns
                            obj_dict = dict(zip(fields, obj))
                            
                            # Prepare data
                            spkid = obj_dict.get('spkid')
                            if not spkid:
                                failed += 1
                                continue
                            
                            # Insert or update
                            cursor.execute("""
                                INSERT INTO small_bodies (
                                    SPKID, JPL_FULL_NAME, JPL_DESIGNATION, JPL_NAME, JPL_PREFIX,
                                    JPL_NEO, JPL_PHA, JPL_H, JPL_DIAMETER, JPL_ALBEDO,
                                    JPL_ROT_PER, JPL_GM, JPL_BV, JPL_UB, JPL_SPEC_B,
                                    JPL_SPEC_T, JPL_CONDITION_CODE, JPL_RMS,
                                    JPL_SB_KIND, JPL_SB_CLASS, JPL_LAST_UPDATED
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                                )
                                ON DUPLICATE KEY UPDATE
                                    JPL_FULL_NAME = VALUES(JPL_FULL_NAME),
                                    JPL_DESIGNATION = VALUES(JPL_DESIGNATION),
                                    JPL_NAME = VALUES(JPL_NAME),
                                    JPL_PREFIX = VALUES(JPL_PREFIX),
                                    JPL_NEO = VALUES(JPL_NEO),
                                    JPL_PHA = VALUES(JPL_PHA),
                                    JPL_H = VALUES(JPL_H),
                                    JPL_DIAMETER = VALUES(JPL_DIAMETER),
                                    JPL_ALBEDO = VALUES(JPL_ALBEDO),
                                    JPL_ROT_PER = VALUES(JPL_ROT_PER),
                                    JPL_GM = VALUES(JPL_GM),
                                    JPL_BV = VALUES(JPL_BV),
                                    JPL_UB = VALUES(JPL_UB),
                                    JPL_SPEC_B = VALUES(JPL_SPEC_B),
                                    JPL_SPEC_T = VALUES(JPL_SPEC_T),
                                    JPL_CONDITION_CODE = VALUES(JPL_CONDITION_CODE),
                                    JPL_RMS = VALUES(JPL_RMS),
                                    JPL_SB_KIND = VALUES(JPL_SB_KIND),
                                    JPL_SB_CLASS = VALUES(JPL_SB_CLASS),
                                    JPL_LAST_UPDATED = NOW()
                            """, (
                                spkid,
                                obj_dict.get('full_name'),
                                obj_dict.get('pdes'),
                                obj_dict.get('name'),
                                obj_dict.get('prefix'),
                                'Y' if obj_dict.get('neo') == 'Y' else 'N',
                                'Y' if obj_dict.get('pha') == 'Y' else 'N',
                                obj_dict.get('H'),
                                obj_dict.get('diameter'),
                                obj_dict.get('albedo'),
                                obj_dict.get('rot_per'),
                                obj_dict.get('GM'),
                                obj_dict.get('BV'),
                                obj_dict.get('UB'),
                                obj_dict.get('spec_B'),
                                obj_dict.get('spec_T'),
                                obj_dict.get('condition_code'),
                                obj_dict.get('rms'),
                                sb_kind,
                                sb_class
                            ))
                            
                            if cursor.rowcount == 1:
                                added += 1
                            else:
                                updated += 1
                            
                        except Exception as e:
                            print(f"Error inserting object {i}: {e}")
                            failed += 1
                        
                        # Update progress every 1000 objects
                        if load_id and (i + 1) % 1000 == 0:
                            conn.commit()
                            update_load_tracking(load_id, 
                                OBJECTS_PROCESSED=i + 1,
                                OBJECTS_ADDED=added,
                                OBJECTS_UPDATED=updated,
                                OBJECTS_FAILED=failed
                            )
                            print(f"Progress: {i + 1}/{len(objects)} objects processed")
                    
                    conn.commit()
            finally:
                conn.close()
            
            return {
                'success': True,
                'total_available': total_count,
                'fetched': len(objects),
                'added': added,
                'updated': updated,
                'failed': failed
            }
            
        except Exception as e:
            print(f"Error loading JPL data: {e}")
            return {'success': False, 'error': str(e), 'count': 0}

@app.route('/api/loader/status', methods=['GET'])
def get_loader_status():
    """Get current loader status"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get recent load history
            cursor.execute("""
                SELECT * FROM load_history 
                ORDER BY STARTED_AT DESC 
                LIMIT 10
            """)
            history = cursor.fetchall()
            
            # Get database statistics
            cursor.execute("SELECT COUNT(*) as total FROM small_bodies")
            total = cursor.fetchone()['total']
            
            cursor.execute("""
                SELECT JPL_SB_CLASS, COUNT(*) as count 
                FROM small_bodies 
                WHERE JPL_SB_CLASS IS NOT NULL
                GROUP BY JPL_SB_CLASS
            """)
            by_class = cursor.fetchall()
            
            return jsonify({
                'database': {
                    'total_objects': total,
                    'by_class': by_class
                },
                'recent_loads': history,
                'current_loads': list(current_loads.keys())
            })
    finally:
        conn.close()

@app.route('/api/loader/load-jpl', methods=['POST'])
def load_jpl_data():
    """Start loading JPL data"""
    data = request.json or {}
    sb_kind = data.get('sb_kind', 'a')
    sb_class = data.get('sb_class')
    limit = data.get('limit', 100000)
    
    load_key = f"JPL_{sb_kind}_{sb_class or 'all'}"
    
    if load_key in current_loads:
        return jsonify({'error': 'Load already in progress', 'load_key': load_key}), 409
    
    # Start load tracking
    load_id = start_load_tracking('JPL', 'full' if not sb_class else 'class')
    current_loads[load_key] = {'load_id': load_id, 'status': 'running'}
    
    # Run load in background
    def run_load():
        try:
            loader = JPLLoader()
            result = loader.load_objects(sb_kind, sb_class, limit, load_id)
            
            if result['success']:
                update_load_tracking(load_id,
                    OBJECTS_PROCESSED=result['fetched'],
                    OBJECTS_ADDED=result['added'],
                    OBJECTS_UPDATED=result['updated'],
                    OBJECTS_FAILED=result['failed']
                )
                complete_load_tracking(load_id, 'completed')
            else:
                complete_load_tracking(load_id, 'failed', result.get('error'))
            
            current_loads[load_key]['status'] = 'completed'
            current_loads[load_key]['result'] = result
            
        except Exception as e:
            complete_load_tracking(load_id, 'failed', str(e))
            current_loads[load_key]['status'] = 'failed'
            current_loads[load_key]['error'] = str(e)
    
    # Start background thread
    import threading
    thread = threading.Thread(target=run_load)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'message': 'Load started',
        'load_id': load_id,
        'load_key': load_key
    })

@app.route('/api/loader/test-db', methods=['GET'])
def test_database():
    """Test database connection"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'version': version,
            'tables': tables
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/merge/jpl-mpc', methods=['POST'])
def merge_jpl_mpc():
    """Merge JPL and MPC data by matching designations"""
    try:
        # Get optional limit parameter from request
        data = request.get_json() or {}
        limit = data.get('limit', None)
        
        # Import the merger module
        from jpl_mpc_merger import run_merge
        
        # Start load tracking
        load_type = f"merge_test_{limit}" if limit else "merge"
        load_id = start_load_tracking('JPL+MPC', load_type)
        
        # Run the merge in a background thread
        import threading
        import sys
        import io
        
        def run_merge_thread():
            try:
                # Capture stdout for progress tracking
                result = run_merge(load_id, limit=limit)
                
                # Update load tracking
                update_load_tracking(
                    load_id,
                    OBJECTS_PROCESSED=result['matches_found'],
                    OBJECTS_UPDATED=result['merged'],
                    OBJECTS_FAILED=result['failed']
                )
                complete_load_tracking(load_id, 'completed')
                
            except Exception as e:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                complete_load_tracking(load_id, 'failed', error_msg)
        
        thread = threading.Thread(target=run_merge_thread)
        thread.daemon = True
        thread.start()
        
        message = f'JPL ↔ MPC merge started ({"TEST: " + str(limit) + " objects" if limit else "FULL merge"})'
        
        return jsonify({
            'status': 'started',
            'load_id': load_id,
            'limit': limit,
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("="*60)
    print("Solar System Small Bodies Database Loader")
    print("="*60)
    print(f"Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print(f"Starting loader API on port 5060...")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5060, debug=True)

