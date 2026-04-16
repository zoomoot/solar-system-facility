#!/usr/bin/env python3
"""
Solar System scene builder — heliocentric 3D positions for all known objects.

Major bodies: Skyfield + JPL DE421 ephemeris (Sun, Moon, planets).
Small bodies: Kepler equation solver using cached orbital elements.
Includes apparent magnitude computation for visibility cutoff.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

_ts = None
_eph = None
_neo_cache: Optional[List[Dict[str, Any]]] = None
_notable_cache: Optional[List[Dict[str, Any]]] = None

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")

# Absolute magnitudes for major bodies (V-band, approximate)
_MAJOR_BODY_H = {
    "Sun": -26.74,
    "Mercury": -0.42,
    "Venus": -4.47,
    "Moon": -12.74,
    "Mars": -1.52,
    "Jupiter": -9.40,
    "Saturn": -8.88,
    "Uranus": -7.19,
    "Neptune": -6.87,
    "Pluto": -1.0,
}

# Approximate diameters in km
_MAJOR_BODY_DIAMETER = {
    "Sun": 1392700.0,
    "Mercury": 4879.0,
    "Venus": 12104.0,
    "Earth": 12742.0,
    "Moon": 3474.0,
    "Mars": 6779.0,
    "Jupiter": 139822.0,
    "Saturn": 116464.0,
    "Uranus": 50724.0,
    "Neptune": 49244.0,
    "Pluto": 2377.0,
}

# Bond albedo for major bodies
_MAJOR_BODY_ALBEDO = {
    "Sun": None,
    "Mercury": 0.088,
    "Venus": 0.76,
    "Moon": 0.12,
    "Earth": 0.306,
    "Mars": 0.17,
    "Jupiter": 0.52,
    "Saturn": 0.47,
    "Uranus": 0.51,
    "Neptune": 0.41,
    "Pluto": 0.58,
}

# Display colors (hex) for major bodies
_MAJOR_BODY_COLOR = {
    "Sun": "#FFF264",
    "Mercury": "#B3B3A6",
    "Venus": "#F2D98D",
    "Moon": "#D9D9E0",
    "Mars": "#E65A33",
    "Jupiter": "#D9A673",
    "Saturn": "#E6CC8D",
    "Uranus": "#80D9E6",
    "Neptune": "#5973F2",
    "Pluto": "#C4A882",
}

# Spectral type to color mapping for asteroids
_SPECTRAL_COLORS = {
    "S": "#C8886E",   # silicate, reddish
    "C": "#5A5A5A",   # carbonaceous, dark
    "M": "#A0A0B0",   # metallic, grey-silver
    "V": "#8B7D6B",   # basaltic
    "X": "#808080",   # degenerate, grey
    "D": "#704030",   # dark reddish
    "B": "#4A4A5A",   # blue-ish dark
    "A": "#C8A070",   # olivine, amber
    "Q": "#B08060",   # ordinary chondrite
    "R": "#A05040",   # red
    "T": "#604020",   # troilite, dark brown
}

_DEFAULT_COLOR = "#808080"

# Notable asteroids/dwarf planets not in the NEO cache, with J2000 orbital elements.
# Source: JPL SBDB (epoch ~2460400.5 / 2024-Apr-17).
_NOTABLE_BODIES = [
    {"name": "Ceres",   "pdes": "1 Ceres",   "type": "dwarf_planet", "a": 2.7671, "e": 0.0760, "i": 10.587, "om": 80.305,  "w": 73.597,  "ma": 130.09, "tp": 2460870.5, "H": 3.53,  "diameter": 939.4,  "albedo": 0.09, "spec_T": "C"},
    {"name": "Vesta",   "pdes": "4 Vesta",   "type": "asteroid",     "a": 2.3615, "e": 0.0887, "i": 7.142,  "om": 103.851, "w": 149.855, "ma": 257.38, "tp": 2460150.5, "H": 3.20,  "diameter": 525.4,  "albedo": 0.42, "spec_T": "V"},
    {"name": "Pallas",  "pdes": "2 Pallas",  "type": "asteroid",     "a": 2.7720, "e": 0.2305, "i": 34.837, "om": 173.089, "w": 310.048, "ma": 68.93,  "tp": 2460550.5, "H": 4.13,  "diameter": 512.0,  "albedo": 0.16, "spec_T": "B"},
    {"name": "Hygiea",  "pdes": "10 Hygiea", "type": "asteroid",     "a": 3.1392, "e": 0.1146, "i": 3.838,  "om": 283.412, "w": 312.317, "ma": 218.65, "tp": 2460050.5, "H": 5.43,  "diameter": 431.0,  "albedo": 0.07, "spec_T": "C"},
    {"name": "Juno",    "pdes": "3 Juno",    "type": "asteroid",     "a": 2.6694, "e": 0.2562, "i": 12.982, "om": 169.870, "w": 247.839, "ma": 33.33,  "tp": 2460750.5, "H": 5.33,  "diameter": 246.6,  "albedo": 0.24, "spec_T": "S"},
    {"name": "Psyche",  "pdes": "16 Psyche", "type": "asteroid",     "a": 2.9211, "e": 0.1339, "i": 3.096,  "om": 150.194, "w": 227.156, "ma": 318.22, "tp": 2460280.5, "H": 5.90,  "diameter": 226.0,  "albedo": 0.12, "spec_T": "M"},
    {"name": "Davida",  "pdes": "511 Davida","type": "asteroid",     "a": 3.1652, "e": 0.1861, "i": 15.938, "om": 107.594, "w": 339.068, "ma": 185.46, "tp": 2459880.5, "H": 6.22,  "diameter": 289.0,  "albedo": 0.05, "spec_T": "C"},
    {"name": "Haumea",  "pdes": "136108",    "type": "dwarf_planet", "a": 43.116, "e": 0.1951, "i": 28.213, "om": 121.900, "w": 239.041, "ma": 218.20, "tp": 2449000.0, "H": 0.43,  "diameter": 1560.0, "albedo": 0.51, "spec_T": ""},
    {"name": "Makemake","pdes": "136472",    "type": "dwarf_planet", "a": 45.430, "e": 0.1613, "i": 28.983, "om": 79.382,  "w": 296.534, "ma": 165.51, "tp": 2448900.0, "H": -0.44, "diameter": 1430.0, "albedo": 0.81, "spec_T": ""},
    {"name": "Eris",    "pdes": "136199",    "type": "dwarf_planet", "a": 67.781, "e": 0.4407, "i": 44.040, "om": 35.877,  "w": 151.639, "ma": 205.99, "tp": 2545000.0, "H": -1.12, "diameter": 2326.0, "albedo": 0.96, "spec_T": ""},
    {"name": "Sedna",   "pdes": "90377",     "type": "detached",     "a": 506.8,  "e": 0.8496, "i": 11.930, "om": 144.514, "w": 311.122, "ma": 358.12, "tp": 2479000.0, "H": 1.56,  "diameter": 995.0,  "albedo": 0.32, "spec_T": ""},
]


def _ensure_ephemeris():
    global _ts, _eph
    if _eph is None:
        from skyfield.api import load
        _ts = load.timescale()
        _eph = load("de421.bsp")
    return _ts, _eph


def _catalog_to_flat(uobj: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a unified-catalog object to the flat dict format used for orbit computation."""
    orb = uobj.get("orbit", {})
    phys = uobj.get("physical", {})
    return {
        "name": uobj.get("name") or uobj.get("designation", ""),
        "pdes": uobj.get("designation", ""),
        "full_name": uobj.get("full_name", ""),
        "type": uobj.get("category", "asteroid"),
        "a": orb.get("a"),
        "e": orb.get("e"),
        "i": orb.get("i"),
        "om": orb.get("om"),
        "w": orb.get("w"),
        "ma": orb.get("ma"),
        "tp": orb.get("tp"),
        "H": phys.get("H"),
        "diameter": phys.get("diameter_km"),
        "albedo": phys.get("albedo"),
        "spec_T": phys.get("spec_T"),
        "spec_B": phys.get("spec_B"),
        "neo": "Y" if phys.get("neo") else "N",
        "pha": "Y" if phys.get("pha") else "N",
    }


def _load_catalog_objects(catalog_name: str, category: str = None) -> List[Dict[str, Any]]:
    """Load objects from a unified catalog file, optionally filtering by category.
    Returns flat-format dicts ready for orbit computation."""
    path = os.path.join(CACHE_DIR, f"catalog_{catalog_name}.json")
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        data = json.load(f)
    objects = data.get("objects", [])
    result = []
    for uobj in objects:
        if category and uobj.get("category") != category:
            continue
        result.append(_catalog_to_flat(uobj))
    return result


def _load_notable_bodies() -> List[Dict[str, Any]]:
    """Load notable bodies, preferring unified catalog, falling back to hardcoded."""
    global _notable_cache
    if _notable_cache is not None:
        return _notable_cache
    catalog_notable = _load_catalog_objects("core", "Notable")
    if catalog_notable:
        _notable_cache = catalog_notable
    else:
        _notable_cache = list(_NOTABLE_BODIES)
    return _notable_cache


def _load_neo_cache() -> List[Dict[str, Any]]:
    """Load NEO data, preferring unified catalog, falling back to legacy cache."""
    global _neo_cache
    if _neo_cache is not None:
        return _neo_cache

    catalog_neo = _load_catalog_objects("neo")
    if catalog_neo:
        _neo_cache = catalog_neo
        return _neo_cache

    cache_path = os.path.join(CACHE_DIR, "neo_mission_data.json")
    if not os.path.exists(cache_path):
        _neo_cache = []
        return _neo_cache

    with open(cache_path, "r") as f:
        raw = json.load(f)

    _neo_cache = list(raw.values())
    return _neo_cache


def _solve_kepler(M: float, e: float, tol: float = 1e-10, max_iter: int = 50) -> float:
    """Solve Kepler's equation M = E - e*sin(E) for eccentric anomaly E."""
    E = M if e < 0.8 else math.pi
    for _ in range(max_iter):
        dE = (E - e * math.sin(E) - M) / (1.0 - e * math.cos(E))
        E -= dE
        if abs(dE) < tol:
            break
    return E


def _kepler_to_cartesian(
    a: float, e: float, i_deg: float, om_deg: float, w_deg: float,
    ma_deg: float, tp_jd: float, epoch_jd: float
) -> Optional[Tuple[float, float, float]]:
    """
    Compute heliocentric ecliptic cartesian position (AU) from Keplerian elements.
    
    tp_jd: time of perihelion passage (Julian date)
    epoch_jd: the epoch at which to compute the position
    """
    if a <= 0 or e >= 1.0:
        return None

    n = 2.0 * math.pi / (a ** 1.5 * 365.25)  # mean motion (rad/day)
    dt_days = epoch_jd - tp_jd
    M = (ma_deg * math.pi / 180.0) + n * dt_days
    M = M % (2.0 * math.pi)

    E = _solve_kepler(M, e)

    nu = 2.0 * math.atan2(
        math.sqrt(1.0 + e) * math.sin(E / 2.0),
        math.sqrt(1.0 - e) * math.cos(E / 2.0),
    )

    r = a * (1.0 - e * math.cos(E))

    x_orb = r * math.cos(nu)
    y_orb = r * math.sin(nu)

    i_r = math.radians(i_deg)
    om_r = math.radians(om_deg)
    w_r = math.radians(w_deg)

    cos_om = math.cos(om_r)
    sin_om = math.sin(om_r)
    cos_i = math.cos(i_r)
    sin_i = math.sin(i_r)
    cos_w = math.cos(w_r)
    sin_w = math.sin(w_r)

    x = x_orb * (cos_om * cos_w - sin_om * sin_w * cos_i) - y_orb * (cos_om * sin_w + sin_om * cos_w * cos_i)
    y = x_orb * (sin_om * cos_w + cos_om * sin_w * cos_i) - y_orb * (sin_om * sin_w - cos_om * cos_w * cos_i)
    z = x_orb * (sin_w * sin_i) + y_orb * (cos_w * sin_i)

    return (x, y, z)


def _apparent_magnitude(H: float, r_sun_au: float, r_obs_au: float, phase_angle_rad: float = 0.0) -> float:
    """
    Simplified apparent magnitude for an asteroid.
    H + 5*log10(r*delta) with a simple phase correction.
    r_sun_au: heliocentric distance, r_obs_au: distance from observer.
    """
    if r_sun_au <= 0 or r_obs_au <= 0:
        return 99.0
    phi = 1.0 - 0.5 * abs(phase_angle_rad) / math.pi  # simple linear phase
    phi = max(phi, 0.1)
    return H + 5.0 * math.log10(r_sun_au * r_obs_au) - 2.5 * math.log10(phi)


def _spectral_to_color(spec_b: Optional[str], spec_t: Optional[str]) -> str:
    """Map SBDB spectral type codes to a hex color."""
    for code in (spec_t, spec_b):
        if code and isinstance(code, str) and len(code) > 0:
            first = code[0].upper()
            if first in _SPECTRAL_COLORS:
                return _SPECTRAL_COLORS[first]
    return _DEFAULT_COLOR


def _datetime_to_jd(dt: datetime) -> float:
    """Convert a UTC datetime to Julian Date."""
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    jdn = dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    jd = jdn + (dt.hour - 12) / 24.0 + dt.minute / 1440.0 + dt.second / 86400.0
    return jd


_OBLIQUITY_RAD = math.radians(23.4392911)
_COS_OBL = math.cos(_OBLIQUITY_RAD)
_SIN_OBL = math.sin(_OBLIQUITY_RAD)


def _icrs_to_ecliptic(x_eq: float, y_eq: float, z_eq: float):
    """Rotate ICRS equatorial coordinates to ecliptic (J2000 obliquity)."""
    x_ecl = x_eq
    y_ecl = y_eq * _COS_OBL + z_eq * _SIN_OBL
    z_ecl = -y_eq * _SIN_OBL + z_eq * _COS_OBL
    return x_ecl, y_ecl, z_ecl


def get_heliocentric_major_bodies(dt_utc: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Get heliocentric ecliptic positions of major solar system bodies via Skyfield."""
    if dt_utc is None:
        dt_utc = datetime.now(timezone.utc)
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)

    ts, eph = _ensure_ephemeris()
    t = ts.utc(dt_utc.year, dt_utc.month, dt_utc.day,
               dt_utc.hour, dt_utc.minute,
               dt_utc.second + dt_utc.microsecond * 1e-6)

    sun = eph["sun"]
    earth = eph["earth"]

    bodies_to_query = [
        ("Sun", eph["sun"]),
        ("Mercury", eph["mercury barycenter"]),
        ("Venus", eph["venus barycenter"]),
        ("Earth", earth),
        ("Moon", eph["moon"]),
        ("Mars", eph["mars barycenter"]),
        ("Jupiter", eph["jupiter barycenter"]),
        ("Saturn", eph["saturn barycenter"]),
        ("Uranus", eph["uranus barycenter"]),
        ("Neptune", eph["neptune barycenter"]),
        ("Pluto", eph["pluto barycenter"]),
    ]

    out = []

    for name, body in bodies_to_query:
        if name == "Sun":
            out.append({
                "name": "Sun",
                "designation": "sun",
                "type": "star",
                "x_au": 0.0, "y_au": 0.0, "z_au": 0.0,
                "distance_au": 0.0,
                "diameter_km": _MAJOR_BODY_DIAMETER["Sun"],
                "H": _MAJOR_BODY_H["Sun"],
                "albedo": _MAJOR_BODY_ALBEDO.get("Sun"),
                "color_hex": _MAJOR_BODY_COLOR["Sun"],
                "apparent_mag": None,
            })
            continue

        pos_eq = sun.at(t).observe(body).position.au
        x, y, z = _icrs_to_ecliptic(float(pos_eq[0]), float(pos_eq[1]), float(pos_eq[2]))
        dist = math.sqrt(x * x + y * y + z * z)

        out.append({
            "name": name,
            "designation": name.lower(),
            "type": "planet" if name not in ("Moon", "Pluto") else ("moon" if name == "Moon" else "dwarf_planet"),
            "x_au": x,
            "y_au": y,
            "z_au": z,
            "distance_au": dist,
            "diameter_km": _MAJOR_BODY_DIAMETER.get(name),
            "H": _MAJOR_BODY_H.get(name),
            "albedo": _MAJOR_BODY_ALBEDO.get(name),
            "color_hex": _MAJOR_BODY_COLOR.get(name, _DEFAULT_COLOR),
            "apparent_mag": None,
        })

    return out


def get_small_body_positions(dt_utc: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Compute heliocentric positions for cached NEO/small body data."""
    if dt_utc is None:
        dt_utc = datetime.now(timezone.utc)

    epoch_jd = _datetime_to_jd(dt_utc)
    neo_data = _load_neo_cache()
    out = []

    for obj in neo_data:
        try:
            a = float(obj.get("a", 0))
            e_val = float(obj.get("e", 0))
            i_val = float(obj.get("i", 0))
            om_val = float(obj.get("om", 0))
            w_val = float(obj.get("w", 0))
            ma_val = float(obj.get("ma", 0))
            tp_val = float(obj.get("tp", 0))
        except (TypeError, ValueError):
            continue

        if a <= 0 or e_val >= 1.0:
            continue

        pos = _kepler_to_cartesian(a, e_val, i_val, om_val, w_val, ma_val, tp_val, epoch_jd)
        if pos is None:
            continue

        x, y, z = pos
        dist_sun = math.sqrt(x * x + y * y + z * z)

        name = obj.get("name") or obj.get("pdes") or str(obj.get("spkid", "?"))
        pdes = obj.get("pdes", "")
        H_val = None
        try:
            H_val = float(obj["H"]) if obj.get("H") else None
        except (TypeError, ValueError):
            pass

        diameter = None
        try:
            diameter = float(obj["diameter"]) if obj.get("diameter") else None
        except (TypeError, ValueError):
            pass

        albedo = None
        try:
            albedo = float(obj["albedo"]) if obj.get("albedo") else None
        except (TypeError, ValueError):
            pass

        obj_type = "NEO" if obj.get("neo") == "Y" else "asteroid"
        if obj.get("pha") == "Y":
            obj_type = "PHA"

        color = _spectral_to_color(obj.get("spec_B"), obj.get("spec_T"))

        out.append({
            "name": name,
            "designation": pdes,
            "type": obj_type,
            "x_au": x,
            "y_au": y,
            "z_au": z,
            "distance_au": dist_sun,
            "diameter_km": diameter,
            "H": H_val,
            "albedo": albedo,
            "color_hex": color,
            "apparent_mag": None,
        })

    return out


def get_notable_body_positions(dt_utc: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Compute heliocentric positions for notable asteroids/dwarf planets."""
    if dt_utc is None:
        dt_utc = datetime.now(timezone.utc)

    epoch_jd = _datetime_to_jd(dt_utc)
    out = []

    for obj in _load_notable_bodies():
        pos = _kepler_to_cartesian(
            obj["a"], obj["e"], obj["i"], obj["om"], obj["w"],
            obj["ma"], obj["tp"], epoch_jd
        )
        if pos is None:
            continue

        x, y, z = pos
        dist_sun = math.sqrt(x * x + y * y + z * z)
        color = _spectral_to_color(None, obj.get("spec_T"))

        out.append({
            "name": obj["name"],
            "designation": obj["pdes"],
            "type": obj.get("type", "asteroid"),
            "x_au": x,
            "y_au": y,
            "z_au": z,
            "distance_au": dist_sun,
            "diameter_km": obj.get("diameter"),
            "H": obj.get("H"),
            "albedo": obj.get("albedo"),
            "color_hex": color,
            "apparent_mag": None,
        })

    return out


def build_scene(
    observer: str = "earth",
    dt_utc: Optional[datetime] = None,
    mag_limit: float = 20.0,
) -> Dict[str, Any]:
    """
    Build a complete solar system scene from a given observer.
    
    observer: "earth", "sun", planet name, or a designation from the NEO cache.
    Returns: {success, time_utc, observer_name, observer_pos, bodies}
    """
    if dt_utc is None:
        dt_utc = datetime.now(timezone.utc)
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)

    major = get_heliocentric_major_bodies(dt_utc)
    notable = get_notable_body_positions(dt_utc)
    small = get_small_body_positions(dt_utc)
    all_bodies = major + notable + small

    observer_pos = {"x_au": 0.0, "y_au": 0.0, "z_au": 0.0}
    observer_name = observer

    obs_lower = observer.lower().strip()
    for b in all_bodies:
        match_name = (b["name"].lower() == obs_lower)
        match_des = (b.get("designation", "").lower() == obs_lower)
        if match_name or match_des:
            observer_pos = {"x_au": b["x_au"], "y_au": b["y_au"], "z_au": b["z_au"]}
            observer_name = b["name"]
            break

    ox = observer_pos["x_au"]
    oy = observer_pos["y_au"]
    oz = observer_pos["z_au"]

    result_bodies = []
    for b in all_bodies:
        dx = b["x_au"] - ox
        dy = b["y_au"] - oy
        dz = b["z_au"] - oz
        dist_to_obs = math.sqrt(dx * dx + dy * dy + dz * dz)

        is_observer = b["name"].lower() == observer_name.lower()
        if is_observer:
            dist_to_obs = 0.0

        dist_sun = math.sqrt(b["x_au"] ** 2 + b["y_au"] ** 2 + b["z_au"] ** 2)

        app_mag = None
        if not is_observer:
            H_val = b.get("H")
            if H_val is not None and b["type"] not in ("star",):
                if b["type"] in ("planet", "moon", "dwarf_planet"):
                    app_mag = H_val + 5.0 * math.log10(max(dist_to_obs, 0.001))
                else:
                    app_mag = _apparent_magnitude(H_val, max(dist_sun, 0.001), dist_to_obs)

                if app_mag > mag_limit:
                    continue

        entry = dict(b)
        entry["rel_x_au"] = 0.0 if is_observer else dx
        entry["rel_y_au"] = 0.0 if is_observer else dy
        entry["rel_z_au"] = 0.0 if is_observer else dz
        entry["distance_to_observer_au"] = 0.0 if is_observer else round(dist_to_obs, 6)
        entry["apparent_mag"] = round(app_mag, 2) if app_mag is not None else None
        result_bodies.append(entry)

    result_bodies.sort(key=lambda b: b.get("apparent_mag") or 99.0)

    iso = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "success": True,
        "time_utc": iso,
        "observer_name": observer_name,
        "observer_pos": observer_pos,
        "body_count": len(result_bodies),
        "bodies": result_bodies,
    }


def _load_sbdb_query_objects() -> List[Dict[str, Any]]:
    """Load all objects from SBDB query cache entries, deduplicated by designation."""
    cache_path = os.path.join(CACHE_DIR, "jpl_sbdb_cache.json")
    if not os.path.exists(cache_path):
        return []

    with open(cache_path, "r") as f:
        cache = json.load(f)

    seen = set()
    objects = []

    for key, entry in cache.items():
        if not key.startswith("query_"):
            continue
        data = entry.get("data", {})
        if not isinstance(data, dict):
            continue
        fields = data.get("fields", [])
        rows = data.get("data", [])
        if not fields or not rows:
            continue

        for row in rows:
            obj = dict(zip(fields, row))
            pdes = obj.get("pdes", "")
            if not pdes or pdes in seen:
                continue
            seen.add(pdes)
            objects.append(obj)

    return objects


def _load_neo_orbit_lookup() -> Dict[str, Dict[str, Any]]:
    """Build a designation -> orbital elements lookup from neo_mission_data.json."""
    neo_data = _load_neo_cache()
    lookup = {}
    for obj in neo_data:
        pdes = obj.get("pdes", "")
        if pdes:
            lookup[pdes] = obj
        name = obj.get("name", "")
        if name:
            lookup[name.lower()] = obj
    return lookup


def build_researched_scene(
    dt_utc: Optional[datetime] = None,
    mag_limit: float = 25.0,
    selection: Optional[List[Dict[str, Any]]] = None,
    include_extras: bool = True,
) -> Dict[str, Any]:
    """
    Build a scene from the current Streamlit selection.

    If *selection* is provided (list of object dicts from the /api/objects/search
    endpoint), use those directly.  Otherwise fall back to reading the SBDB
    query cache on disk (legacy behaviour).

    If *include_extras* is False, only Sun + Earth + the selection are shown
    (no notable bodies like Ceres/Vesta beyond what was explicitly selected).
    """
    if dt_utc is None:
        dt_utc = datetime.now(timezone.utc)
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)

    epoch_jd = _datetime_to_jd(dt_utc)

    major = get_heliocentric_major_bodies(dt_utc)
    notable = get_notable_body_positions(dt_utc) if include_extras else []

    # Build lookup of Skyfield-computed major body positions by name
    major_by_name: Dict[str, Dict[str, Any]] = {b["name"].lower(): b for b in major}

    query_objects = selection if selection is not None else _load_sbdb_query_objects()
    neo_lookup = _load_neo_orbit_lookup()

    if not include_extras:
        # Spacecraft mode: only Sun + Earth + explicitly selected objects
        selected_names = set()
        for obj in (query_objects or []):
            raw_name = obj.get("name")
            n = str(raw_name).strip() if raw_name and str(raw_name).strip() not in ("", "None") else str(obj.get("pdes", "")).strip()
            if n:
                selected_names.add(n.lower())

        # Keep only Sun and Earth from major (Earth needed for relative coords)
        base_bodies = [b for b in major if b["name"] in ("Sun", "Earth")]

        resolved: List[Dict[str, Any]] = []
        for obj in (query_objects or []):
            pdes = str(obj.get("pdes", "")).strip()
            raw_name = obj.get("name")
            name = str(raw_name).strip() if raw_name and str(raw_name).strip() not in ("", "None") else pdes
            if not name:
                continue
            # Skip Earth/Sun (already in base)
            if name.lower() in ("sun", "earth"):
                continue

            parent = obj.get("parent")  # e.g. "Jupiter" for Io

            # If this object IS a major body, use its Skyfield position
            if name.lower() in major_by_name:
                entry = dict(major_by_name[name.lower()])
                # Preserve selection fields that Skyfield doesn't provide
                for k in ("spec_B", "spec_T", "rot_per", "neo", "pha"):
                    if obj.get(k) is not None:
                        entry[k] = obj[k]
                resolved.append(entry)
                continue

            # If this is a moon with a known parent, offset from parent position
            if parent and parent.lower() in major_by_name:
                parent_pos = major_by_name[parent.lower()]
                px, py, pz = parent_pos["x_au"], parent_pos["y_au"], parent_pos["z_au"]
                a_val = _safe_float(obj.get("a"))
                # Place moon at parent position + semi-major axis offset
                # (simplified; proper moon orbital computation would need full elements)
                if a_val and a_val > 0:
                    x = px + a_val
                    y = py
                    z = pz
                else:
                    x, y, z = px, py, pz
                dist_sun = math.sqrt(x * x + y * y + z * z)
                resolved.append({
                    "name": name.strip(),
                    "designation": pdes,
                    "type": "moon",
                    "x_au": x, "y_au": y, "z_au": z,
                    "distance_au": dist_sun,
                    "diameter_km": _safe_float(obj.get("diameter")),
                    "H": _safe_float(obj.get("H")),
                    "albedo": _safe_float(obj.get("albedo")),
                    "color_hex": _spectral_to_color(obj.get("spec_B"), obj.get("spec_T")),
                    "apparent_mag": None,
                    "spec_B": obj.get("spec_B"),
                    "spec_T": obj.get("spec_T"),
                    "rot_per": _safe_float(obj.get("rot_per")),
                    "neo": obj.get("neo"),
                    "pha": obj.get("pha"),
                })
                continue

            # Standard small body: heliocentric Keplerian computation
            a_val = _safe_float(obj.get("a"))
            e_val = _safe_float(obj.get("e"))
            i_val = _safe_float(obj.get("i"))
            om_val = _safe_float(obj.get("om"))
            w_val = _safe_float(obj.get("w"))
            ma_val = _safe_float(obj.get("ma"))
            tp_val = _safe_float(obj.get("tp"))

            if a_val is None or e_val is None:
                fallback = neo_lookup.get(pdes) or neo_lookup.get(name.lower())
                if fallback:
                    a_val = a_val or _safe_float(fallback.get("a"))
                    e_val = e_val or _safe_float(fallback.get("e"))
                    i_val = i_val or _safe_float(fallback.get("i"))
                    om_val = om_val or _safe_float(fallback.get("om"))
                    w_val = w_val or _safe_float(fallback.get("w"))
                    ma_val = ma_val or _safe_float(fallback.get("ma"))
                    tp_val = tp_val or _safe_float(fallback.get("tp"))

            if a_val is None or e_val is None or a_val <= 0 or e_val >= 1.0:
                continue

            pos = _kepler_to_cartesian(
                a_val, e_val, i_val or 0, om_val or 0, w_val or 0,
                ma_val or 0, tp_val or epoch_jd, epoch_jd
            )
            if pos is None:
                continue

            x, y, z = pos
            dist_sun = math.sqrt(x * x + y * y + z * z)

            H_val = _safe_float(obj.get("H"))
            diameter = _safe_float(obj.get("diameter"))
            albedo = _safe_float(obj.get("albedo"))
            color = _spectral_to_color(obj.get("spec_B"), obj.get("spec_T"))

            obj_type = "NEO" if obj.get("neo") == "Y" else "asteroid"
            if obj.get("pha") == "Y":
                obj_type = "PHA"

            resolved.append({
                "name": name.strip(),
                "designation": pdes,
                "type": obj_type,
                "x_au": x, "y_au": y, "z_au": z,
                "distance_au": dist_sun,
                "diameter_km": diameter,
                "H": H_val,
                "albedo": albedo,
                "color_hex": color,
                "apparent_mag": None,
                "spec_B": obj.get("spec_B"),
                "spec_T": obj.get("spec_T"),
                "rot_per": _safe_float(obj.get("rot_per")),
                "neo": obj.get("neo"),
                "pha": obj.get("pha"),
            })

        all_bodies = base_bodies + resolved

    else:
        # Original behaviour: all major bodies + notables + selection via Keplerian
        major_names = {b["name"].lower() for b in major}
        notable_names = {b["name"].lower() for b in notable}

        small_bodies: List[Dict[str, Any]] = []
        for obj in query_objects:
            pdes = str(obj.get("pdes", "")).strip()
            raw_name = obj.get("name")
            name = str(raw_name).strip() if raw_name and str(raw_name).strip() not in ("", "None") else pdes
            if not name or name.lower() in major_names or name.lower() in notable_names:
                continue

            a_val = _safe_float(obj.get("a"))
            e_val = _safe_float(obj.get("e"))
            i_val = _safe_float(obj.get("i"))
            om_val = _safe_float(obj.get("om"))
            w_val = _safe_float(obj.get("w"))
            ma_val = _safe_float(obj.get("ma"))
            tp_val = _safe_float(obj.get("tp"))

            if a_val is None or e_val is None:
                fallback = neo_lookup.get(pdes) or neo_lookup.get(name.lower())
                if fallback:
                    a_val = a_val or _safe_float(fallback.get("a"))
                    e_val = e_val or _safe_float(fallback.get("e"))
                    i_val = i_val or _safe_float(fallback.get("i"))
                    om_val = om_val or _safe_float(fallback.get("om"))
                    w_val = w_val or _safe_float(fallback.get("w"))
                    ma_val = ma_val or _safe_float(fallback.get("ma"))
                    tp_val = tp_val or _safe_float(fallback.get("tp"))

            if a_val is None or e_val is None or a_val <= 0 or e_val >= 1.0:
                continue

            pos = _kepler_to_cartesian(
                a_val, e_val, i_val or 0, om_val or 0, w_val or 0,
                ma_val or 0, tp_val or epoch_jd, epoch_jd
            )
            if pos is None:
                continue

            x, y, z = pos
            dist_sun = math.sqrt(x * x + y * y + z * z)

            H_val = _safe_float(obj.get("H"))
            diameter = _safe_float(obj.get("diameter"))
            albedo = _safe_float(obj.get("albedo"))
            color = _spectral_to_color(obj.get("spec_B"), obj.get("spec_T"))

            obj_type = "NEO" if obj.get("neo") == "Y" else "asteroid"
            if obj.get("pha") == "Y":
                obj_type = "PHA"

            small_bodies.append({
                "name": name.strip(),
                "designation": pdes,
                "type": obj_type,
                "x_au": x, "y_au": y, "z_au": z,
                "distance_au": dist_sun,
                "diameter_km": diameter,
                "H": H_val,
                "albedo": albedo,
                "color_hex": color,
                "apparent_mag": None,
                "spec_B": obj.get("spec_B"),
                "spec_T": obj.get("spec_T"),
                "rot_per": _safe_float(obj.get("rot_per")),
                "neo": obj.get("neo"),
                "pha": obj.get("pha"),
            })

        all_bodies = major + notable + small_bodies

    # Compute relative positions from Earth
    earth_pos = {"x_au": 0.0, "y_au": 0.0, "z_au": 0.0}
    for b in major:
        if b["name"] == "Earth":
            earth_pos = {"x_au": b["x_au"], "y_au": b["y_au"], "z_au": b["z_au"]}
            break

    ox, oy, oz = earth_pos["x_au"], earth_pos["y_au"], earth_pos["z_au"]

    result_bodies = []
    for b in all_bodies:
        is_earth = (b["name"] == "Earth")

        dx = b["x_au"] - ox
        dy = b["y_au"] - oy
        dz = b["z_au"] - oz
        dist_to_obs = math.sqrt(dx * dx + dy * dy + dz * dz)
        if is_earth:
            dist_to_obs = 0.0

        dist_sun = math.sqrt(b["x_au"] ** 2 + b["y_au"] ** 2 + b["z_au"] ** 2)

        app_mag = None
        if not is_earth:
            H_val = b.get("H")
            if H_val is not None and b["type"] not in ("star",):
                if b["type"] in ("planet", "moon", "dwarf_planet"):
                    app_mag = H_val + 5.0 * math.log10(max(dist_to_obs, 0.001))
                else:
                    app_mag = _apparent_magnitude(H_val, max(dist_sun, 0.001), dist_to_obs)
                if app_mag > mag_limit:
                    continue

        entry = dict(b)
        entry["rel_x_au"] = 0.0 if is_earth else dx
        entry["rel_y_au"] = 0.0 if is_earth else dy
        entry["rel_z_au"] = 0.0 if is_earth else dz
        entry["distance_to_observer_au"] = 0.0 if is_earth else round(dist_to_obs, 6)
        entry["apparent_mag"] = round(app_mag, 2) if app_mag is not None else None
        result_bodies.append(entry)

    result_bodies.sort(key=lambda b: b.get("apparent_mag") or 99.0)

    iso = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "success": True,
        "time_utc": iso,
        "observer_name": "Earth",
        "observer_pos": earth_pos,
        "body_count": len(result_bodies),
        "bodies": result_bodies,
    }


def _safe_float(val) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def search_objects(query: str, limit: int = 20) -> List[Dict[str, str]]:
    """Search major bodies, notable bodies, and NEO cache by name/designation."""
    query_lower = query.lower().strip()
    results = []

    for name in _MAJOR_BODY_DIAMETER:
        if query_lower in name.lower():
            results.append({"name": name, "designation": name.lower(), "type": "major_body"})

    for obj in _load_notable_bodies():
        if (query_lower in obj["name"].lower()
                or query_lower in obj["pdes"].lower()):
            results.append({
                "name": obj["name"],
                "designation": obj["pdes"],
                "type": obj.get("type", "asteroid"),
            })

    neo_data = _load_neo_cache()
    for obj in neo_data:
        name = obj.get("name", "")
        pdes = obj.get("pdes", "")
        full_name = obj.get("full_name", "")
        if (query_lower in (name or "").lower()
                or query_lower in (pdes or "").lower()
                or query_lower in (full_name or "").lower()):
            results.append({
                "name": name or pdes,
                "designation": pdes,
                "type": "NEO" if obj.get("neo") == "Y" else "asteroid",
            })

    return results[:limit]
