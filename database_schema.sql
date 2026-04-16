-- Solar System Small Bodies Database Schema
-- Convention: tables = lowercase, FIELDS = UPPERCASE
-- Source prefixes: JPL_, SSOD_, WIKI_, MPC_, etc.

-- Drop existing tables if they exist
DROP TABLE IF EXISTS small_bodies;
DROP TABLE IF EXISTS load_history;

-- Main small bodies table
CREATE TABLE small_bodies (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    SPKID BIGINT UNIQUE NOT NULL COMMENT 'JPL SPK-ID (unique identifier)',
    
    -- JPL SBDB fields
    JPL_FULL_NAME VARCHAR(255) COMMENT 'Full name from JPL',
    JPL_DESIGNATION VARCHAR(100) COMMENT 'Provisional designation',
    JPL_NAME VARCHAR(100) COMMENT 'Proper name (if any)',
    JPL_PREFIX VARCHAR(10) COMMENT 'Object prefix (A/, C/, P/, etc.)',
    JPL_NEO CHAR(1) COMMENT 'Near-Earth Object flag (Y/N)',
    JPL_PHA CHAR(1) COMMENT 'Potentially Hazardous Asteroid flag (Y/N)',
    JPL_H FLOAT COMMENT 'Absolute magnitude',
    JPL_DIAMETER FLOAT COMMENT 'Diameter in km',
    JPL_ALBEDO FLOAT COMMENT 'Geometric albedo',
    JPL_ROT_PER FLOAT COMMENT 'Rotation period in hours',
    JPL_GM FLOAT COMMENT 'GM (gravitational parameter)',
    JPL_BV FLOAT COMMENT 'B-V color index',
    JPL_UB FLOAT COMMENT 'U-B color index',
    JPL_SPEC_B VARCHAR(50) COMMENT 'Spectral type (SMASSII)',
    JPL_SPEC_T VARCHAR(50) COMMENT 'Spectral type (Tholen)',
    JPL_CONDITION_CODE INT COMMENT 'Orbit condition code (0-9)',
    JPL_RMS FLOAT COMMENT 'RMS residual of orbit fit',
    JPL_SB_KIND VARCHAR(10) COMMENT 'Small body kind (a=asteroid, c=comet)',
    JPL_SB_CLASS VARCHAR(50) COMMENT 'Small body class (NEO, TNO, etc.)',
    JPL_ORBIT_CLASS VARCHAR(100) COMMENT 'Detailed orbit classification',
    JPL_LAST_UPDATED DATETIME COMMENT 'Last update from JPL',
    
    -- SsODNet fields
    SSOD_MASS FLOAT COMMENT 'Mass in kg',
    SSOD_MASS_ERROR FLOAT COMMENT 'Mass uncertainty',
    SSOD_DENSITY FLOAT COMMENT 'Density in g/cm³',
    SSOD_DENSITY_ERROR FLOAT COMMENT 'Density uncertainty',
    SSOD_TAXONOMY VARCHAR(50) COMMENT 'Taxonomic classification',
    SSOD_BINARY BOOLEAN COMMENT 'Binary system flag',
    SSOD_LAST_UPDATED DATETIME COMMENT 'Last update from SsODNet',
    
    -- Wikipedia fields
    WIKI_TITLE VARCHAR(255) COMMENT 'Wikipedia article title',
    WIKI_SUMMARY TEXT COMMENT 'Short summary',
    WIKI_URL VARCHAR(512) COMMENT 'Wikipedia article URL',
    WIKI_THUMBNAIL VARCHAR(512) COMMENT 'Thumbnail image URL',
    WIKI_LAST_UPDATED DATETIME COMMENT 'Last update from Wikipedia',
    
    -- Computed/Derived fields
    COMPLETENESS_SCORE FLOAT COMMENT 'Data completeness percentage (0-100)',
    RESEARCH_PRIORITY ENUM('high', 'medium', 'low', 'unknown') DEFAULT 'unknown' COMMENT 'Research priority classification',
    MISSING_PROPERTIES TEXT COMMENT 'JSON array of missing properties',
    PRESENT_PROPERTIES TEXT COMMENT 'JSON array of present properties',
    
    -- Metadata
    CREATED_AT DATETIME DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_jpl_sb_class (JPL_SB_CLASS),
    INDEX idx_jpl_neo (JPL_NEO),
    INDEX idx_jpl_pha (JPL_PHA),
    INDEX idx_jpl_h (JPL_H),
    INDEX idx_jpl_diameter (JPL_DIAMETER),
    INDEX idx_completeness (COMPLETENESS_SCORE),
    INDEX idx_priority (RESEARCH_PRIORITY),
    INDEX idx_spkid (SPKID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Small solar system bodies from multiple data sources';

-- Load history tracking table
CREATE TABLE load_history (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    SOURCE VARCHAR(50) NOT NULL COMMENT 'Data source (JPL, SSOD, WIKI, etc.)',
    LOAD_TYPE VARCHAR(50) NOT NULL COMMENT 'Type of load (full, incremental, update)',
    OBJECTS_PROCESSED INT DEFAULT 0 COMMENT 'Number of objects processed',
    OBJECTS_ADDED INT DEFAULT 0 COMMENT 'Number of new objects added',
    OBJECTS_UPDATED INT DEFAULT 0 COMMENT 'Number of objects updated',
    OBJECTS_FAILED INT DEFAULT 0 COMMENT 'Number of objects that failed',
    STATUS ENUM('running', 'completed', 'failed', 'cancelled') DEFAULT 'running',
    ERROR_MESSAGE TEXT COMMENT 'Error details if failed',
    STARTED_AT DATETIME DEFAULT CURRENT_TIMESTAMP,
    COMPLETED_AT DATETIME NULL,
    DURATION_SECONDS INT COMMENT 'Load duration in seconds',
    
    INDEX idx_source (SOURCE),
    INDEX idx_status (STATUS),
    INDEX idx_started (STARTED_AT)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='History of data loading operations';




