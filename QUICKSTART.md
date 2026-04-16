# Quick Start Guide

## 🚀 Getting Started in 3 Steps

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the Server

```bash
python app.py
```

Or use the convenience script:
```bash
./start.sh
```

### 3. Open in Browser

Navigate to: **http://localhost:5050**

---

## 🎯 What You'll See

### Dashboard Overview
- **Total Objects**: Number of objects in current dataset
- **High Priority**: Under-researched NEOs and PHAs
- **Avg Completeness**: Overall data coverage percentage
- **Data Sources**: Active integrations (JPL SBDB, SsODNet)

### Three Main Tabs

#### 1. Object Explorer
- Browse small solar system bodies
- View completeness scores (0-100%)
- See missing properties for each object
- Export data to CSV

**Try this:**
- Click "Load Objects" to fetch 100 objects from JPL SBDB
- Sort by completeness to find gaps
- Click "Details" on any object for more info

#### 2. Data Analytics
- Visual property coverage charts
- Identify systematic observation gaps
- See which properties are most/least covered

**Key Insights:**
- Which properties are missing most often?
- Are certain object types better studied?
- Where should observation efforts focus?

#### 3. Under-Researched
- Automated target identification
- Priority ranking (High/Medium/Low)
- Filter by priority level

**Priority Criteria:**
- **High**: NEOs/PHAs missing 2+ critical properties
- **Medium**: Any object missing 3+ critical properties
- **Low**: Relatively complete data

---

## 🔍 Example Queries

### Find High-Priority Targets
1. Go to "Under-Researched" tab
2. Select "High Only" priority
3. Click "Find Targets"
4. Review NEOs/PHAs with missing physical properties

### Analyze Property Coverage
1. Go to "Data Analytics" tab
2. View horizontal bar charts
3. Identify least-covered properties
4. Plan observation campaigns

### Export for Further Analysis
1. Load objects in "Object Explorer"
2. Click "Export CSV"
3. Open in spreadsheet software
4. Perform custom analysis

---

## 📊 Understanding the Data

### Critical Properties Tracked

| Property | Description | Why Important |
|----------|-------------|---------------|
| **diameter** | Object size (km) | Mission planning, impact risk |
| **albedo** | Surface reflectivity | Composition, thermal modeling |
| **rot_per** | Rotation period (hours) | Shape, stability, YORP effect |
| **H** | Absolute magnitude | Size estimate, brightness |
| **spec_B** | Bus spectral type | Composition, taxonomy |
| **spec_T** | Tholen spectral type | Composition, taxonomy |
| **GM** | Gravitational parameter | Mass, density |
| **BV** | B-V color index | Surface properties |
| **UB** | U-B color index | Surface properties |

### Completeness Score

The completeness score is calculated as:
```
(Present Properties / Total Critical Properties) × 100%
```

- **90-100%**: Well-characterized object
- **60-89%**: Moderate characterization
- **30-59%**: Poorly characterized
- **0-29%**: Severely under-researched

---

## 🛠️ API Usage

### REST Endpoints

#### Search Objects
```bash
curl "http://localhost:5050/api/objects/search?source=jpl&limit=100"
```

#### Get Object Details
```bash
curl "http://localhost:5050/api/objects/433"  # Eros
```

#### Completeness Statistics
```bash
curl "http://localhost:5050/api/stats/completeness"
```

#### Under-Researched Objects
```bash
curl "http://localhost:5050/api/under-researched?priority=high&limit=50"
```

### Response Format

All API responses follow this structure:
```json
{
  "success": true,
  "count": 100,
  "objects": [...],
  "source": "JPL SBDB"
}
```

---

## 🎓 Research Workflow Example

### Goal: Identify NEO targets for spectroscopic follow-up

1. **Load NEO data**
   - Set limit to 500 objects
   - Click "Load Objects"

2. **Filter for spectral gaps**
   - Go to "Under-Researched" tab
   - Select "High Only" priority
   - Look for objects missing `spec_B` or `spec_T`

3. **Cross-reference**
   - Check if objects are observable (H magnitude)
   - Verify they're accessible (NEO designation)
   - Note rotation period for observation planning

4. **Export and prioritize**
   - Export to CSV
   - Add columns for telescope time, observability windows
   - Submit observation proposals

---

## 🔧 Troubleshooting

### Server won't start
- Check port 5050 isn't in use: `lsof -i :5050`
- Try a different port in `app.py`
- Verify Python 3.7+ is installed

### No data loading
- Check internet connection (APIs require network access)
- Wait 30 seconds for API timeout
- Check cache directory permissions

### API errors
- JPL SBDB may be temporarily down
- Try SsODNet as alternative source
- Check cache files in `cache/` directory

### Slow performance
- Reduce limit parameter (try 50 instead of 500)
- Clear cache directory to force refresh
- Check network speed

---

## 📈 Next Steps

### Expand Your Analysis

1. **Add More Data Sources**
   - NASA Exoplanet Archive (comparative studies)
   - Minor Planet Center observations
   - WISE/NEOWISE thermal data

2. **Custom Filters**
   - Orbital elements (a, e, i)
   - Dynamical families
   - Discovery circumstances

3. **Mission Planning**
   - Delta-v calculations
   - Launch window analysis
   - Multi-target tours

4. **Collaborative Research**
   - Share findings with community
   - Coordinate observations
   - Contribute new measurements

---

## 💡 Tips & Tricks

- **Bookmark interesting objects**: Use browser bookmarks for quick access
- **Compare sources**: Check both JPL and SsODNet for same object
- **Track changes**: Re-run queries periodically to see new data
- **Cache awareness**: Data cached for 24 hours, delete `cache/` to force refresh
- **Export regularly**: Save CSV snapshots for longitudinal studies

---

## 🌟 Example Discoveries

### What you might find:

- **NEO with no spectral type**: High-priority target for ground-based spectroscopy
- **Large MBA with no diameter**: Candidate for stellar occultation
- **Fast rotator with no period**: Target for lightcurve photometry
- **PHA with no albedo**: Critical for impact risk assessment

---

## 📚 Further Reading

- [JPL SBDB Documentation](https://ssd-api.jpl.nasa.gov/doc/)
- [SsODNet User Guide](https://ssp.imcce.fr/webservices/ssodnet/)
- [Minor Planet Center](https://www.minorplanetcenter.net/)
- [NASA NEO Program](https://cneos.jpl.nasa.gov/)

---

**Happy Exploring! 🌌**

For questions or issues, check the main README.md or API documentation.

