# 🌌 Solar System Explorer - Backup & Restore Guide

## 📦 Current Backup

**File:** `Solar-System-v2.0.0-streamlit-YYYYMMDD-HHMMSS.tar.gz`  
**Location:** `/Users/gwil/Cursor/`  
**Version:** 2.0.0-streamlit  
**Date:** November 16, 2025

---

## 🔄 How to Restore from Backup

### Step 1: Extract the Archive

```bash
cd /path/to/destination
tar -xzf Solar-System-v2.0.0-streamlit-*.tar.gz
cd Solar-System
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Run the Application

**Easy Way (Recommended):**
```bash
./START_EXPLORER.sh
```

**Manual Way:**
```bash
# Terminal 1: Start Flask backend
python app.py

# Terminal 2: Start Streamlit frontend
streamlit run streamlit_app.py --server.port 8501
```

### Step 4: Open in Browser

Navigate to: **http://localhost:8501**

---

## 📋 What's Included in Backup

✅ **Core Application Files**
- `app.py` - Flask backend API
- `streamlit_app.py` - Streamlit frontend
- `config.py` - Configuration
- `requirements.txt` - Python dependencies
- `START_EXPLORER.sh` - Standalone launcher

✅ **Templates & Frontend**
- `templates/index.html` - Flask web UI

✅ **Documentation** (15+ files)
- README.md, QUICKSTART.md, FEATURES.md
- PROJECT_OVERVIEW.md, VERSION.txt
- All setup and usage guides

✅ **Database System** (Optional)
- `loader_app.py` - Database loader backend
- `loader_dashboard.py` - Loader dashboard
- `mpc_loader.py` - MPC data import
- `database_schema.sql` - Database schema

✅ **Mission Analysis Scripts**
- `probe_mission_analysis.py`
- `yorp_mission_design.py`
- `yorp_science_case.py`
- `yorp_satellite_repurposing.py`

✅ **MCP Integration** (AI Agents)
- `mcp_server.py`
- `mcp_server_simple.py`
- MCP documentation

---

## ❌ What's NOT Included

These files are excluded to keep backups small:

- `venv/` - Virtual environment (recreated on install)
- `cache/` - API cache files (regenerated automatically)
- `*.log` - Log files
- `__pycache__/` - Python bytecode
- `MPCORB.DAT` - Large MPC data file (286 MB, re-downloadable)
- `data/` - Cached data files

---

## 🚀 Quick Restoration Checklist

1. ✅ Extract backup archive
2. ✅ Create virtual environment (`python3 -m venv venv`)
3. ✅ Activate venv (`source venv/bin/activate`)
4. ✅ Install dependencies (`pip install -r requirements.txt`)
5. ✅ Run application (`./START_EXPLORER.sh`)
6. ✅ Open browser to http://localhost:8501

---

## 🔧 Troubleshooting

### Port Already in Use

```bash
# Check what's using the port
lsof -i :8501
lsof -i :5050

# Kill the process
pkill -f streamlit
pkill -f "python app.py"
```

### Dependencies Won't Install

```bash
# Upgrade pip first
pip install --upgrade pip

# Try installing again
pip install -r requirements.txt
```

### No Internet Connection

The app requires internet to fetch data from:
- JPL Small-Body Database
- SsODNet
- Wikipedia

Cached data will be used if available.

---

## 💾 Creating New Backups

### Method 1: Using tar (Recommended)

```bash
cd /Users/gwil/Cursor
BACKUP_NAME="Solar-System-v2.0.0-streamlit-$(date +%Y%m%d-%H%M%S)"
tar -czf "${BACKUP_NAME}.tar.gz" \
  --exclude="Solar-System/venv" \
  --exclude="Solar-System/cache" \
  --exclude="Solar-System/__pycache__" \
  --exclude="Solar-System/*.log" \
  --exclude="Solar-System/MPCORB.DAT" \
  --exclude="Solar-System/data" \
  Solar-System
```

### Method 2: Using Git

```bash
cd /Users/gwil/Cursor/Solar-System
git add .
git commit -m "Backup: v2.0.0-streamlit $(date)"
git tag v2.0.0-streamlit
```

---

## 📤 Sharing the Project

### Option 1: Share the Backup Archive

```bash
# Upload to cloud storage
# - Google Drive
# - Dropbox
# - AWS S3
# - GitHub releases

# Share the .tar.gz file
```

### Option 2: GitHub Repository

```bash
cd /Users/gwil/Cursor/Solar-System
git init
git add .
git commit -m "Initial commit: v2.0.0-streamlit"

# Create repo on GitHub, then:
git remote add origin https://github.com/yourusername/solar-system-explorer.git
git push -u origin main
git tag v2.0.0-streamlit
git push --tags
```

---

## 🔐 Backup Strategy Recommendations

### Daily Backups
```bash
# Add to cron job or Task Scheduler
0 2 * * * cd /Users/gwil/Cursor && tar -czf "backups/solar-system-$(date +\%Y\%m\%d).tar.gz" --exclude="venv" --exclude="cache" Solar-System
```

### Multiple Backup Locations
1. **Local:** External hard drive
2. **Cloud:** Google Drive, Dropbox, iCloud
3. **Remote:** GitHub, GitLab, AWS
4. **Archive:** Keep monthly snapshots

---

## 📊 Backup Contents Summary

**Total Files:** ~150 files (excluding venv, cache)  
**Compressed Size:** ~127 KB  
**Uncompressed Size:** ~2-3 MB  
**Code:** ~3,000+ lines of Python  
**Documentation:** ~2,000+ lines  

---

## 🎯 Version History

### v2.0.0-streamlit (November 16, 2025) - CURRENT
- Streamlit interactive interface
- 3D orbital visualizations
- Plotly charts and filtering
- Standalone launcher script

### v1.0.0 (November 1, 2025)
- Flask-based web application
- Basic three-tab interface
- JPL + SsODNet integration

---

## ✅ Verification After Restore

Run these commands to verify the restoration:

```bash
# Check Python version
python --version  # Should be 3.9+

# Check dependencies
pip list | grep -E "(flask|streamlit|plotly|pandas)"

# Check main files exist
ls -l app.py streamlit_app.py requirements.txt

# Test backend
curl http://localhost:5050/api/stats/completeness

# Test frontend
# Open http://localhost:8501 in browser
```

---

## 📞 Support

If you encounter issues:

1. Check `VERSION.txt` for current version info
2. Review `README.md` for detailed documentation
3. Check `*.log` files for error messages
4. Verify internet connection for API access

---

**Your project is fully backed up and restorable!** 🎉

