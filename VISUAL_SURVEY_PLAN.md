# 🔭 Visual Survey Search Implementation Plan

## Overview

Add visual search capabilities to the object detail panel, allowing automatic discovery of images across 10+ major astronomical surveys.

---

## Architecture Design

```
┌─────────────────────────────────────────────────────────────────┐
│                     OBJECT DETAIL PANEL                         │
│  (Current: JPL + SsODNet + Wikipedia + Orbital Plot)           │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│            NEW TAB: "Visual Survey Search" 🔍                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: Gather Object Identifiers                             │
│    • MPC designation (packed & unpacked)                        │
│    • JPL SPK-ID                                                 │
│    • Alternate names from Wikipedia                            │
│    • Orbital elements & uncertainties                          │
│                                                                 │
│  Step 2: Generate Ephemerides                                  │
│    • Use JPL Horizons API                                      │
│    • Time range: Survey-specific (2000-2024)                   │
│    • Output: RA, Dec, Vmag, rate, uncertainty ellipse          │
│    • Resolution: 1-hour or 3-hour intervals                    │
│                                                                 │
│  Step 3: Query Survey Footprints                               │
│    • Pre-filter by footprint overlap (HEALPix)                 │
│    • Only query surveys with potential coverage                │
│    • Request cutouts where available                           │
│                                                                 │
│  Step 4: Display Results                                       │
│    • Gallery view of all found images                          │
│    • Metadata: Survey, date, filter, magnitude                 │
│    • Interactive: zoom, enhance, mark detections               │
│    • Export: Download images, generate report                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation (Week 1-2)

### 1.1 Create Survey Module Structure

```python
# surveys/__init__.py
# surveys/base.py - Abstract base class
# surveys/panstarrs.py
# surveys/ztf.py
# surveys/sdss.py
# surveys/neowise.py
# surveys/decam.py
```

### 1.2 Ephemeris Generator

Use JPL Horizons API:
- Input: Object designation, time range, observer location
- Output: RA/Dec table with uncertainties
- Cache results for performance

### 1.3 Survey Registry

```python
SURVEYS = {
    'panstarrs': {
        'name': 'Pan-STARRS',
        'years': (2009, 2024),
        'depth': 24.0,  # limiting magnitude
        'bands': ['g', 'r', 'i', 'z', 'y'],
        'api': 'https://ps1images.stsci.edu/cgi-bin/ps1cutouts',
        'priority': 5  # 1-5, 5 = best
    },
    'ztf': {
        'name': 'ZTF',
        'years': (2018, 2024),
        'depth': 20.5,
        'bands': ['g', 'r', 'i'],
        'api': 'https://irsa.ipac.caltech.edu/ibe/search/ztf',
        'priority': 4
    },
    # ... more surveys
}
```

---

## Phase 2: Proof of Concept (Week 3-4)

### Start with 2 Surveys

**Priority 1: Pan-STARRS** (easiest API)
- STScI provides simple cutout service
- Excellent coverage (3π sr)
- Well-documented API

**Priority 2: ZTF** (current data)
- Active survey (2018-present)
- Good for recent discoveries
- Public data access via IRSA

### Implementation Steps

#### 2.1 Pan-STARRS Integration

```python
# surveys/panstarrs.py

import requests
from typing import List, Dict, Tuple
from astropy.coordinates import SkyCoord
import astropy.units as u

class PanSTARRSClient:
    BASE_URL = "https://ps1images.stsci.edu/cgi-bin/ps1cutouts"
    
    def __init__(self):
        self.coverage = self._load_coverage_map()
    
    def check_coverage(self, ra: float, dec: float) -> bool:
        """Check if position is in Pan-STARRS footprint"""
        # Pan-STARRS covers 3π steradians (3/4 of sky)
        # Exclude galactic plane and far south
        if dec < -30:
            return False
        return True
    
    def get_cutout(self, ra: float, dec: float, 
                   date_range: Tuple[str, str],
                   size: int = 240,
                   filters: List[str] = ['g', 'r', 'i']) -> List[Dict]:
        """
        Request image cutouts for given position
        
        Args:
            ra: Right Ascension (degrees)
            dec: Declination (degrees)
            date_range: (start_date, end_date) as 'YYYY-MM-DD'
            size: Cutout size in pixels (default 240 = 1 arcmin)
            filters: List of filters to query
        
        Returns:
            List of dicts with image URLs and metadata
        """
        results = []
        
        for filt in filters:
            params = {
                'ra': ra,
                'dec': dec,
                'size': size,
                'filter': filt,
                'format': 'jpg',
                'output_size': 0  # actual size
            }
            
            try:
                response = requests.get(self.BASE_URL, params=params, timeout=30)
                if response.status_code == 200:
                    results.append({
                        'survey': 'Pan-STARRS',
                        'filter': filt,
                        'ra': ra,
                        'dec': dec,
                        'image_url': response.url,
                        'date_range': date_range,
                        'size_arcsec': size * 0.25  # PS1 pixel scale
                    })
            except Exception as e:
                print(f"Error fetching Pan-STARRS {filt}: {e}")
        
        return results
    
    def search_object(self, ephemeris: List[Dict]) -> List[Dict]:
        """
        Search for object across entire ephemeris
        
        Args:
            ephemeris: List of {time, ra, dec, vmag, uncertainty}
        
        Returns:
            List of found images
        """
        results = []
        
        # Sample ephemeris (not every hour, maybe every day or week)
        sample_rate = 24 if len(ephemeris) > 1000 else 1
        
        for i, position in enumerate(ephemeris[::sample_rate]):
            if self.check_coverage(position['ra'], position['dec']):
                cutouts = self.get_cutout(
                    position['ra'], 
                    position['dec'],
                    date_range=(position['time'], position['time']),
                    filters=['r']  # Start with r-band only
                )
                results.extend(cutouts)
        
        return results
```

#### 2.2 Ephemeris Generator

```python
# ephemeris_generator.py

import requests
from datetime import datetime, timedelta
from typing import List, Dict

class EphemerisGenerator:
    """Generate ephemerides using JPL Horizons API"""
    
    HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
    
    def generate(self, 
                 designation: str,
                 start_date: str,
                 end_date: str,
                 step: str = '1d',  # 1 day
                 observer: str = '500') -> List[Dict]:
        """
        Generate ephemeris for object
        
        Args:
            designation: Object designation (e.g., '433', '2023 DW')
            start_date: 'YYYY-MM-DD'
            end_date: 'YYYY-MM-DD'
            step: Time step ('1h', '3h', '1d')
            observer: Observer location ('500' = geocenter)
        
        Returns:
            List of ephemeris points
        """
        params = {
            'format': 'json',
            'COMMAND': f"'{designation}'",
            'OBJ_DATA': 'YES',
            'MAKE_EPHEM': 'YES',
            'EPHEM_TYPE': 'OBSERVER',
            'CENTER': observer,
            'START_TIME': start_date,
            'STOP_TIME': end_date,
            'STEP_SIZE': step,
            'QUANTITIES': '1,9,20,23,24',  # RA, DEC, Vmag, etc.
        }
        
        try:
            response = requests.get(self.HORIZONS_URL, params=params, timeout=60)
            data = response.json()
            
            # Parse ephemeris data
            return self._parse_horizons_response(data)
            
        except Exception as e:
            print(f"Error generating ephemeris: {e}")
            return []
    
    def _parse_horizons_response(self, data: Dict) -> List[Dict]:
        """Parse Horizons JSON response into structured ephemeris"""
        ephemeris = []
        
        if 'result' in data:
            lines = data['result'].split('\n')
            
            # Find data section (starts after $$SOE marker)
            in_data = False
            for line in lines:
                if '$$SOE' in line:
                    in_data = True
                    continue
                elif '$$EOE' in line:
                    break
                elif in_data and line.strip():
                    # Parse ephemeris line
                    # Format: Date RA DEC Vmag ...
                    parts = line.split()
                    if len(parts) >= 4:
                        ephemeris.append({
                            'time': parts[0],
                            'ra': float(parts[1]),
                            'dec': float(parts[2]),
                            'vmag': float(parts[3]) if parts[3] != 'n.a.' else None
                        })
        
        return ephemeris
```

#### 2.3 Streamlit Tab Integration

```python
# Add to streamlit_app.py detail panel

def show_visual_survey_search(designation: str, jpl_data: Dict, ssodnet_data: Dict):
    """New tab for visual survey search"""
    
    st.markdown("### 🔍 Visual Survey Search")
    st.info("Search for this object in archived sky surveys")
    
    # Step 1: Gather identifiers
    with st.expander("📋 Step 1: Object Identifiers", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Primary Identifiers:**")
            st.write(f"• Designation: `{designation}`")
            if jpl_data and 'object' in jpl_data:
                spkid = jpl_data['object'].get('spkid')
                st.write(f"• SPK-ID: `{spkid}`")
                fullname = jpl_data['object'].get('fullname')
                st.write(f"• Full Name: `{fullname}`")
        
        with col2:
            st.markdown("**Alternate Names:**")
            # Extract from Wikipedia if available
            st.write("• (from Wikipedia data)")
    
    # Step 2: Generate ephemeris
    with st.expander("📈 Step 2: Generate Ephemeris", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_date = st.date_input("Start Date", 
                                       value=datetime(2010, 1, 1))
        with col2:
            end_date = st.date_input("End Date",
                                     value=datetime.now())
        with col3:
            step = st.selectbox("Time Step", 
                               ['1h', '3h', '1d', '1w'],
                               index=2)
        
        if st.button("🚀 Generate Ephemeris", type="primary"):
            with st.spinner("Querying JPL Horizons..."):
                ephem_gen = EphemerisGenerator()
                ephemeris = ephem_gen.generate(
                    designation,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d'),
                    step
                )
                
                if ephemeris:
                    st.success(f"✓ Generated {len(ephemeris)} ephemeris points")
                    st.session_state['ephemeris'] = ephemeris
                    
                    # Show sample
                    df = pd.DataFrame(ephemeris[:10])
                    st.dataframe(df)
                else:
                    st.error("Failed to generate ephemeris")
    
    # Step 3: Survey search
    if 'ephemeris' in st.session_state:
        with st.expander("🔭 Step 3: Search Surveys", expanded=True):
            st.markdown("**Available Surveys:**")
            
            surveys_to_search = st.multiselect(
                "Select surveys to search:",
                ['Pan-STARRS', 'ZTF', 'SDSS', 'NEOWISE'],
                default=['Pan-STARRS']
            )
            
            if st.button("🔍 Search Selected Surveys", type="primary"):
                results = []
                
                for survey_name in surveys_to_search:
                    with st.spinner(f"Searching {survey_name}..."):
                        if survey_name == 'Pan-STARRS':
                            ps_client = PanSTARRSClient()
                            survey_results = ps_client.search_object(
                                st.session_state['ephemeris']
                            )
                            results.extend(survey_results)
                
                st.session_state['survey_results'] = results
                st.success(f"✓ Found {len(results)} potential images")
    
    # Step 4: Display results
    if 'survey_results' in st.session_state:
        with st.expander("📸 Step 4: View Results", expanded=True):
            results = st.session_state['survey_results']
            
            if results:
                st.markdown(f"**Found {len(results)} images across surveys**")
                
                # Gallery view
                cols = st.columns(3)
                for i, result in enumerate(results[:12]):  # Show first 12
                    with cols[i % 3]:
                        st.image(result['image_url'], 
                                caption=f"{result['survey']} {result['filter']}")
                        st.caption(f"RA: {result['ra']:.4f}°, Dec: {result['dec']:.4f}°")
            else:
                st.warning("No images found")
```

---

## Phase 3: Expand to More Surveys (Week 5-8)

### Survey Priority Order

1. ✅ **Pan-STARRS** (Phase 2)
2. ✅ **ZTF** (Phase 2)
3. **SDSS** - Historical data (2000-2009)
4. **NEOWISE** - Infrared (2010-2024)
5. **DECam** - Deep southern sky
6. **CFHT** - MegaCam archive
7. **Subaru** - HSC archive
8. **ATLAS** - All-sky survey
9. **Catalina Sky Survey**
10. **DSS2** - Historical plates

---

## Phase 4: Advanced Features (Week 9-12)

### 4.1 Footprint Pre-filtering

Use HEALPix tiles to quickly determine if a position falls within survey coverage.

### 4.2 Streak Detection

For fast-moving objects, implement trail detection:
- Hough transform
- Motion vector analysis
- Tracklet linking

### 4.3 Automated Detection

- Blink comparator
- Difference imaging
- Motion detection algorithms

### 4.4 Export & Reporting

- PDF report generation
- All images in ZIP file
- CSV of metadata
- Light curve plotting

---

## File Structure

```
Solar-System/
├── surveys/
│   ├── __init__.py
│   ├── base.py                 # Abstract base class
│   ├── panstarrs.py
│   ├── ztf.py
│   ├── sdss.py
│   ├── neowise.py
│   └── registry.py             # Survey metadata
│
├── ephemeris_generator.py      # JPL Horizons interface
├── footprint_checker.py        # HEALPix coverage
├── visual_search.py            # Main search orchestrator
│
└── streamlit_app.py            # Add visual search tab
```

---

## API Endpoints Reference

### Pan-STARRS
- **URL:** https://ps1images.stsci.edu/cgi-bin/ps1cutouts
- **Docs:** https://ps1images.stsci.edu/ps1_dr2_api.html
- **Auth:** None required

### ZTF
- **URL:** https://irsa.ipac.caltech.edu/ibe/search/ztf
- **Docs:** https://irsa.ipac.caltech.edu/docs/program_interface/ztf_api.html
- **Auth:** None for public data

### SDSS
- **URL:** https://skyserver.sdss.org/dr18/SkyServerWS/ImgCutout/getjpeg
- **Docs:** https://skyserver.sdss.org/dr18/help/docs/api.aspx
- **Auth:** None required

### NEOWISE
- **URL:** https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query
- **Docs:** https://irsa.ipac.caltech.edu/docs/program_interface/api.html
- **Auth:** None required

### JPL Horizons
- **URL:** https://ssd.jpl.nasa.gov/api/horizons.api
- **Docs:** https://ssd-api.jpl.nasa.gov/doc/horizons.html
- **Auth:** None required

---

## Testing Strategy

### Test Objects

1. **433 Eros** - Well-observed NEO, many images
2. **1I/'Oumuamua** - Interstellar, limited coverage
3. **2I/Borisov** - Comet, recent discovery
4. **99942 Apophis** - PHA, excellent coverage
5. **Random MBA** - Check footprint logic

### Success Criteria

- Ephemeris generation: < 5 seconds
- Survey search: < 30 seconds per survey
- Image retrieval: < 2 seconds per cutout
- No false positives (coverage check working)
- At least 50% of known detections found

---

## Estimated Timeline

- **Phase 1** (Foundation): 2 weeks
- **Phase 2** (PoC - 2 surveys): 2 weeks
- **Phase 3** (Add 8 more surveys): 4 weeks
- **Phase 4** (Advanced features): 4 weeks

**Total:** ~12 weeks for full implementation

---

## Next Immediate Steps

1. ✅ Create `surveys/` directory structure
2. ✅ Implement `EphemerisGenerator` class
3. ✅ Implement `PanSTARRSClient` class
4. ✅ Add visual search tab to Streamlit app
5. ✅ Test with 433 Eros
6. ✅ Add ZTF support
7. Iterate and expand

---

## Questions to Consider

1. **Should we cache ephemerides?** Yes - store in cache/ with 30-day expiry
2. **How to handle slow APIs?** Background tasks + progress bars
3. **Storage for downloaded images?** Temporary cache, auto-cleanup after 24h
4. **Rate limiting?** Respect survey API limits, add delays if needed
5. **Failed queries?** Retry logic with exponential backoff

---

**This feature would make your app unique in the field - no other tool provides automated visual survey searches across 10+ archives from a single panel!** 🚀

