# Feature Guide

## 🎨 Visual Tour of the Application

### Main Interface

When you open http://localhost:5050, you'll see:

#### Header Section
```
🌌 Solar System Small Bodies Explorer
Identifying Under-Researched Objects for Robotic Exploration
```

#### Dashboard Cards (Top Row)

Four real-time statistics cards:

1. **Total Objects**
   - Shows number of objects in current dataset
   - Updates when you load new data
   - Example: "200" objects

2. **High Priority**
   - Count of under-researched NEOs/PHAs
   - Critical for planetary defense
   - Example: "23" high-priority targets

3. **Avg Completeness**
   - Overall data coverage percentage
   - Helps track dataset quality
   - Example: "78.5%" average completeness

4. **Data Sources**
   - Number of integrated databases
   - Currently: "2" (JPL SBDB • SsODNet)
   - Will expand as more sources added

### Tab 1: Object Explorer

**Purpose**: Browse and search small solar system bodies

**Controls**:
- **Data Source**: Choose between JPL SBDB or SsODNet
- **Limit**: Set how many objects to load (10-500)
- **Load Objects**: Fetch data from selected source
- **Export CSV**: Download current dataset

**Table Columns**:
1. **Designation**: Official identifier (e.g., "2023 DW")
2. **Name**: Common name if available (e.g., "Ceres")
3. **Type**: Classification (NEO, PHA, MBA)
4. **Completeness**: Visual bar showing 0-100%
5. **Priority**: Badge showing High/Medium/Low
6. **Missing Properties**: List of unknown parameters
7. **Actions**: "Details" button for more info

**Example Row**:
```
┌─────────────┬──────┬──────────┬──────────────────┬──────────┬─────────────────────────┬─────────┐
│ 2023 DW     │ -    │ NEO (PHA)│ ████████░░ 78%   │ [HIGH]   │ diameter, albedo, spec_B│ Details │
└─────────────┴──────┴──────────┴──────────────────┴──────────┴─────────────────────────┴─────────┘
```

**Interactive Features**:
- Hover over rows to highlight
- Click column headers to sort (future)
- Completeness bars are color-coded:
  - Red (0-30%): Severely under-researched
  - Yellow (30-70%): Moderately characterized
  - Green (70-100%): Well-studied

### Tab 2: Data Analytics

**Purpose**: Visualize property coverage across the dataset

**Display**: Horizontal bar chart showing:
- Property name (left)
- Coverage bar (center)
- Percentage and count (right)

**Example Visualization**:
```
H           ████████████████████████████████████ 100% (200/200)
diameter    ████████████████░░░░░░░░░░░░░░░░░░░  45% (90/200)
albedo      ███████████░░░░░░░░░░░░░░░░░░░░░░░░  32% (64/200)
rot_per     ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  18% (36/200)
spec_B      ████████████████████░░░░░░░░░░░░░░░  56% (112/200)
spec_T      ███████████████░░░░░░░░░░░░░░░░░░░░  42% (84/200)
GM          ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   5% (10/200)
BV          ███████████████████████░░░░░░░░░░░░  65% (130/200)
UB          ████████████████░░░░░░░░░░░░░░░░░░░  45% (90/200)
```

**Insights**:
- Absolute magnitude (H) is nearly always available
- Mass (GM) is rarely measured (requires close flybys)
- Spectral classification has moderate coverage
- Rotation periods are challenging to obtain

### Tab 3: Under-Researched

**Purpose**: Identify high-value observation targets

**Controls**:
- **Minimum Priority**: Filter by High/Medium/Low
- **Find Targets**: Run analysis algorithm

**Output Table**:
1. **Rank**: Priority order (#1 = highest)
2. **Designation**: Object identifier
3. **Name**: Common name
4. **Type**: NEO, PHA, or MBA
5. **Priority**: Color-coded badge
6. **Completeness**: Percentage score
7. **Key Missing Data**: Top 3 missing properties

**Example Output**:
```
┌──────┬─────────────┬──────┬──────────┬──────────┬──────────────┬─────────────────────────┐
│ #1   │ 2024 AB1    │ -    │ NEO (PHA)│ [HIGH]   │ 45%          │ diameter, albedo, spec_B│
│ #2   │ 2023 XY5    │ -    │ NEO (PHA)│ [HIGH]   │ 56%          │ rot_per, spec_T, GM     │
│ #3   │ 2022 CD3    │ -    │ NEO      │ [HIGH]   │ 67%          │ diameter, rot_per       │
│ #4   │ 2021 QW8    │ -    │ NEO      │ [MEDIUM] │ 72%          │ albedo, spec_B, BV      │
└──────┴─────────────┴──────┴──────────┴──────────┴──────────────┴─────────────────────────┘
```

**Use Cases**:
- Telescope proposal writing
- Mission target selection
- Coordinating observation campaigns
- Tracking characterization progress

## 🔧 Key Features

### 1. Real-Time Data Integration

**How it works**:
- Queries JPL SBDB API on demand
- Caches responses for 24 hours
- Automatic retry on failure
- Graceful degradation if API unavailable

**Benefits**:
- Always up-to-date information
- Fast repeat queries (cached)
- Reliable even with network issues

### 2. Intelligent Completeness Analysis

**Algorithm**:
```python
For each object:
  1. Check presence of 9 critical properties
  2. Calculate completeness percentage
  3. Identify specific missing properties
  4. Assign research priority
  5. Generate recommendations
```

**Critical Properties**:
- **Physical**: diameter, albedo, rotation period, mass
- **Spectral**: Bus type, Tholen type, color indices
- **Photometric**: absolute magnitude (H)

### 3. Priority Ranking System

**Factors Considered**:
- **Object Type**: NEOs and PHAs get higher priority
- **Missing Properties**: More gaps = higher priority
- **Property Importance**: Diameter/albedo weighted heavily
- **Scientific Value**: Unique or unusual objects boosted

**Priority Levels**:
- **High**: Immediate observation recommended
- **Medium**: Should be characterized soon
- **Low**: Can wait for routine surveys

### 4. Data Export

**Formats**:
- CSV (current): Spreadsheet-compatible
- JSON (future): Machine-readable
- XLSX (future): Excel native format

**Export Contents**:
- Object designation and name
- Classification (NEO/PHA/MBA)
- Completeness score
- Priority level
- Missing properties list
- All available physical parameters

### 5. Caching System

**Cache Structure**:
```
cache/
├── jpl_sbdb_cache.json      # JPL SBDB responses
└── ssodnet_cache.json       # SsODNet responses
```

**Cache Entry Format**:
```json
{
  "query_100_None": {
    "timestamp": "2025-11-01T10:30:00",
    "data": { ... }
  }
}
```

**Benefits**:
- Reduces API load
- Faster repeat queries
- Works offline (with stale data)
- Respects upstream rate limits

## 🎯 Advanced Usage

### Programmatic Access

Use the Python API client directly:

```python
import requests

# Get objects
response = requests.get('http://localhost:5050/api/objects/search?limit=100')
data = response.json()

# Analyze
for obj in data['objects']:
    if obj['analysis']['research_priority'] == 'high':
        print(f"High priority: {obj['pdes']}")
```

### Custom Filtering

Modify `app.py` to add custom filters:

```python
# Example: Filter by orbital elements
def filter_by_semimajor_axis(objects, a_min, a_max):
    return [obj for obj in objects 
            if a_min <= float(obj.get('a', 0)) <= a_max]
```

### Batch Processing

Process large datasets efficiently:

```python
# Load in batches
for offset in range(0, 1000, 100):
    objects = get_objects(limit=100, offset=offset)
    analyze_batch(objects)
    export_results(objects)
```

## 🚀 Performance Tips

### 1. Optimize Query Size
- Start with 100 objects for exploration
- Use 500+ for statistical analysis
- Avoid >1000 unless necessary (slow)

### 2. Use Caching Effectively
- First query is slow (API call)
- Repeat queries are instant (cached)
- Clear cache to force refresh: `rm -rf cache/`

### 3. Filter Early
- Apply filters before loading all data
- Use API parameters when available
- Post-process only when necessary

### 4. Export Strategically
- Export once, analyze offline
- Use CSV for spreadsheets
- Use JSON for programming

## 🎨 Customization

### Change Color Scheme

Edit `templates/index.html`:

```css
:root {
  --primary-color: #4a9eff;      /* Blue */
  --secondary-color: #5fd3ff;    /* Cyan */
  --background: #0a0e27;         /* Dark blue */
}
```

### Modify Priority Thresholds

Edit `app.py`:

```python
def _calculate_priority(missing_props, obj):
    critical_missing = len([p for p in missing_props 
                           if p in ['diameter', 'albedo']])
    
    if critical_missing >= 2:  # Change threshold here
        return 'high'
```

### Add New Properties

Edit `config.py`:

```python
CRITICAL_PROPERTIES = [
    'diameter',
    'albedo',
    'rot_per',
    'your_new_property',  # Add here
]
```

## 📊 Interpreting Results

### Completeness Scores

- **100%**: All critical properties known
  - Example: (1) Ceres - well-studied largest asteroid
  
- **75-99%**: Nearly complete characterization
  - Example: (433) Eros - NEAR mission target
  
- **50-74%**: Moderate knowledge
  - Example: Typical numbered asteroid
  
- **25-49%**: Poorly characterized
  - Example: Recently discovered NEO
  
- **0-24%**: Severely under-researched
  - Example: Faint, distant object

### Priority Badges

- **[HIGH]** - Red badge
  - Action: Immediate observation recommended
  - Reason: NEO/PHA with critical gaps
  
- **[MEDIUM]** - Yellow badge
  - Action: Should characterize soon
  - Reason: Multiple missing properties
  
- **[LOW]** - Green badge
  - Action: Routine follow-up sufficient
  - Reason: Well-characterized already

### Missing Properties

Common patterns:

1. **"diameter, albedo"**
   - No size measurement
   - Requires radar or thermal IR
   
2. **"spec_B, spec_T"**
   - No spectral classification
   - Requires visible/NIR spectroscopy
   
3. **"rot_per"**
   - No rotation period
   - Requires lightcurve photometry
   
4. **"GM"**
   - No mass measurement
   - Requires close flyby or binary system

## 🔬 Scientific Interpretation

### What the Data Tells Us

**High completeness (>80%)**:
- Object has been well-observed
- Multiple observation techniques used
- Likely a mission target or bright object
- Good candidate for comparison studies

**Low completeness (<40%)**:
- Recently discovered or faint
- Limited observation opportunities
- High scientific value (unexplored)
- Good candidate for new observations

**Missing diameter + albedo**:
- Size is uncertain
- Impact risk poorly constrained (if NEO)
- Thermal modeling needed
- Radar or WISE observations recommended

**Missing spectral type**:
- Composition unknown
- Taxonomy uncertain
- Visible/NIR spectroscopy needed
- Family membership ambiguous

## 🎓 Educational Applications

### Classroom Activities

1. **Data Quality Assessment**
   - Load 100 objects
   - Calculate average completeness
   - Identify systematic biases
   
2. **Observation Planning**
   - Find high-priority NEOs
   - Check visibility from your location
   - Write mock telescope proposal
   
3. **Mission Target Selection**
   - Filter for accessible NEOs
   - Rank by scientific value
   - Justify top choice

### Research Projects

1. **Completeness vs. Discovery Date**
   - Do older objects have more data?
   - Plot completeness over time
   
2. **Family Characterization**
   - Compare completeness across families
   - Identify under-studied families
   
3. **NEO vs. MBA Comparison**
   - Are NEOs better characterized?
   - Why or why not?

---

**Ready to Explore?**

Start the server and open http://localhost:5050 to begin your journey through the solar system! 🚀

