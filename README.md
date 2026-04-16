# Solar System Small Bodies Explorer

A web-based application for exploring and analyzing under-researched small solar system bodies, with focus on identifying targets for robotic exploration.

## Overview

This application integrates multiple data sources to help identify research gaps in our knowledge of asteroids, comets, and other small bodies:

- **JPL Small-Body Database (SBDB)**: NASA's comprehensive database of orbital and physical properties
- **SsODNet**: IMCCE's Solar System Object Database Network with ~1.3M objects and ~190M properties
- **Data Gap Analysis**: Automated identification of objects with missing critical properties
- **Research Prioritization**: Ranking system for exploration targets based on completeness and scientific value

## Features

### 1. Object Explorer
- Search and browse small solar system bodies
- View completeness scores for each object
- Identify missing physical properties (diameter, albedo, rotation period, spectral type, etc.)
- Filter by data source (JPL SBDB, SsODNet)

### 2. Data Analytics
- Property coverage visualization
- Statistical analysis of dataset completeness
- Identify systematic gaps in observations

### 3. Under-Researched Objects
- Automated identification of high-priority targets
- Focus on NEOs (Near-Earth Objects) and PHAs (Potentially Hazardous Asteroids)
- Ranking by research priority and completeness
- Export capabilities for further analysis

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Setup

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to:
```
http://localhost:5050
```

## Usage

### Basic Workflow

1. **Load Objects**: Click "Load Objects" to fetch data from JPL SBDB
2. **Explore Data**: Browse the table to see completeness scores and missing properties
3. **Analyze Gaps**: Switch to "Data Analytics" tab to see property coverage statistics
4. **Find Targets**: Use "Under-Researched" tab to identify high-priority objects
5. **Export**: Download CSV files for further analysis

### API Endpoints

The application provides several REST API endpoints:

- `GET /api/objects/search?source=jpl&limit=100` - Search for objects
- `GET /api/objects/<designation>` - Get detailed object information
- `GET /api/stats/completeness` - Get completeness statistics
- `GET /api/under-researched?priority=high&limit=50` - Find under-researched objects

### Priority Levels

Objects are ranked by research priority:

- **High**: NEOs/PHAs missing 2+ critical properties (diameter, albedo, spectral type)
- **Medium**: Any object missing 3+ critical properties
- **Low**: Objects with relatively complete data

### Critical Properties Tracked

- **diameter**: Object size
- **albedo**: Surface reflectivity
- **rot_per**: Rotation period
- **H**: Absolute magnitude
- **spec_B**: Spectral type (Bus taxonomy)
- **spec_T**: Spectral type (Tholen taxonomy)
- **GM**: Gravitational parameter (mass)
- **BV**: B-V color index
- **UB**: U-B color index

## Data Sources

### JPL Small-Body Database (SBDB)
- URL: https://ssd-api.jpl.nasa.gov/
- Coverage: ~1.2M objects
- Focus: Orbital elements, physical properties
- Update frequency: Daily

### SsODNet (IMCCE)
- URL: https://ssp.imcce.fr/webservices/ssodnet/
- Coverage: ~1.3M objects, ~190M properties
- Focus: Comprehensive multi-source compilation
- Features: ssoCard, datacloud, advanced search (in development)

## Architecture

### Backend (Flask)
- `app.py`: Main application server
- API clients for JPL SBDB and SsODNet
- Data caching layer (24-hour expiry)
- Completeness analysis engine
- Priority ranking algorithm

### Frontend (HTML/CSS/JavaScript)
- Responsive single-page application
- Real-time data visualization
- Interactive filtering and sorting
- CSV export functionality

### Caching
- Local file-based cache in `cache/` directory
- 24-hour expiry for API responses
- Reduces API load and improves performance

## Future Enhancements

### Planned Features
1. **Additional Data Sources**
   - NASA Exoplanet Archive (for comparative planetology)
   - Minor Planet Center (MPC) observations
   - WISE/NEOWISE thermal data
   - Gaia stellar occultations

2. **Advanced Analytics**
   - Machine learning for property prediction
   - Family membership analysis
   - Collision probability calculations
   - Mission feasibility scoring (delta-v, accessibility)

3. **Robotic Exploration Planning**
   - Trajectory optimization
   - Mission duration estimates
   - Scientific value scoring
   - Multi-target tour planning

4. **Collaborative Features**
   - User annotations and notes
   - Observation request integration
   - Data contribution workflow
   - Community prioritization voting

## Contributing

This is a research tool under active development. Suggestions for improvements:

- Additional data sources to integrate
- New analysis metrics
- Visualization improvements
- Export format options
- API enhancements

## Technical Notes

### Rate Limiting
- JPL SBDB: No official limit, but use caching to be respectful
- SsODNet: No official limit documented

### Data Quality
- Property values may be estimates with varying uncertainties
- Missing data doesn't always mean "unknown" - may be "not applicable"
- Cross-reference multiple sources when possible

### Performance
- Initial load fetches 100-500 objects
- Caching significantly improves repeat queries
- Large dataset queries (>1000 objects) may take several seconds

## License

This tool is for research and educational purposes. Data sources have their own terms of use:
- JPL SBDB: Public domain (NASA)
- SsODNet: Check IMCCE terms of service

## Contact & Support

For questions about small solar system bodies research or this tool, consult:
- JPL SBDB documentation: https://ssd-api.jpl.nasa.gov/doc/
- SsODNet documentation: https://ssp.imcce.fr/webservices/ssodnet/
- Minor Planet Center: https://www.minorplanetcenter.net/

## Acknowledgments

Data provided by:
- NASA Jet Propulsion Laboratory (JPL)
- Institut de Mécanique Céleste et de Calcul des Éphémérides (IMCCE)
- Minor Planet Center (MPC)
- International Astronomical Union (IAU)

---

**Version**: 1.0.0  
**Last Updated**: November 2025  
**Status**: Prototype - Active Development

