# Solar System Database Loader

Separate application for loading and merging small body data from multiple sources into MariaDB.

## Architecture

```
┌─────────────────────────────────────────┐
│     Loader Application (Port 5060)     │
│  ┌──────────┐  ┌──────────┐            │
│  │   JPL    │  │ SsODNet  │            │
│  │  Loader  │  │  Loader  │            │
│  └─────┬────┘  └─────┬────┘            │
│        └─────────┬───────┘              │
│                  ▼                       │
│         ┌──────────────┐                │
│         │   MariaDB    │                │
│         │ small_bodies │                │
│         └──────────────┘                │
└─────────────────────────────────────────┘
```

## Database Schema

### Naming Conventions
- **Tables**: lowercase (e.g., `small_bodies`, `load_history`)
- **FIELDS**: UPPERCASE (e.g., `SPKID`, `JPL_FULL_NAME`)
- **Source Prefixes**: `JPL_`, `SSOD_`, `WIKI_`, `MPC_`

### Main Table: `small_bodies`

| Field | Type | Description |
|-------|------|-------------|
| ID | INT | Primary key |
| SPKID | BIGINT | JPL SPK-ID (unique) |
| JPL_FULL_NAME | VARCHAR(255) | Full name from JPL |
| JPL_DESIGNATION | VARCHAR(100) | Provisional designation |
| JPL_H | FLOAT | Absolute magnitude |
| JPL_DIAMETER | FLOAT | Diameter in km |
| JPL_SB_CLASS | VARCHAR(50) | Small body class |
| SSOD_MASS | FLOAT | Mass from SsODNet |
| SSOD_DENSITY | FLOAT | Density from SsODNet |
| WIKI_TITLE | VARCHAR(255) | Wikipedia article title |
| COMPLETENESS_SCORE | FLOAT | Data completeness (0-100) |
| RESEARCH_PRIORITY | ENUM | Research priority |

See `database_schema.sql` for complete schema.

## Installation

### 1. Install MariaDB

**macOS:**
```bash
brew install mariadb
brew services start mariadb
```

**Ubuntu/Debian:**
```bash
sudo apt-get install mariadb-server
sudo systemctl start mariadb
```

### 2. Install Python Dependencies

```bash
pip install pymysql flask flask-cors requests
```

### 3. Setup Database

```bash
chmod +x setup_database.sh
./setup_database.sh
```

This will:
- Create database `solar_system`
- Create user `solar_user`
- Load schema from `database_schema.sql`

### 4. Configure Environment

Create `.env` file or export variables:

```bash
export DB_HOST=localhost
export DB_PORT=3306
export DB_NAME=solar_system
export DB_USER=solar_user
export DB_PASSWORD=solar_pass_2025
```

## Usage

### Start Loader Application

```bash
python loader_app.py
```

Runs on **port 5060** (separate from main app on 5050)

### API Endpoints

#### Test Database Connection
```bash
curl http://localhost:5060/api/loader/test-db
```

#### Get Loader Status
```bash
curl http://localhost:5060/api/loader/status
```

#### Load JPL Data

**Load all asteroids (limit 100K):**
```bash
curl -X POST http://localhost:5060/api/loader/load-jpl \
  -H "Content-Type: application/json" \
  -d '{"sb_kind": "a", "limit": 100000}'
```

**Load specific class (e.g., NEO):**
```bash
curl -X POST http://localhost:5060/api/loader/load-jpl \
  -H "Content-Type: application/json" \
  -d '{"sb_kind": "a", "sb_class": "NEO", "limit": 50000}'
```

**Load comets:**
```bash
curl -X POST http://localhost:5060/api/loader/load-jpl \
  -H "Content-Type: application/json" \
  -d '{"sb_kind": "c", "limit": 10000}'
```

### Loading Strategy

To load all data efficiently:

```bash
# 1. Load classified objects first (fast, under 100K each)
curl -X POST http://localhost:5060/api/loader/load-jpl -d '{"sb_class": "NEO", "limit": 50000}'
curl -X POST http://localhost:5060/api/loader/load-jpl -d '{"sb_class": "TNO", "limit": 10000}'
curl -X POST http://localhost:5060/api/loader/load-jpl -d '{"sb_class": "IMB", "limit": 50000}'
curl -X POST http://localhost:5060/api/loader/load-jpl -d '{"sb_class": "OMB", "limit": 50000}'
# ... etc for all classes

# 2. Load unclassified in 100K chunks (will need multiple runs)
curl -X POST http://localhost:5060/api/loader/load-jpl -d '{"sb_kind": "a", "limit": 100000}'

# 3. Load comets
curl -X POST http://localhost:5060/api/loader/load-jpl -d '{"sb_kind": "c", "limit": 5000}'
```

## Progress Tracking

The loader tracks all operations in the `load_history` table:

```sql
SELECT * FROM load_history ORDER BY STARTED_AT DESC LIMIT 10;
```

Fields tracked:
- SOURCE (JPL, SSOD, WIKI)
- LOAD_TYPE (full, incremental, update)
- OBJECTS_PROCESSED, OBJECTS_ADDED, OBJECTS_UPDATED, OBJECTS_FAILED
- STATUS (running, completed, failed)
- DURATION_SECONDS

## Next Steps

1. ✅ Database schema created
2. ✅ Loader application built
3. ⏳ Load JPL data
4. ⏳ Add SsODNet enrichment
5. ⏳ Add Wikipedia data
6. ⏳ Update main Flask app to query database
7. ⏳ Add periodic refresh mechanism

## Advantages Over Direct API

- ✅ **No pagination limits** - query any range
- ✅ **Fast queries** - indexed database
- ✅ **Offline access** - no API dependency
- ✅ **Multi-source integration** - JPL + SsODNet + Wikipedia
- ✅ **Custom fields** - completeness scores, priorities
- ✅ **Complex filtering** - SQL power for advanced queries




