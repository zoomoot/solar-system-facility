#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Geocentric positions of Sun, Moon, and major planets at an instant (Skyfield + JPL DE).
Vectors are ICRS equatorial J2000-ish (Skyfield ICRS), in AU, from Earth center.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Lazy-loaded to avoid import cost if Flask route unused
_ts = None
_eph = None


def _ensure_ephemeris():
    global _ts, _eph
    if _eph is None:
        from skyfield.api import load

        _ts = load.timescale()
        # ~16 MB first download; cached under ~/.skyfield
        _eph = load("de421.bsp")
    return _ts, _eph


def get_geocentric_bodies(
    dt_utc: Optional[datetime] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Returns (iso_time_utc, list of body dicts).
    Each dict: name, x_au, y_au, z_au, distance_au (geocentric).
    """
    if dt_utc is None:
        dt_utc = datetime.now(timezone.utc)
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)

    ts, eph = _ensure_ephemeris()
    t = ts.utc(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour,
        dt_utc.minute,
        dt_utc.second + dt_utc.microsecond * 1e-6,
    )

    earth = eph["earth"]
    pairs: List[Tuple[str, Any]] = [
        ("Sun", eph["sun"]),
        ("Mercury", eph["mercury barycenter"]),
        ("Venus", eph["venus barycenter"]),
        ("Moon", eph["moon"]),
        ("Mars", eph["mars barycenter"]),
        ("Jupiter", eph["jupiter barycenter"]),
        ("Saturn", eph["saturn barycenter"]),
        ("Uranus", eph["uranus barycenter"]),
        ("Neptune", eph["neptune barycenter"]),
        ("Pluto", eph["pluto barycenter"]),
    ]

    out: List[Dict[str, Any]] = []
    for name, body in pairs:
        ast = earth.at(t).observe(body)
        pos = ast.position.au
        out.append(
            {
                "name": name,
                "x_au": float(pos[0]),
                "y_au": float(pos[1]),
                "z_au": float(pos[2]),
                "distance_au": float(ast.distance().au),
            }
        )

    iso = dt_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return iso, out


def get_topocentric_bodies(
    lat_deg: float,
    lon_deg: float,
    height_m: float = 0.0,
    dt_utc: Optional[datetime] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Apparent alt/az + distance as seen from WGS84 lat/lon (deg), height_m.
    Azimuth: astropy convention — from geographic North toward East.
    Returns (iso_time_utc, list of dicts with name, alt_deg, az_deg, distance_au).
    """
    import astropy.units as u
    from astropy.coordinates import AltAz, EarthLocation, get_body
    from astropy.time import Time

    if dt_utc is None:
        dt_utc = datetime.now(timezone.utc)
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)

    loc = EarthLocation.from_geodetic(
        lon_deg * u.deg, lat_deg * u.deg, height_m * u.m
    )
    t = Time(dt_utc)

    pairs: List[Tuple[str, str]] = [
        ("Sun", "sun"),
        ("Mercury", "mercury"),
        ("Venus", "venus"),
        ("Moon", "moon"),
        ("Mars", "mars"),
        ("Jupiter", "jupiter"),
        ("Saturn", "saturn"),
        ("Uranus", "uranus"),
        ("Neptune", "neptune"),
    ]

    out: List[Dict[str, Any]] = []
    for label, bid in pairs:
        try:
            coord = get_body(bid, t, loc)
            aa = coord.transform_to(AltAz(obstime=t, location=loc))
            dist_au = float(aa.distance.to(u.au).value)
            out.append(
                {
                    "name": label,
                    "alt_deg": float(aa.alt.to(u.deg).value),
                    "az_deg": float(aa.az.to(u.deg).value),
                    "distance_au": dist_au,
                }
            )
        except Exception as e:
            out.append(
                {
                    "name": label,
                    "error": str(e),
                    "alt_deg": None,
                    "az_deg": None,
                    "distance_au": None,
                }
            )

    iso = dt_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return iso, out
