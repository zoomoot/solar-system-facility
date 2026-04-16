"""
Solar System Database Loader Dashboard
Web-based control panel for managing data loading operations
Port: 8601
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# Configuration
LOADER_API = "http://localhost:5060"

st.set_page_config(
    page_title="Database Loader Dashboard",
    page_icon="🔄",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .big-metric { font-size: 2em; font-weight: bold; }
    .status-running { color: #FFA500; }
    .status-completed { color: #00FF00; }
    .status-failed { color: #FF0000; }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🔄 Solar System Database Loader")
st.markdown("**Control Panel for Multi-Source Data Loading**")

# Sidebar - Configuration
st.sidebar.header("⚙️ Configuration")
st.sidebar.markdown("**Loader API:** http://localhost:5060")
st.sidebar.markdown("**Database:** solar_system")
st.sidebar.markdown("**Port:** 8601")

# Test connection
try:
    response = requests.get(f"{LOADER_API}/api/loader/status", timeout=5)
    if response.status_code == 200:
        st.sidebar.success("✅ Connected to Loader API")
    else:
        st.sidebar.error("❌ Loader API Error")
except:
    st.sidebar.error("❌ Cannot connect to Loader API")
    st.error("**Error:** Cannot connect to loader API on port 5060. Make sure it's running: `python loader_app.py`")
    st.stop()

# Get current status
status_data = requests.get(f"{LOADER_API}/api/loader/status").json()

# Main Dashboard
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Total Objects in DB",
        f"{status_data['database']['total_objects']:,}",
        help="Total number of objects loaded"
    )

with col2:
    active_loads = len(status_data['current_loads'])
    st.metric(
        "Active Loads",
        active_loads,
        help="Number of loads currently running"
    )

with col3:
    recent_loads = len(status_data['recent_loads'])
    st.metric(
        "Recent Operations",
        recent_loads,
        help="Number of recent load operations"
    )

st.divider()

# Tabs for different operations
tab1, tab2, tab_merge, tab3, tab4 = st.tabs(["📥 JPL Loader", "🌐 MPC Loader", "🔗 Merge Data", "📊 Status & History", "🔧 Maintenance"])

# TAB 1: JPL Loader
with tab1:
    st.header("JPL SBDB Data Loader")
    st.markdown("Load data from NASA's JPL Small-Body Database API")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Quick Load Presets")
        
        if st.button("🚀 Load All Classified Objects", use_container_width=True):
            st.info("Starting loads for all classified object types...")
            
            classifications = [
                ("IEO", 100),
                ("ATE", 5000),
                ("APO", 25000),
                ("AMO", 15000),
                ("IMB", 35000),
                ("OMB", 50000),
                ("MCA", 30000),
                ("TNO", 10000),
                ("CEN", 1000),
                ("TJN", 20000),
                ("AST", 200),
                ("HYA", 10),
            ]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, (sb_class, limit) in enumerate(classifications):
                status_text.text(f"Loading {sb_class}...")
                try:
                    response = requests.post(
                        f"{LOADER_API}/api/loader/load-jpl",
                        json={"sb_class": sb_class, "limit": limit},
                        timeout=5
                    )
                    if response.status_code == 200:
                        st.success(f"✅ {sb_class} load started")
                    else:
                        st.warning(f"⚠️ {sb_class}: {response.json().get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"❌ {sb_class}: {str(e)}")
                
                progress_bar.progress((i + 1) / len(classifications))
                time.sleep(2)  # Rate limiting
            
            status_text.text("All loads initiated!")
            st.balloons()
        
        if st.button("☄️ Load All Comets", use_container_width=True):
            try:
                response = requests.post(
                    f"{LOADER_API}/api/loader/load-jpl",
                    json={"sb_kind": "c", "limit": 5000},
                    timeout=5
                )
                if response.status_code == 200:
                    st.success("✅ Comet load started!")
                else:
                    st.error(f"Error: {response.json()}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    with col2:
        st.subheader("Custom Load")
        
        load_type = st.radio(
            "Load Type",
            ["By Classification", "By Kind"],
            horizontal=True
        )
        
        if load_type == "By Classification":
            sb_class = st.selectbox(
                "Object Class",
                ["NEO", "IEO", "ATE", "APO", "AMO", "IMB", "OMB", "MCA", "TNO", "CEN", "TJN", "AST", "HYA"]
            )
            sb_kind = "a"
        else:
            sb_kind = st.selectbox("Object Kind", ["a (Asteroids)", "c (Comets)"])
            sb_kind = sb_kind[0]
            sb_class = None
        
        limit = st.number_input("Limit", min_value=100, max_value=100000, value=10000, step=1000)
        
        if st.button("▶️ Start Custom Load", use_container_width=True):
            payload = {"sb_kind": sb_kind, "limit": limit}
            if sb_class:
                payload["sb_class"] = sb_class
            
            try:
                response = requests.post(
                    f"{LOADER_API}/api/loader/load-jpl",
                    json=payload,
                    timeout=5
                )
                if response.status_code == 200:
                    st.success(f"✅ Load started: {response.json()}")
                else:
                    st.error(f"Error: {response.json()}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# TAB 2: MPC Loader
with tab2:
    st.header("MPC MPCORB.DAT Loader")
    st.markdown("Load complete orbital element database from Minor Planet Center")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.info("""
        **About MPC MPCORB.DAT:**
        - Contains ~1.47M objects with orbital elements
        - Updated daily by Minor Planet Center
        - Includes numbered and unnumbered asteroids
        - File size: ~285MB uncompressed
        """)
        
        file_status = st.empty()
        
        import os
        mpcorb_path = "/Users/gwil/Cursor/Solar-System/MPCORB.DAT"
        if os.path.exists(mpcorb_path):
            file_size = os.path.getsize(mpcorb_path) / (1024*1024)
            file_time = datetime.fromtimestamp(os.path.getmtime(mpcorb_path))
            file_status.success(f"✅ File exists: {file_size:.1f} MB (Last modified: {file_time.strftime('%Y-%m-%d %H:%M')})")
        else:
            file_status.warning("⚠️ MPCORB.DAT not found")
    
    with col2:
        st.subheader("Actions")
        
        if st.button("📥 Download Latest MPCORB.DAT", use_container_width=True):
            with st.spinner("Downloading..."):
                import subprocess
                result = subprocess.run(
                    ["curl", "-o", mpcorb_path + ".gz", 
                     "https://www.minorplanetcenter.net/iau/MPCORB/MPCORB.DAT.gz"],
                    capture_output=True
                )
                if result.returncode == 0:
                    subprocess.run(["gunzip", "-f", mpcorb_path + ".gz"])
                    st.success("✅ Downloaded and extracted!")
                    st.rerun()
                else:
                    st.error("❌ Download failed")
        
        if st.button("🔄 Load MPCORB.DAT into Database", use_container_width=True):
            if not os.path.exists(mpcorb_path):
                st.error("❌ MPCORB.DAT not found. Download it first!")
            else:
                with st.spinner("Loading MPC data... This will take several minutes"):
                    import subprocess
                    result = subprocess.run(
                        ["/Users/gwil/Cursor/Solar-System/venv/bin/python",
                         "/Users/gwil/Cursor/Solar-System/mpc_loader.py",
                         mpcorb_path],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        st.success("✅ MPC data loaded successfully!")
                        st.code(result.stdout[-500:])  # Show last 500 chars
                        st.rerun()
                    else:
                        st.error("❌ Load failed")
                        st.code(result.stderr)

# TAB MERGE: Merge Data
with tab_merge:
    st.header("🔗 Data Merging & Enrichment")
    st.markdown("Merge and enrich data from multiple sources")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Step 3: Match & Merge JPL ↔ MPC")
        st.info("""
        **What this does:**
        - Matches JPL objects with MPC objects by designation
        - Merges JPL physical properties (diameter, albedo, etc.) into MPC rows
        - Eliminates duplicate rows
        - Creates unified dataset with both orbital elements and physical properties
        
        **Before:** 142K JPL rows + 998K MPC rows = 1.14M total
        **After:** ~1.0M unified rows (JPL data merged into MPC rows)
        """)
        
        # Merge mode selection
        merge_mode = st.radio(
            "Merge Mode",
            ["🧪 Test (1,000 objects)", "🚀 Full Merge (all objects)"],
            horizontal=True
        )
        
        limit = 1000 if "Test" in merge_mode else None
        button_label = "🧪 Run Test Merge (1K)" if limit else "🚀 Run Full Merge (138K)"
        
        if st.button(button_label, use_container_width=True, type="primary"):
            result_box = st.empty()
            with result_box.container():
                st.info(f"⏳ Starting merge... {'(TEST MODE: 1,000 objects)' if limit else '(FULL: ~138K objects)'}")
                
                try:
                    response = requests.post(
                        f"{LOADER_API}/api/merge/jpl-mpc",
                        json={"limit": limit},
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"""
                        ✅ **Merge Started Successfully!**
                        
                        - **Load ID:** {result.get('load_id')}
                        - **Mode:** {'TEST (1,000 objects)' if limit else 'FULL (~138K objects)'}
                        - **Status:** Running in background
                        
                        Check the **'Status & History'** tab to monitor progress.
                        """)
                        time.sleep(3)
                        st.rerun()
                    else:
                        st.error(f"❌ **Merge Failed**\n\n{response.text}")
                        
                except Exception as e:
                    st.error(f"❌ **Error Starting Merge**\n\n{str(e)}")
    
    with col2:
        st.subheader("Merge Statistics")
        
        # Get current merge status from database
        try:
            db_status = requests.get(f"{LOADER_API}/api/loader/status").json()
            total_objects = db_status['database']['total_objects']
            
            # Count objects with both JPL and MPC data
            st.metric("Total Objects", f"{total_objects:,}")
            
            # Show merge status
            recent_merges = [load for load in db_status['recent_loads'] 
                           if load.get('LOAD_TYPE') == 'merge']
            
            if recent_merges:
                last_merge = recent_merges[0]
                st.metric("Last Merge", last_merge.get('COMPLETED_AT', 'Running...'))
                st.metric("Objects Merged", f"{last_merge.get('OBJECTS_UPDATED', 0):,}")
            else:
                st.warning("⚠️ No merge operations yet")
                
        except Exception as e:
            st.error(f"Error fetching merge stats: {e}")
    
    st.divider()
    
    # Future enrichment steps (placeholders)
    st.subheader("Future Enrichment Steps")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("""
        **Step 4: JPL Physical Data**
        Fetch diameter, albedo, rotation for MPC-only objects
        """)
        if st.button("🚀 Enrich with JPL", use_container_width=True, disabled=True):
            st.info("Coming soon!")
    
    with col2:
        st.info("""
        **Step 5: SsODNet Data**
        Add mass, density, taxonomy for well-studied objects
        """)
        if st.button("🌐 Enrich with SsODNet", use_container_width=True, disabled=True):
            st.info("Coming soon!")
    
    with col3:
        st.info("""
        **Step 6: Wikipedia Data**
        Add summaries and references for notable objects
        """)
        if st.button("📖 Enrich with Wikipedia", use_container_width=True, disabled=True):
            st.info("Coming soon!")

# TAB 3: Status & History
with tab3:
    st.header("Load Status & History")
    
    # Current active loads
    if status_data['current_loads']:
        st.subheader("🔄 Active Loads")
        for load_key in status_data['current_loads']:
            st.info(f"⏳ {load_key} - In Progress")
    else:
        st.success("✅ No active loads")
    
    st.divider()
    
    # Recent load history
    st.subheader("📜 Recent Load History")
    
    if status_data['recent_loads']:
        history_df = pd.DataFrame(status_data['recent_loads'])
        
        # Format columns
        history_df['STARTED_AT'] = pd.to_datetime(history_df['STARTED_AT'])
        history_df['COMPLETED_AT'] = pd.to_datetime(history_df['COMPLETED_AT'])
        
        # Display table
        st.dataframe(
            history_df[[
                'ID', 'SOURCE', 'LOAD_TYPE', 'STATUS', 
                'OBJECTS_PROCESSED', 'OBJECTS_ADDED', 'OBJECTS_UPDATED', 'OBJECTS_FAILED',
                'DURATION_SECONDS', 'STARTED_AT'
            ]],
            use_container_width=True,
            hide_index=True
        )
        
        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        
        completed = history_df[history_df['STATUS'] == 'completed']
        
        with col1:
            st.metric("Completed Loads", len(completed))
        with col2:
            st.metric("Total Objects Added", f"{completed['OBJECTS_ADDED'].sum():,}")
        with col3:
            st.metric("Total Objects Updated", f"{completed['OBJECTS_UPDATED'].sum():,}")
        with col4:
            avg_duration = completed['DURATION_SECONDS'].mean()
            st.metric("Avg Duration", f"{avg_duration:.1f}s" if not pd.isna(avg_duration) else "N/A")
    else:
        st.info("No load history available")
    
    st.divider()
    
    # Database statistics
    st.subheader("📊 Database Statistics")
    
    if status_data['database']['by_class']:
        class_df = pd.DataFrame(status_data['database']['by_class'])
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.bar_chart(class_df.set_index('JPL_SB_CLASS')['count'])
        
        with col2:
            st.dataframe(
                class_df.sort_values('count', ascending=False),
                use_container_width=True,
                hide_index=True
            )

# TAB 4: Maintenance
with tab4:
    st.header("🔧 Database Maintenance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Database Info")
        
        try:
            import pymysql
            conn = pymysql.connect(
                host='127.0.0.1',
                port=3306,
                user='solar_user',
                password='solar_pass_2025',
                database='solar_system'
            )
            
            with conn.cursor() as cursor:
                # Table sizes
                cursor.execute("""
                    SELECT 
                        table_name,
                        ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb,
                        table_rows
                    FROM information_schema.TABLES
                    WHERE table_schema = 'solar_system'
                    ORDER BY (data_length + index_length) DESC
                """)
                tables = cursor.fetchall()
                
                st.markdown("**Table Sizes:**")
                for table in tables:
                    st.text(f"{table[0]}: {table[1]} MB ({table[2]:,} rows)")
                
                # Field coverage
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(SPKID) as with_spkid,
                        COUNT(MPC_DESIGNATION) as with_mpc,
                        COUNT(JPL_H) as with_jpl_h,
                        COUNT(MPC_H) as with_mpc_h,
                        COUNT(JPL_DIAMETER) as with_diameter,
                        COUNT(MPC_A) as with_semimajor
                    FROM small_bodies
                """)
                coverage = cursor.fetchone()
                
                st.markdown("**Data Coverage:**")
                st.text(f"Total objects: {coverage[0]:,}")
                st.text(f"With JPL SPKID: {coverage[1]:,} ({coverage[1]/coverage[0]*100:.1f}%)")
                st.text(f"With MPC designation: {coverage[2]:,} ({coverage[2]/coverage[0]*100:.1f}%)")
                st.text(f"With JPL H magnitude: {coverage[3]:,} ({coverage[3]/coverage[0]*100:.1f}%)")
                st.text(f"With MPC H magnitude: {coverage[4]:,} ({coverage[4]/coverage[0]*100:.1f}%)")
                st.text(f"With diameter: {coverage[5]:,} ({coverage[5]/coverage[0]*100:.1f}%)")
                st.text(f"With semi-major axis: {coverage[6]:,} ({coverage[6]/coverage[0]*100:.1f}%)")
            
            conn.close()
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    with col2:
        st.subheader("Actions")
        
        if st.button("🔄 Refresh Status", use_container_width=True):
            st.rerun()
        
        if st.button("🗑️ Clear Load History", use_container_width=True):
            st.warning("This will clear the load_history table")
            if st.button("⚠️ Confirm Clear"):
                try:
                    import pymysql
                    conn = pymysql.connect(
                        host='127.0.0.1',
                        port=3306,
                        user='solar_user',
                        password='solar_pass_2025',
                        database='solar_system'
                    )
                    with conn.cursor() as cursor:
                        cursor.execute("TRUNCATE TABLE load_history")
                    conn.commit()
                    conn.close()
                    st.success("✅ Load history cleared")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        st.divider()
        
        st.markdown("**Export Data:**")
        if st.button("📤 Export to CSV", use_container_width=True):
            st.info("Feature coming soon...")

# Footer
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Loader API:** http://localhost:5060")
with col2:
    st.markdown("**Dashboard:** http://localhost:8601")
with col3:
    if st.button("🔄 Auto-refresh (5s)", use_container_width=True):
        time.sleep(5)
        st.rerun()


