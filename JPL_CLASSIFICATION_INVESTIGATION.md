# JPL SBDB Classification Investigation Results
**Date:** 2025-11-02  
**Goal:** Find all available object classifications to subdivide categories into ≤100K chunks

---

## Summary of Findings

### ✅ WORKING CLASSIFICATIONS (sb-class with sb-kind=a)

| Code | Description | Count | Status |
|------|-------------|-------|--------|
| **IEO** | Interior to Earth Orbit | 37 | ✅ Under 100K |
| **ATE** | Aten (NEO subtype) | 3,193 | ✅ Under 100K |
| **APO** | Apollo (NEO subtype) | 22,550 | ✅ Under 100K |
| **AMO** | Amor (NEO subtype) | 14,062 | ✅ Under 100K |
| **TNO** | Trans-Neptunian Objects | 5,575 | ✅ Under 100K |
| **CEN** | Centaurs | 967 | ✅ Under 100K |
| **TJN** | Jupiter Trojans | 15,467 | ✅ Under 100K |
| **MCA** | Mars Crossers | 28,701 | ✅ Under 100K |
| **OMB** | Outer Main Belt | 46,401 | ✅ Under 100K |
| **IMB** | Inner Main Belt | 31,682 | ✅ Under 100K |
| **AST** | Asteroid (generic) | 147 | ✅ Under 100K |
| **HYA** | Hyperbolic Asteroid | 6 | ✅ Under 100K |

**Total with sb-class:** 208,593 objects

---

### ✅ COMET CLASSIFICATIONS (sb-kind=c)

| Code | Description | Count | Status |
|------|-------------|-------|--------|
| **All Comets** | (no sb-class) | 4,037 | ✅ Under 100K |
| **COM** | Comet (generic) | 718 | ✅ Under 100K |
| **JFC** | Jupiter Family Comet | 17 | ✅ Under 100K |
| **HTC** | Halley-Type Comet | 109 | ✅ Under 100K |
| **PAR** | Parabolic Comet | 1,762 | ✅ Under 100K |
| **HYP** | Hyperbolic Comet | 509 | ✅ Under 100K |
| **ETc** | Encke-Type Comet | 75 | ✅ Under 100K |
| **CTc** | Chiron-Type Comet | 22 | ✅ Under 100K |

**Total comets:** 4,037 objects

---

### ❌ THE PROBLEM: 1.26M UNCLASSIFIED OBJECTS

**Total asteroids (sb-kind=a):** 1,472,750  
**With sb-class:** 208,593  
**WITHOUT sb-class:** **1,264,157** ❌ **WAY OVER 100K LIMIT!**

These are likely:
- Main Belt Asteroids without specific orbital classification
- Newly discovered objects pending classification
- Objects with insufficient orbital data for classification

---

### ❌ NON-WORKING FILTERS

**These filters return N/A or errors:**
- `MBA` (as sb-class) - doesn't exist
- `MBA-I`, `MBA-M`, `MBA-O` - don't exist
- `NEO` (as sb-class) - doesn't work (NEO is a grouping, not a class)
- `numbered=true/false` - parameter not recognized
- `a-min`, `a-max` (semi-major axis ranges) - not recognized
- `e-min`, `e-max` (eccentricity ranges) - not recognized
- `H-min`, `H-max` (magnitude ranges) - not recognized
- `SDO`, `DDO` (Scattered/Detached Disk) - don't exist as separate classes

---

## Proposed Hierarchical Structure

### Option A: Use What We Have (Leave 1.26M as "MBA - Unclassified")

```
☐ NEO - Near-Earth Objects (39,805)
    ☐ All NEOs
    ☐ IEO - Interior to Earth (37)
    ☐ ATE - Aten (3,193)
    ☐ APO - Apollo (22,550)
    ☐ AMO - Amor (14,062)

☐ MBA - Main Belt (1,264,157) ⚠️ TOO LARGE
    ☐ All MBA (unclassified) - 1,264,157 ❌
    ☐ IMB - Inner Main Belt (31,682) ✅
    ☐ OMB - Outer Main Belt (46,401) ✅

☐ MCA - Mars Crossers (28,701) ✅

☐ TNO - Trans-Neptunian (5,575) ✅

☐ CEN - Centaurs (967) ✅

☐ TJN - Jupiter Trojans (15,467) ✅

☐ Comets (4,037) ✅
    ☐ All Comets
    ☐ JFC - Jupiter Family (17)
    ☐ HTC - Halley-Type (109)
    ☐ PAR - Parabolic (1,762)
    ☐ HYP - Hyperbolic (509)
    ☐ ETc - Encke-Type (75)
    ☐ CTc - Chiron-Type (22)
    ☐ COM - Other (718)

☐ Special Objects
    ☐ ISO - Interstellar (3) ✅
    ☐ HYA - Hyperbolic Asteroids (6) ✅
    ☐ AST - Other Asteroids (147) ✅
```

**PROBLEM:** The 1.26M unclassified MBA objects cannot be downloaded in one go!

---

### Option B: Warn User About Large Categories

Add a warning in the UI:
```
⚠️ MBA (Unclassified) contains 1,264,157 objects
   Loading all objects may take several minutes and use significant memory.
   Consider using IMB or OMB subcategories instead.
```

Then allow users to:
1. Load in batches (100K at a time)
2. Use client-side pagination
3. Or just accept the limitation

---

### Option C: Contact JPL / Check Documentation

There might be additional API parameters we're missing:
- Numbered vs provisional designations
- Discovery date ranges
- Orbital quality codes
- Proper orbital element ranges

**Next steps:**
1. Check JPL SBDB API documentation more thoroughly
2. Look for examples of subdividing large queries
3. Consider if we need to implement server-side pagination for MBA

---

## Immediate Recommendations

1. **Implement hierarchical UI with what we have** ✅
2. **Add all working classifications** ✅
3. **Add warning for MBA (unclassified)** ⚠️
4. **Set max limit to 100K and inform user** ⚠️
5. **Research if JPL has pagination or additional filters** 🔍

---

## Categories Ready for Implementation

**All under 100K (safe to implement):**
- NEO subtypes (IEO, ATE, APO, AMO)
- IMB, OMB (but not full MBA)
- MCA, TNO, CEN, TJN
- All comet types
- ISO, HYA, AST

**Over 100K (needs special handling):**
- MBA unclassified: 1,264,157 objects




