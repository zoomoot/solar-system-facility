# 🔄 Solar System Database Loader Dashboard

## Quick Start

### 1. Start Required Services

```bash
# Terminal 1: Start Loader API (Port 5060)
cd /Users/gwil/Cursor/Solar-System
source venv/bin/activate
python loader_app.py

# Terminal 2: Start Dashboard (Port 8601)
cd /Users/gwil/Cursor/Solar-System
source venv/bin/activate
streamlit run loader_dashboard.py --server.port 8601 --server.address 0.0.0.0
```

### 2. Access Dashboard

Open browser to: **http://localhost:8601**

---

## Dashboard Features

### 📥 JPL Loader Tab
- **Quick Load Presets**: One-click loading of all classified objects
- **Custom Load**: Specify object class, kind, and limit
- **Progress Tracking**: Real-time feedback on load operations

**Available Classifications:**
- NEO, IEO, ATE, APO, AMO (Near-Earth Objects)
- IMB, OMB (Main Belt)
- MCA (Mars Crossers)
- TNO (Trans-Neptunian)
- CEN (Centaurs)
- TJN (Jupiter Trojans)
- AST, HYA (Special types)

### 🌐 MPC Loader Tab
- **Download Latest MPCORB.DAT**: Fetches from Minor Planet Center
- **Load into Database**: Imports ~1.47M objects with orbital elements
- **File Status**: Shows current file info and last update

### 📊 Status & History Tab
- **Active Loads**: See what's currently running
- **Load History**: Complete history of all operations
- **Statistics**: Objects added, updated, failed
- **Database Stats**: Breakdown by classification

### 🔧 Maintenance Tab
- **Database Info**: Table sizes, row counts
- **Data Coverage**: Percentage of objects with each field
- **Actions**: Refresh, clear history, export data

---

## Typical Workflow

### Initial Setup (First Time)

1. **Start Services** (see Quick Start above)

2. **Load JPL Classified Data**:
   - Go to "JPL Loader" tab
   - Click "🚀 Load All Classified Objects"
   - Wait ~2-3 minutes for completion

3. **Load MPC Bulk Data**:
   - Go to "MPC Loader" tab
   - Click "📥 Download Latest MPCORB.DAT" (if not already downloaded)
   - Click "🔄 Load MPCORB.DAT into Database"
   - Wait ~5-10 minutes for 1.47M objects to load

4. **Verify**:
   - Go to "Status & History" tab
   - Check total objects (should be ~1.14M)
   - Review load history for any failures

### Periodic Updates (Weekly/Monthly)

1. **Update MPC Data**:
   - Go to "MPC Loader" tab
   - Click "📥 Download Latest MPCORB.DAT"
   - Click "🔄 Load MPCORB.DAT into Database"
   - This will update existing objects and add new discoveries

2. **Update JPL Data** (optional):
   - Go to "JPL Loader" tab
   - Click "🚀 Load All Classified Objects"
   - This will update physical parameters for classified objects

---

## Current Database Status

**As of last load:**
- **Total Objects**: 1,139,765
- **From JPL**: 142,182 (with physical parameters)
- **From MPC**: 997,583 (with orbital elements)
- **Database Size**: ~500MB

**Data Sources:**
- **JPL SBDB**: Physical parameters (H, diameter, albedo, rotation, etc.)
- **MPC MPCORB**: Orbital elements (a, e, i, Ω, ω, M)

---

## Architecture

```
┌─────────────────────────────────────────────┐
│   Loader Dashboard (Port 8601)              │
│   - Web UI for control                      │
│   - Real-time status                        │
│   - One-click operations                    │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│   Loader API (Port 5060)                    │
│   - Background processing                   │
│   - Progress tracking                       │
│   - Error handling                          │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│   MariaDB (Port 3306)                       │
│   Database: solar_system                    │
│   Tables: small_bodies, load_history        │
└─────────────────────────────────────────────┘
```

---

## Troubleshooting

### Dashboard won't start
```bash
# Check if port is in use
lsof -i:8601

# Kill existing process
lsof -ti:8601 | xargs kill -9

# Restart
streamlit run loader_dashboard.py --server.port 8601
```

### Loader API not responding
```bash
# Check if running
lsof -i:5060

# Restart
python loader_app.py
```

### Database connection errors
```bash
# Test MySQL connection
mysql -u solar_user -psolar_pass_2025 -h 127.0.0.1 solar_system -e "SELECT COUNT(*) FROM small_bodies;"
```

---

## Next Steps

1. ✅ **JPL + MPC data loaded** (1.14M objects)
2. ⏳ **Match JPL ↔ MPC** objects to merge data
3. ⏳ **Add SsODNet enrichment** for mass/density
4. ⏳ **Add Wikipedia** references
5. ⏳ **Update main Flask app** to query database

---

## Files

- `loader_dashboard.py` - Streamlit dashboard (Port 8601)
- `loader_app.py` - Flask API (Port 5060)
- `mpc_loader.py` - MPC MPCORB.DAT parser
- `database_schema.sql` - Database schema
- `MPCORB.DAT` - MPC data file (285MB)

---

## Database Schema

**Naming Convention:**
- Tables: `lowercase` (small_bodies, load_history)
- Fields: `UPPERCASE` (SPKID, JPL_H, MPC_A)
- Source Prefixes: `JPL_*`, `MPC_*`, `SSOD_*`, `WIKI_*`

**Key Fields:**
- `SPKID` - JPL's unique identifier
- `MPC_DESIGNATION` - MPC's designation
- `JPL_H` - Absolute magnitude (JPL)
- `MPC_H` - Absolute magnitude (MPC)
- `JPL_DIAMETER` - Diameter in km
- `MPC_A` - Semi-major axis in AU
- `MPC_E` - Eccentricity
- `MPC_INCL` - Inclination in degrees




