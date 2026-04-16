#!/usr/bin/env python3
"""Generate unified solar system catalog files.

Usage:
    python generate_catalog.py core          # Planets + Moons + Notable bodies
    python generate_catalog.py neo           # All NEOs from SBDB
    python generate_catalog.py neocp         # MPC NEOCP candidates (pre-JPL)
    python generate_catalog.py mba [--limit] # Main Belt from SBDB
    python generate_catalog.py tno [--limit] # TNOs from SBDB
    python generate_catalog.py comet [--limit]
    python generate_catalog.py all           # Rebuild everything

Output: cache/catalog_<name>.json

Each catalog file uses the same unified object schema so all consumers
(Flask API, Streamlit, Quest VR) speak one format.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ── Spectral color mapping (matches solar_scene.py) ────────────────────

SPECTRAL_COLORS = {
    "S": "#C8886E", "C": "#5A5A5A", "M": "#A0A0B0", "V": "#8B7D6B",
    "X": "#808080", "D": "#704030", "B": "#4A4A5A", "A": "#C8A070",
    "Q": "#B08060", "R": "#A05040", "T": "#604020",
}
DEFAULT_COLOR = "#808080"

BODY_COLORS = {
    "Sun": "#FFF264", "Mercury": "#B3B3A6", "Venus": "#F2D98D",
    "Moon": "#D9D9E0", "Mars": "#E65A33", "Jupiter": "#D9A673",
    "Saturn": "#E6CC8D", "Uranus": "#80D9E6", "Neptune": "#5973F2",
    "Pluto": "#C4A882", "Earth": "#3366E6",
}

PLANET_TEXTURES = {
    "sun": "https://www.solarsystemscope.com/textures/download/2k_sun.jpg",
    "mercury": "https://www.solarsystemscope.com/textures/download/2k_mercury.jpg",
    "venus": "https://www.solarsystemscope.com/textures/download/2k_venus_surface.jpg",
    "earth": "https://www.solarsystemscope.com/textures/download/2k_earth_daymap.jpg",
    "moon": "https://www.solarsystemscope.com/textures/download/2k_moon.jpg",
    "mars": "https://www.solarsystemscope.com/textures/download/2k_mars.jpg",
    "jupiter": "https://www.solarsystemscope.com/textures/download/2k_jupiter.jpg",
    "saturn": "https://www.solarsystemscope.com/textures/download/2k_saturn.jpg",
    "uranus": "https://www.solarsystemscope.com/textures/download/2k_uranus.jpg",
    "neptune": "https://www.solarsystemscope.com/textures/download/2k_neptune.jpg",
    "pluto": "https://www.solarsystemscope.com/textures/download/2k_makemake_fictional.jpg",
    "io": "https://www.solarsystemscope.com/textures/download/2k_io.jpg",
    "europa": "https://www.solarsystemscope.com/textures/download/2k_europa.jpg",
    "ganymede": "https://www.solarsystemscope.com/textures/download/2k_ganymede.jpg",
    "callisto": "https://www.solarsystemscope.com/textures/download/2k_callisto.jpg",
    "titan": "https://www.solarsystemscope.com/textures/download/2k_saturn.jpg",
    "charon": "https://www.solarsystemscope.com/textures/download/2k_makemake_fictional.jpg",
}


def _spectral_color(spec_b, spec_t):
    for code in (spec_t, spec_b):
        if code and isinstance(code, str) and len(code) > 0:
            first = code[0].upper()
            if first in SPECTRAL_COLORS:
                return SPECTRAL_COLORS[first]
    return DEFAULT_COLOR


def _to_unified(obj, category, status):
    """Convert any legacy object dict into the unified catalog schema."""
    name = obj.get("name") or ""
    designation = obj.get("pdes") or obj.get("designation") or name
    spkid = obj.get("spkid")

    spec_b = obj.get("spec_B")
    spec_t = obj.get("spec_T")
    color = BODY_COLORS.get(name, _spectral_color(spec_b, spec_t))
    texture = PLANET_TEXTURES.get(name.lower())

    neo_flag = obj.get("neo")
    pha_flag = obj.get("pha")
    neo_bool = neo_flag == "Y" or neo_flag is True if neo_flag is not None else None
    pha_bool = pha_flag == "Y" or pha_flag is True if pha_flag is not None else None

    def _flt(v):
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    return {
        "id": str(designation),
        "category": category,
        "status": status,
        "name": name or None,
        "designation": str(designation),
        "full_name": obj.get("full_name") or name,
        "spkid": int(spkid) if spkid is not None else None,
        "parent": obj.get("parent"),
        "discovery_year": obj.get("discovery_year"),
        "orbit": {
            "source": "static",
            "epoch_jd": _flt(obj.get("tp")),
            "a": _flt(obj.get("a")),
            "e": _flt(obj.get("e")),
            "i": _flt(obj.get("i")),
            "om": _flt(obj.get("om")),
            "w": _flt(obj.get("w")),
            "ma": _flt(obj.get("ma")),
            "tp": _flt(obj.get("tp")),
            "per": _flt(obj.get("per")),
            "q": _flt(obj.get("q")),
        },
        "physical": {
            "H": _flt(obj.get("H")),
            "diameter_km": _flt(obj.get("diameter") or obj.get("diameter_km")),
            "albedo": _flt(obj.get("albedo")),
            "rot_per_h": _flt(obj.get("rot_per")),
            "GM": _flt(obj.get("GM")),
            "spec_B": spec_b if spec_b else None,
            "spec_T": spec_t if spec_t else None,
            "BV": _flt(obj.get("BV")),
            "UB": _flt(obj.get("UB")),
            "neo": neo_bool,
            "pha": pha_bool,
            "condition_code": obj.get("condition_code"),
            "rms": _flt(obj.get("rms")),
        },
        "rendering": {
            "color_hex": color,
            "texture_url": texture,
            "model_type": "texture" if texture else None,
            "model_source": "Solar System Scope" if texture else None,
        },
        "media_refs": {
            "wikipedia_title": None,
            "ssodnet_id": None,
        },
        "sources": ["static"],
        "updated": datetime.now(timezone.utc).isoformat(),
    }


def _write_catalog(name, objects):
    data = {
        "catalog": name,
        "version": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "count": len(objects),
        "objects": objects,
    }
    path = os.path.join(CACHE_DIR, f"catalog_{name}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Wrote {path}: {len(objects)} objects")
    return path


# ── Core catalog ────────────────────────────────────────────────────────

def build_core():
    """Build catalog_core.json from planets_moons.json + notable bodies."""
    objects = []

    # Load existing planets_moons.json
    pm_path = os.path.join(CACHE_DIR, "planets_moons.json")
    if os.path.exists(pm_path):
        with open(pm_path, "r") as f:
            pm = json.load(f)
        for p in pm.get("planets", []):
            objects.append(_to_unified(p, "Planet", "permanent"))
        for m in pm.get("moons", []):
            objects.append(_to_unified(m, "Moon", "permanent"))
        print(f"  Loaded {len(pm.get('planets', []))} planets, {len(pm.get('moons', []))} moons from planets_moons.json")
    else:
        print("  WARNING: planets_moons.json not found — run generate_planets_moons.py first")

    # Notable bodies (from solar_scene.py _NOTABLE_BODIES)
    notable = [
        {"name": "Ceres",    "pdes": "1",      "type": "dwarf_planet", "a": 2.7671, "e": 0.0760, "i": 10.587, "om": 80.305,  "w": 73.597,  "ma": 130.09, "tp": 2460870.5, "H": 3.53,  "diameter": 939.4,  "albedo": 0.09, "spec_T": "C"},
        {"name": "Vesta",    "pdes": "4",      "type": "asteroid",     "a": 2.3615, "e": 0.0887, "i": 7.142,  "om": 103.851, "w": 149.855, "ma": 257.38, "tp": 2460150.5, "H": 3.20,  "diameter": 525.4,  "albedo": 0.42, "spec_T": "V"},
        {"name": "Pallas",   "pdes": "2",      "type": "asteroid",     "a": 2.7720, "e": 0.2305, "i": 34.837, "om": 173.089, "w": 310.048, "ma": 68.93,  "tp": 2460550.5, "H": 4.13,  "diameter": 512.0,  "albedo": 0.16, "spec_T": "B"},
        {"name": "Hygiea",   "pdes": "10",     "type": "asteroid",     "a": 3.1392, "e": 0.1146, "i": 3.838,  "om": 283.412, "w": 312.317, "ma": 218.65, "tp": 2460050.5, "H": 5.43,  "diameter": 431.0,  "albedo": 0.07, "spec_T": "C"},
        {"name": "Juno",     "pdes": "3",      "type": "asteroid",     "a": 2.6694, "e": 0.2562, "i": 12.982, "om": 169.870, "w": 247.839, "ma": 33.33,  "tp": 2460750.5, "H": 5.33,  "diameter": 246.6,  "albedo": 0.24, "spec_T": "S"},
        {"name": "Psyche",   "pdes": "16",     "type": "asteroid",     "a": 2.9211, "e": 0.1339, "i": 3.096,  "om": 150.194, "w": 227.156, "ma": 318.22, "tp": 2460280.5, "H": 5.90,  "diameter": 226.0,  "albedo": 0.12, "spec_T": "M"},
        {"name": "Davida",   "pdes": "511",    "type": "asteroid",     "a": 3.1652, "e": 0.1861, "i": 15.938, "om": 107.594, "w": 339.068, "ma": 185.46, "tp": 2459880.5, "H": 6.22,  "diameter": 289.0,  "albedo": 0.05, "spec_T": "C"},
        {"name": "Haumea",   "pdes": "136108", "type": "dwarf_planet", "a": 43.116, "e": 0.1951, "i": 28.213, "om": 121.900, "w": 239.041, "ma": 218.20, "tp": 2449000.0, "H": 0.43,  "diameter": 1560.0, "albedo": 0.51, "spec_T": ""},
        {"name": "Makemake", "pdes": "136472", "type": "dwarf_planet", "a": 45.430, "e": 0.1613, "i": 28.983, "om": 79.382,  "w": 296.534, "ma": 165.51, "tp": 2448900.0, "H": -0.44, "diameter": 1430.0, "albedo": 0.81, "spec_T": ""},
        {"name": "Eris",     "pdes": "136199", "type": "dwarf_planet", "a": 67.781, "e": 0.4407, "i": 44.040, "om": 35.877,  "w": 151.639, "ma": 205.99, "tp": 2545000.0, "H": -1.12, "diameter": 2326.0, "albedo": 0.96, "spec_T": ""},
        {"name": "Sedna",    "pdes": "90377",  "type": "detached",     "a": 506.8,  "e": 0.8496, "i": 11.930, "om": 144.514, "w": 311.122, "ma": 358.12, "tp": 2479000.0, "H": 1.56,  "diameter": 995.0,  "albedo": 0.32, "spec_T": ""},
    ]
    for nb in notable:
        obj = _to_unified(nb, "Notable", "named")
        obj["orbit"]["source"] = "jpl_sbdb"
        obj["sources"] = ["jpl_sbdb"]
        objects.append(obj)
    print(f"  Added {len(notable)} notable bodies")

    _write_catalog("core", objects)
    return objects


# ── NEO catalog ─────────────────────────────────────────────────────────

def build_neo(limit=50000):
    """Build catalog_neo.json from existing neo_mission_data.json or live SBDB."""
    objects = []

    neo_path = os.path.join(CACHE_DIR, "neo_mission_data.json")
    if os.path.exists(neo_path):
        with open(neo_path, "r") as f:
            raw = json.load(f)
        items = list(raw.values()) if isinstance(raw, dict) else raw
        for obj in items[:limit]:
            neo_flag = obj.get("neo")
            pha_flag = obj.get("pha")
            cat = "NEO"
            if pha_flag == "Y":
                cat = "PHA"
            u = _to_unified(obj, cat, "numbered")
            u["orbit"]["source"] = "jpl_sbdb"
            u["sources"] = ["jpl_sbdb"]
            objects.append(u)
        print(f"  Converted {len(objects)} NEOs from neo_mission_data.json")
    else:
        print("  WARNING: neo_mission_data.json not found")
        print("  Attempting live SBDB query...")
        try:
            import requests
            params = {
                "fields": "spkid,full_name,pdes,name,neo,pha,H,diameter,albedo,rot_per,spec_B,spec_T,a,e,i,om,w,ma,tp",
                "sb-kind": "a",
                "sb-class": "ATE,APO,AMO",
                "limit": limit,
            }
            resp = requests.get("https://ssd-api.jpl.nasa.gov/sbdb_query.api",
                                params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            fields = data.get("fields", [])
            for row in data.get("data", []):
                obj = dict(zip(fields, row))
                u = _to_unified(obj, "NEO", "numbered")
                u["orbit"]["source"] = "jpl_sbdb"
                u["sources"] = ["jpl_sbdb"]
                if u["physical"]["pha"]:
                    u["category"] = "PHA"
                objects.append(u)
            print(f"  Fetched {len(objects)} NEOs from SBDB")
        except Exception as exc:
            print(f"  SBDB query failed: {exc}")

    _write_catalog("neo", objects)
    return objects


# ── NEOCP (pre-JPL candidates) ─────────────────────────────────────────

def build_neocp():
    """Build catalog_neocp.json from MPC NEOCP JSON endpoint."""
    objects = []
    try:
        import requests
        url = "https://www.minorplanetcenter.net/Extended_Files/neocp.json"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        items = resp.json()
        for item in items:
            tmpdesig = item.get("Temp_Desig", "")
            obj = {
                "name": None,
                "pdes": tmpdesig,
                "full_name": tmpdesig,
                "spkid": None,
                "H": item.get("H"),
                "neo": "Y",
                "pha": None,
            }
            u = _to_unified(obj, "NEOCP", "candidate")
            u["orbit"]["source"] = "mpc_neocp"
            u["sources"] = ["mpc_neocp"]

            disc_y = item.get("Discovery_year")
            disc_m = item.get("Discovery_month")
            disc_d = item.get("Discovery_day")
            if disc_y:
                u["discovery_year"] = int(disc_y)

            u["neocp"] = {
                "score": item.get("Score"),
                "ra_h": item.get("R.A."),
                "dec_deg": item.get("Decl."),
                "V_mag": item.get("V"),
                "n_obs": item.get("NObs"),
                "arc_days": item.get("Arc"),
                "not_seen_days": item.get("Not_Seen_dys"),
                "discovery_date": f"{disc_y}-{disc_m:02d}-{disc_d}" if disc_y and disc_m else None,
                "updated": item.get("Updated"),
            }
            objects.append(u)
        print(f"  Fetched {len(objects)} NEOCP candidates from MPC")
    except Exception as exc:
        print(f"  MPC NEOCP fetch failed: {exc}")

    _write_catalog("neocp", objects)
    return objects


# ── SBDB category catalogs ──────────────────────────────────────────────

SBDB_CATEGORIES = {
    "mba":     {"sb-kind": "a", "sb-class": "MBA"},
    "imb":     {"sb-kind": "a", "sb-class": "IMB"},
    "omb":     {"sb-kind": "a", "sb-class": "OMB"},
    "tno":     {"sb-kind": "a", "sb-class": "TNO"},
    "centaur": {"sb-kind": "a", "sb-class": "CEN"},
    "trojan":  {"sb-kind": "a", "sb-class": "TJN"},
    "comet":   {"sb-kind": "c"},
}

def build_sbdb_category(cat_name, limit=10000):
    """Build a catalog file for an SBDB category (MBA, TNO, etc.)."""
    if cat_name not in SBDB_CATEGORIES:
        print(f"  Unknown SBDB category: {cat_name}")
        return []
    objects = []
    try:
        import requests
        sbdb_params = SBDB_CATEGORIES[cat_name]
        params = {
            "fields": "spkid,full_name,pdes,name,neo,pha,H,diameter,albedo,rot_per,spec_B,spec_T,a,e,i,om,w,ma,tp",
            "limit": limit,
            **sbdb_params,
        }
        print(f"  Querying SBDB for {cat_name} (limit {limit})...")
        resp = requests.get("https://ssd-api.jpl.nasa.gov/sbdb_query.api",
                            params=params, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        fields = data.get("fields", [])
        ui_cat = cat_name.upper()
        if ui_cat == "CENTAUR":
            ui_cat = "Centaur"
        elif ui_cat == "TROJAN":
            ui_cat = "Trojan"
        elif ui_cat == "COMET":
            ui_cat = "Comet"
        for row in data.get("data", []):
            obj = dict(zip(fields, row))
            u = _to_unified(obj, ui_cat, "numbered")
            u["orbit"]["source"] = "jpl_sbdb"
            u["sources"] = ["jpl_sbdb"]
            objects.append(u)
        print(f"  Fetched {len(objects)} {cat_name} objects from SBDB")
    except Exception as exc:
        print(f"  SBDB {cat_name} query failed: {exc}")

    _write_catalog(cat_name, objects)
    return objects


# ── Main ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate unified solar system catalog files")
    parser.add_argument("target", choices=[
        "core", "neo", "neocp",
        "mba", "imb", "omb", "tno", "centaur", "trojan", "comet",
        "all",
    ])
    parser.add_argument("--limit", type=int, default=50000)
    args = parser.parse_args()

    print(f"=== generate_catalog.py: {args.target} ===")

    if args.target == "core":
        build_core()
    elif args.target == "neo":
        build_neo(args.limit)
    elif args.target == "neocp":
        build_neocp()
    elif args.target in SBDB_CATEGORIES:
        build_sbdb_category(args.target, args.limit)
    elif args.target == "all":
        build_core()
        build_neo(args.limit)
        build_neocp()
        for cat in SBDB_CATEGORIES:
            build_sbdb_category(cat, args.limit)

    print("Done.")


if __name__ == "__main__":
    main()
