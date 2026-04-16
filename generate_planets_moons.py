#!/usr/bin/env python3
"""Generate planets_moons.json — SBDB-compatible dataset for planets and all IAU-named moons.

Run: python generate_planets_moons.py
Output: cache/planets_moons.json

Data sourced from JPL Solar System Dynamics, IAU Minor Planet Center,
and NASA Planetary Fact Sheets. Physical parameters: diameter (km),
albedo (geometric), rotation period (hours), GM (km³/s²), orbital
elements (heliocentric AU for planets, planet-centric km for moons).
"""

import json
import os

# ── Planets ─────────────────────────────────────────────────────────────

PLANETS = [
    {
        "spkid": "199", "full_name": "Mercury", "pdes": "Mercury", "name": "Mercury",
        "prefix": None, "neo": "N", "pha": "N",
        "H": -0.42, "diameter": 4879.4, "albedo": 0.142,
        "rot_per": 1407.6, "GM": 22031.868, "BV": 0.93, "UB": 0.41,
        "spec_B": None, "spec_T": None,
        "a": 0.38710, "e": 0.20563, "i": 7.005, "om": 48.331, "w": 29.124,
        "ma": None, "tp": None,
        "type": "planet", "parent": None,
        "condition_code": None, "rms": None,
    },
    {
        "spkid": "299", "full_name": "Venus", "pdes": "Venus", "name": "Venus",
        "prefix": None, "neo": "N", "pha": "N",
        "H": -4.47, "diameter": 12103.6, "albedo": 0.689,
        "rot_per": -5832.6, "GM": 324858.592, "BV": 0.81, "UB": 0.50,
        "spec_B": None, "spec_T": None,
        "a": 0.72333, "e": 0.00677, "i": 3.395, "om": 76.681, "w": 54.884,
        "ma": None, "tp": None,
        "type": "planet", "parent": None,
        "condition_code": None, "rms": None,
    },
    {
        "spkid": "399", "full_name": "Earth", "pdes": "Earth", "name": "Earth",
        "prefix": None, "neo": "N", "pha": "N",
        "H": -3.99, "diameter": 12756.3, "albedo": 0.367,
        "rot_per": 23.9345, "GM": 398600.435, "BV": None, "UB": None,
        "spec_B": None, "spec_T": None,
        "a": 1.00000, "e": 0.01671, "i": 0.000, "om": -11.261, "w": 114.208,
        "ma": None, "tp": None,
        "type": "planet", "parent": None,
        "condition_code": None, "rms": None,
    },
    {
        "spkid": "499", "full_name": "Mars", "pdes": "Mars", "name": "Mars",
        "prefix": None, "neo": "N", "pha": "N",
        "H": -1.60, "diameter": 6792.4, "albedo": 0.170,
        "rot_per": 24.6229, "GM": 42828.375, "BV": 1.36, "UB": 0.58,
        "spec_B": None, "spec_T": None,
        "a": 1.52368, "e": 0.09341, "i": 1.850, "om": 49.558, "w": 286.502,
        "ma": None, "tp": None,
        "type": "planet", "parent": None,
        "condition_code": None, "rms": None,
    },
    {
        "spkid": "599", "full_name": "Jupiter", "pdes": "Jupiter", "name": "Jupiter",
        "prefix": None, "neo": "N", "pha": "N",
        "H": -9.40, "diameter": 142984.0, "albedo": 0.538,
        "rot_per": 9.9250, "GM": 126686534.0, "BV": 0.83, "UB": 0.48,
        "spec_B": None, "spec_T": None,
        "a": 5.20260, "e": 0.04839, "i": 1.303, "om": 100.464, "w": 273.867,
        "ma": None, "tp": None,
        "type": "planet", "parent": None,
        "condition_code": None, "rms": None,
    },
    {
        "spkid": "699", "full_name": "Saturn", "pdes": "Saturn", "name": "Saturn",
        "prefix": None, "neo": "N", "pha": "N",
        "H": -8.88, "diameter": 120536.0, "albedo": 0.499,
        "rot_per": 10.656, "GM": 37931206.2, "BV": 1.04, "UB": 0.58,
        "spec_B": None, "spec_T": None,
        "a": 9.55491, "e": 0.05415, "i": 2.489, "om": 113.666, "w": 339.392,
        "ma": None, "tp": None,
        "type": "planet", "parent": None,
        "condition_code": None, "rms": None,
    },
    {
        "spkid": "799", "full_name": "Uranus", "pdes": "Uranus", "name": "Uranus",
        "prefix": None, "neo": "N", "pha": "N",
        "H": -7.19, "diameter": 51118.0, "albedo": 0.488,
        "rot_per": -17.24, "GM": 5793951.3, "BV": 0.56, "UB": 0.28,
        "spec_B": None, "spec_T": None,
        "a": 19.21845, "e": 0.04717, "i": 0.773, "om": 74.006, "w": 96.999,
        "ma": None, "tp": None,
        "type": "planet", "parent": None,
        "condition_code": None, "rms": None,
    },
    {
        "spkid": "899", "full_name": "Neptune", "pdes": "Neptune", "name": "Neptune",
        "prefix": None, "neo": "N", "pha": "N",
        "H": -6.87, "diameter": 49528.0, "albedo": 0.442,
        "rot_per": 16.11, "GM": 6835099.5, "BV": 0.41, "UB": 0.21,
        "spec_B": None, "spec_T": None,
        "a": 30.11039, "e": 0.00859, "i": 1.770, "om": 131.784, "w": 276.336,
        "ma": None, "tp": None,
        "type": "planet", "parent": None,
        "condition_code": None, "rms": None,
    },
]

# ── Moons ───────────────────────────────────────────────────────────────
# Organised by parent planet. Fields match SBDB where applicable.
# a_km = semi-major axis around parent (km); a = converted to AU.
# diameter in km, albedo = geometric, rot_per in hours.
# Data from JPL SSD Satellite Physical Parameters + NASA Fact Sheets.

AU_KM = 149597870.7  # 1 AU in km


def _moon(spkid, name, parent, diameter=None, albedo=None, rot_per=None,
          GM=None, a_km=None, e=None, i=None, H=None, discovery_year=None):
    """Helper to build a moon dict in SBDB-compatible format."""
    return {
        "spkid": str(spkid) if spkid else None,
        "full_name": name,
        "pdes": name,
        "name": name,
        "prefix": None,
        "neo": "N",
        "pha": "N",
        "H": H,
        "diameter": diameter,
        "albedo": albedo,
        "rot_per": rot_per,
        "GM": GM,
        "BV": None,
        "UB": None,
        "spec_B": None,
        "spec_T": None,
        "a": round(a_km / AU_KM, 8) if a_km else None,
        "a_km": a_km,
        "e": e,
        "i": i,
        "om": None,
        "w": None,
        "ma": None,
        "tp": None,
        "type": "moon",
        "parent": parent,
        "condition_code": None,
        "rms": None,
        "discovery_year": discovery_year,
    }


MOONS = [
    # ── Earth ────────────────────────────────────────────────────────
    _moon(301, "Moon", "Earth", 3474.8, 0.12, 655.728, 4902.800, 384400, 0.0549, 5.145, -12.74),

    # ── Mars ─────────────────────────────────────────────────────────
    _moon(401, "Phobos", "Mars", 22.4, 0.071, 7.654, 0.0007112, 9376, 0.0151, 1.093, None, 1877),
    _moon(402, "Deimos", "Mars", 12.4, 0.068, 30.312, 0.0000985, 23463, 0.0002, 0.93, None, 1877),

    # ── Jupiter ──────────────────────────────────────────────────────
    # Inner moons
    _moon(516, "Metis", "Jupiter", 43.0, 0.061, 7.077, None, 128000, 0.0002, 0.06, None, 1979),
    _moon(515, "Adrastea", "Jupiter", 16.4, 0.10, 7.154, None, 129000, 0.0015, 0.03, None, 1979),
    _moon(505, "Amalthea", "Jupiter", 167.0, 0.090, 11.952, None, 181400, 0.0032, 0.380, None, 1892),
    _moon(514, "Thebe", "Jupiter", 98.6, 0.047, 16.178, None, 221900, 0.0176, 1.076, None, 1979),
    # Galilean moons
    _moon(501, "Io", "Jupiter", 3643.2, 0.63, 42.459, 5959.916, 421800, 0.0041, 0.036, -1.68, 1610),
    _moon(502, "Europa", "Jupiter", 3121.6, 0.67, 85.228, 3202.739, 671100, 0.0094, 0.466, -1.41, 1610),
    _moon(503, "Ganymede", "Jupiter", 5268.2, 0.43, 171.709, 9887.834, 1070400, 0.0011, 0.177, -2.09, 1610),
    _moon(504, "Callisto", "Jupiter", 4820.6, 0.17, 400.536, 7179.289, 1882700, 0.0074, 0.192, -1.05, 1610),
    # Himalia group
    _moon(513, "Leda", "Jupiter", 20.0, 0.07, None, None, 11165000, 0.164, 27.46, None, 1974),
    _moon(506, "Himalia", "Jupiter", 139.6, 0.04, 7.782, None, 11461000, 0.162, 27.50, None, 1904),
    _moon(510, "Lysithea", "Jupiter", 42.2, 0.04, None, None, 11717000, 0.112, 28.30, None, 1938),
    _moon(507, "Elara", "Jupiter", 79.9, 0.04, 12.0, None, 11741000, 0.217, 26.63, None, 1905),
    _moon(553, "Dia", "Jupiter", 4.0, 0.04, None, None, 12118000, 0.211, 28.23, None, 2000),
    # Themisto
    _moon(518, "Themisto", "Jupiter", 8.0, 0.04, None, None, 7507000, 0.242, 43.08, None, 1975),
    # Carpo
    _moon(546, "Carpo", "Jupiter", 3.0, 0.04, None, None, 17058000, 0.430, 51.40, None, 2003),
    # Valetudo (prograde distant)
    _moon(562, "Valetudo", "Jupiter", 1.0, 0.04, None, None, 18928000, 0.222, 34.01, None, 2016),
    # Ananke group
    _moon(534, "Euporie", "Jupiter", 2.0, 0.04, None, None, 19302000, 0.144, 145.8, None, 2001),
    _moon(540, "Mneme", "Jupiter", 2.0, 0.04, None, None, 21069000, 0.227, 148.6, None, 2003),
    _moon(533, "Euanthe", "Jupiter", 3.0, 0.04, None, None, 20797000, 0.232, 148.9, None, 2001),
    _moon(522, "Harpalyke", "Jupiter", 4.3, 0.04, None, None, 20858000, 0.226, 148.6, None, 2000),
    _moon(527, "Praxidike", "Jupiter", 6.8, 0.04, None, None, 20908000, 0.231, 149.0, None, 2000),
    _moon(529, "Thyone", "Jupiter", 4.0, 0.04, None, None, 20940000, 0.229, 148.5, None, 2001),
    _moon(554, "Thelxinoe", "Jupiter", 2.0, 0.04, None, None, 21162000, 0.221, 151.4, None, 2003),
    _moon(545, "Helike", "Jupiter", 4.0, 0.04, None, None, 21263000, 0.156, 154.8, None, 2003),
    _moon(524, "Iocaste", "Jupiter", 5.2, 0.04, None, None, 21269000, 0.216, 149.4, None, 2000),
    _moon(512, "Ananke", "Jupiter", 29.1, 0.04, None, None, 21276000, 0.244, 148.9, None, 1951),
    _moon(530, "Hermippe", "Jupiter", 4.0, 0.04, None, None, 21131000, 0.210, 150.7, None, 2001),
    _moon(532, "Eurydome", "Jupiter", 3.0, 0.04, None, None, 22865000, 0.276, 150.3, None, 2001),
    # Carme group
    _moon(543, "Arche", "Jupiter", 3.0, 0.04, None, None, 22931000, 0.259, 165.0, None, 2002),
    _moon(538, "Pasithee", "Jupiter", 2.0, 0.04, None, None, 23004000, 0.267, 165.1, None, 2001),
    _moon(521, "Chaldene", "Jupiter", 3.8, 0.04, None, None, 23100000, 0.251, 165.2, None, 2000),
    _moon(526, "Isonoe", "Jupiter", 3.8, 0.04, None, None, 23155000, 0.246, 165.2, None, 2000),
    _moon(525, "Erinome", "Jupiter", 3.2, 0.04, None, None, 23196000, 0.266, 164.9, None, 2000),
    _moon(537, "Kale", "Jupiter", 2.0, 0.04, None, None, 23217000, 0.260, 165.0, None, 2001),
    _moon(531, "Aitne", "Jupiter", 3.0, 0.04, None, None, 23229000, 0.264, 165.1, None, 2001),
    _moon(520, "Taygete", "Jupiter", 5.0, 0.04, None, None, 23280000, 0.252, 165.2, None, 2000),
    _moon(511, "Carme", "Jupiter", 46.7, 0.04, None, None, 23404000, 0.253, 164.9, None, 1938),
    _moon(523, "Kalyke", "Jupiter", 5.2, 0.04, None, None, 23566000, 0.245, 165.2, None, 2000),
    _moon(547, "Eukelade", "Jupiter", 4.0, 0.04, None, None, 23661000, 0.272, 165.5, None, 2003),
    _moon(544, "Kallichore", "Jupiter", 2.0, 0.04, None, None, 23288000, 0.264, 165.5, None, 2003),
    # Pasiphae group
    _moon(519, "Megaclite", "Jupiter", 5.4, 0.04, None, None, 23493000, 0.421, 152.8, None, 2000),
    _moon(517, "Callirrhoe", "Jupiter", 8.6, 0.04, None, None, 24103000, 0.283, 147.1, None, 1999),
    _moon(508, "Pasiphae", "Jupiter", 57.8, 0.04, None, None, 23624000, 0.409, 151.4, None, 1908),
    _moon(509, "Sinope", "Jupiter", 35.0, 0.04, None, None, 23939000, 0.250, 158.1, None, 1914),
    _moon(528, "Autonoe", "Jupiter", 4.0, 0.04, None, None, 24046000, 0.334, 152.9, None, 2001),
    _moon(536, "Sponde", "Jupiter", 2.0, 0.04, None, None, 23487000, 0.312, 151.0, None, 2001),
    _moon(548, "Cyllene", "Jupiter", 2.0, 0.04, None, None, 23951000, 0.319, 149.3, None, 2003),
    _moon(539, "Hegemone", "Jupiter", 3.0, 0.04, None, None, 23947000, 0.328, 155.2, None, 2003),
    _moon(541, "Aoede", "Jupiter", 4.0, 0.04, None, None, 23981000, 0.432, 158.3, None, 2003),
    _moon(549, "Kore", "Jupiter", 2.0, 0.04, None, None, 24543000, 0.325, 145.0, None, 2003),
    # Additional named Jupiter moons
    _moon(535, "Orthosie", "Jupiter", 2.0, 0.04, None, None, 20720000, 0.281, 145.9, None, 2001),
    _moon(542, "Thelxinoe", "Jupiter", 2.0, 0.04, None, None, 21162000, 0.221, 151.4, None, 2003),
    _moon(550, "Herse", "Jupiter", 2.0, 0.04, None, None, 23097000, 0.249, 164.2, None, 2003),
    _moon(551, "Eirene", "Jupiter", 4.0, 0.04, None, None, 23495000, 0.270, 164.2, None, 2003),
    _moon(552, "Philophrosyne", "Jupiter", 2.0, 0.04, None, None, 22627000, 0.194, 143.6, None, 2003),
    _moon(555, "Carme-like S/2003 J 9", "Jupiter", 1.0, 0.04, None, None, 23384000, 0.263, 165.0, None, 2003),
    _moon(556, "Pandia", "Jupiter", 3.0, 0.04, None, None, 11525000, 0.180, 28.15, None, 2017),
    _moon(557, "Ersa", "Jupiter", 3.0, 0.04, None, None, 11453000, 0.094, 30.61, None, 2018),

    # ── Saturn ───────────────────────────────────────────────────────
    # Ring-embedded and inner moons
    _moon(618, "Pan", "Saturn", 28.2, 0.5, 13.580, None, 133584, 0.0000, 0.001, None, 1990),
    _moon(635, "Daphnis", "Saturn", 7.6, 0.5, None, None, 136505, 0.0000, 0.004, None, 2005),
    _moon(615, "Atlas", "Saturn", 30.2, 0.4, 14.429, None, 137670, 0.0012, 0.003, None, 1980),
    _moon(616, "Prometheus", "Saturn", 86.2, 0.6, 14.711, None, 139380, 0.0022, 0.008, None, 1980),
    _moon(617, "Pandora", "Saturn", 81.4, 0.5, 15.084, None, 141720, 0.0042, 0.050, None, 1980),
    _moon(611, "Epimetheus", "Saturn", 116.2, 0.73, 16.672, 0.0351, 151422, 0.0098, 0.351, None, 1977),
    _moon(610, "Janus", "Saturn", 178.8, 0.71, 16.672, 0.1263, 151472, 0.0068, 0.163, None, 1966),
    _moon(632, "Methone", "Saturn", 3.2, 0.7, None, None, 194440, 0.0001, 0.007, None, 2004),
    _moon(649, "Anthe", "Saturn", 1.8, 0.5, None, None, 197700, 0.001, 0.02, None, 2007),
    _moon(633, "Pallene", "Saturn", 5.0, 0.5, None, None, 212280, 0.004, 0.181, None, 2004),
    # Major inner moons
    _moon(601, "Mimas", "Saturn", 396.4, 0.962, 22.613, 2.5026, 185539, 0.0196, 1.574, None, 1789),
    _moon(602, "Enceladus", "Saturn", 504.2, 1.375, 32.885, 7.2096, 238042, 0.0047, 0.009, None, 1789),
    _moon(603, "Tethys", "Saturn", 1062.2, 1.229, 45.307, 41.209, 294672, 0.0001, 1.091, None, 1684),
    _moon(613, "Telesto", "Saturn", 24.8, 1.0, None, None, 294672, 0.0002, 1.18, None, 1980),
    _moon(614, "Calypso", "Saturn", 21.4, 0.7, None, None, 294672, 0.0005, 1.50, None, 1980),
    _moon(604, "Dione", "Saturn", 1122.8, 0.998, 65.686, 73.113, 377415, 0.0022, 0.028, None, 1684),
    _moon(612, "Helene", "Saturn", 35.2, 0.6, None, None, 377415, 0.0071, 0.213, None, 1980),
    _moon(634, "Polydeuces", "Saturn", 2.6, 0.5, None, None, 377415, 0.019, 0.175, None, 2004),
    _moon(605, "Rhea", "Saturn", 1527.6, 0.949, 108.42, 153.94, 527068, 0.0010, 0.333, None, 1672),
    _moon(606, "Titan", "Saturn", 5149.46, 0.22, 382.69, 8978.14, 1221870, 0.0288, 0.312, -1.28, 1655),
    _moon(607, "Hyperion", "Saturn", 270.0, 0.3, None, 0.3727, 1481010, 0.1042, 0.615, None, 1848),
    _moon(608, "Iapetus", "Saturn", 1468.6, 0.6, 1903.9, 120.51, 3560820, 0.0276, 15.47, None, 1671),
    _moon(609, "Phoebe", "Saturn", 213.0, 0.081, 9.274, 0.5531, 12944300, 0.164, 175.3, None, 1898),
    # Norse (retrograde irregular) group
    _moon(636, "Kiviuq", "Saturn", 16.0, 0.04, None, None, 11111000, 0.334, 45.71, None, 2000),
    _moon(637, "Ijiraq", "Saturn", 12.0, 0.06, None, None, 11124000, 0.316, 46.44, None, 2000),
    _moon(619, "Paaliaq", "Saturn", 22.0, 0.06, None, None, 15200000, 0.363, 45.13, None, 2000),
    _moon(620, "Skathi", "Saturn", 8.0, 0.04, None, None, 15541000, 0.270, 152.7, None, 2000),
    _moon(638, "Albiorix", "Saturn", 32.0, 0.06, None, None, 16182000, 0.478, 34.21, None, 2000),
    _moon(651, "S/2007 S 2", "Saturn", 6.0, 0.04, None, None, 16725000, 0.218, 174.0, None, 2007),
    _moon(626, "Bebhionn", "Saturn", 6.0, 0.04, None, None, 17119000, 0.469, 35.01, None, 2004),
    _moon(639, "Erriapo", "Saturn", 10.0, 0.06, None, None, 17343000, 0.474, 34.69, None, 2000),
    _moon(621, "Siarnaq", "Saturn", 40.0, 0.06, None, None, 17531000, 0.296, 46.00, None, 2000),
    _moon(628, "Skoll", "Saturn", 6.0, 0.04, None, None, 17665000, 0.464, 161.0, None, 2006),
    _moon(640, "Tarvos", "Saturn", 15.0, 0.06, None, None, 17983000, 0.531, 33.83, None, 2000),
    _moon(630, "Tarqeq", "Saturn", 7.0, 0.04, None, None, 18009000, 0.108, 46.09, None, 2007),
    _moon(641, "Greip", "Saturn", 6.0, 0.04, None, None, 18206000, 0.326, 179.8, None, 2006),
    _moon(629, "Hyrrokkin", "Saturn", 8.0, 0.04, None, None, 18437000, 0.333, 151.5, None, 2006),
    _moon(622, "Mundilfari", "Saturn", 7.0, 0.04, None, None, 18685000, 0.210, 167.5, None, 2000),
    _moon(650, "Jarnsaxa", "Saturn", 6.0, 0.04, None, None, 18811000, 0.216, 163.3, None, 2006),
    _moon(643, "Narvi", "Saturn", 7.0, 0.04, None, None, 19007000, 0.431, 145.8, None, 2003),
    _moon(631, "Bergelmir", "Saturn", 6.0, 0.04, None, None, 19336000, 0.142, 158.6, None, 2004),
    _moon(644, "Suttungr", "Saturn", 7.0, 0.04, None, None, 19459000, 0.114, 175.8, None, 2000),
    _moon(627, "Hati", "Saturn", 6.0, 0.04, None, None, 19856000, 0.372, 165.8, None, 2004),
    _moon(647, "S/2004 S 13", "Saturn", 6.0, 0.04, None, None, 18404000, 0.261, 168.8, None, 2004),
    _moon(652, "S/2004 S 17", "Saturn", 4.0, 0.04, None, None, 19447000, 0.179, 168.2, None, 2004),
    _moon(623, "Bestla", "Saturn", 7.0, 0.04, None, None, 20192000, 0.521, 145.2, None, 2004),
    _moon(642, "Farbauti", "Saturn", 5.0, 0.04, None, None, 20390000, 0.206, 156.4, None, 2004),
    _moon(645, "Thrymr", "Saturn", 7.0, 0.04, None, None, 20474000, 0.470, 175.8, None, 2000),
    _moon(648, "S/2004 S 7", "Saturn", 6.0, 0.04, None, None, 20576000, 0.529, 166.2, None, 2004),
    _moon(625, "Aegir", "Saturn", 6.0, 0.04, None, None, 20751000, 0.252, 166.7, None, 2004),
    _moon(646, "S/2006 S 1", "Saturn", 6.0, 0.04, None, None, 18981000, 0.130, 154.2, None, 2006),
    _moon(624, "Fornjot", "Saturn", 6.0, 0.04, None, None, 25146000, 0.206, 170.4, None, 2004),
    _moon(653, "Fenrir", "Saturn", 4.0, 0.04, None, None, 22454000, 0.136, 164.9, None, 2004),
    _moon(654, "Surtur", "Saturn", 6.0, 0.04, None, None, 22707000, 0.451, 177.5, None, 2006),
    _moon(655, "Kari", "Saturn", 7.0, 0.04, None, None, 22118000, 0.478, 156.3, None, 2006),
    _moon(656, "Ymir", "Saturn", 18.0, 0.06, None, None, 23041000, 0.335, 173.1, None, 2000),
    _moon(657, "Loge", "Saturn", 6.0, 0.04, None, None, 23065000, 0.187, 167.9, None, 2006),

    # ── Uranus ───────────────────────────────────────────────────────
    # Inner moons
    _moon(706, "Cordelia", "Uranus", 40.2, 0.07, None, None, 49770, 0.0003, 0.085, None, 1986),
    _moon(707, "Ophelia", "Uranus", 42.8, 0.07, None, None, 53790, 0.0099, 0.104, None, 1986),
    _moon(708, "Bianca", "Uranus", 51.4, 0.07, None, None, 59170, 0.0009, 0.193, None, 1986),
    _moon(709, "Cressida", "Uranus", 79.6, 0.07, None, None, 61780, 0.0004, 0.006, None, 1986),
    _moon(710, "Desdemona", "Uranus", 64.0, 0.07, None, None, 62680, 0.0001, 0.113, None, 1986),
    _moon(711, "Juliet", "Uranus", 93.6, 0.07, None, None, 64350, 0.0007, 0.065, None, 1986),
    _moon(712, "Portia", "Uranus", 135.2, 0.07, None, None, 66090, 0.0001, 0.059, None, 1986),
    _moon(713, "Rosalind", "Uranus", 72.0, 0.07, None, None, 69940, 0.0001, 0.279, None, 1986),
    _moon(727, "Cupid", "Uranus", 17.8, 0.07, None, None, 74392, 0.0013, 0.099, None, 2003),
    _moon(714, "Belinda", "Uranus", 80.6, 0.07, None, None, 75260, 0.0001, 0.031, None, 1986),
    _moon(725, "Perdita", "Uranus", 30.0, 0.07, None, None, 76420, 0.0116, 0.470, None, 1986),
    _moon(715, "Puck", "Uranus", 162.0, 0.07, 18.284, None, 86010, 0.0001, 0.319, None, 1985),
    _moon(726, "Mab", "Uranus", 24.0, 0.07, None, None, 97736, 0.0025, 0.134, None, 2003),
    # Major moons
    _moon(701, "Ariel", "Uranus", 1157.8, 0.53, 60.489, 83.46, 190900, 0.0012, 0.041, None, 1851),
    _moon(702, "Umbriel", "Uranus", 1169.4, 0.26, 99.460, 78.20, 266000, 0.0039, 0.128, None, 1851),
    _moon(703, "Titania", "Uranus", 1576.8, 0.35, 208.94, 228.2, 436300, 0.0011, 0.079, None, 1787),
    _moon(704, "Oberon", "Uranus", 1522.8, 0.31, 323.12, 192.4, 583500, 0.0014, 0.068, None, 1787),
    _moon(705, "Miranda", "Uranus", 471.6, 0.32, 33.923, 4.4, 129900, 0.0013, 4.338, None, 1948),
    # Irregular moons
    _moon(716, "Caliban", "Uranus", 72.0, 0.04, None, None, 7231000, 0.159, 140.9, None, 1997),
    _moon(720, "Stephano", "Uranus", 32.0, 0.04, None, None, 8004000, 0.229, 144.1, None, 1999),
    _moon(717, "Sycorax", "Uranus", 150.0, 0.04, None, None, 12179000, 0.522, 159.4, None, 1997),
    _moon(721, "Trinculo", "Uranus", 18.0, 0.04, None, None, 8504000, 0.220, 167.0, None, 2001),
    _moon(718, "Prospero", "Uranus", 50.0, 0.04, None, None, 16256000, 0.444, 151.8, None, 1999),
    _moon(719, "Setebos", "Uranus", 48.0, 0.04, None, None, 17418000, 0.591, 158.2, None, 1999),
    _moon(722, "Francisco", "Uranus", 22.0, 0.04, None, None, 4276000, 0.146, 147.3, None, 2001),
    _moon(723, "Ferdinand", "Uranus", 20.0, 0.04, None, None, 20901000, 0.368, 169.8, None, 2001),
    _moon(724, "Margaret", "Uranus", 20.0, 0.04, None, None, 14345000, 0.661, 57.37, None, 2003),

    # ── Neptune ──────────────────────────────────────────────────────
    # Inner moons
    _moon(803, "Naiad", "Neptune", 60.4, 0.072, 7.070, None, 48227, 0.0003, 4.691, None, 1989),
    _moon(804, "Thalassa", "Neptune", 81.4, 0.091, 7.485, None, 50075, 0.0002, 0.135, None, 1989),
    _moon(805, "Despina", "Neptune", 150.0, 0.090, 7.994, None, 52526, 0.0001, 0.068, None, 1989),
    _moon(806, "Galatea", "Neptune", 174.8, 0.079, 10.297, None, 61953, 0.0001, 0.034, None, 1989),
    _moon(807, "Larissa", "Neptune", 194.0, 0.091, 13.325, None, 73548, 0.0014, 0.205, None, 1981),
    _moon(814, "Hippocamp", "Neptune", 34.8, 0.09, None, None, 105283, 0.0005, 0.064, None, 2013),
    _moon(808, "Proteus", "Neptune", 420.0, 0.096, 26.868, None, 117647, 0.0005, 0.075, None, 1989),
    # Triton (retrograde)
    _moon(801, "Triton", "Neptune", 2706.8, 0.719, 141.04, 1427.6, 354759, 0.0000, 156.865, -1.24, 1846),
    # Irregular moons
    _moon(802, "Nereid", "Neptune", 340.0, 0.155, None, None, 5513818, 0.751, 7.232, None, 1949),
    _moon(809, "Halimede", "Neptune", 62.0, 0.04, None, None, 16611000, 0.265, 112.7, None, 2002),
    _moon(810, "Psamathe", "Neptune", 40.0, 0.04, None, None, 46695000, 0.380, 137.4, None, 2003),
    _moon(811, "Sao", "Neptune", 44.0, 0.04, None, None, 22228000, 0.137, 48.51, None, 2002),
    _moon(812, "Laomedeia", "Neptune", 42.0, 0.04, None, None, 23567000, 0.397, 37.87, None, 2002),
    _moon(813, "Neso", "Neptune", 60.0, 0.04, None, None, 49285000, 0.571, 136.4, None, 2002),

    # ── Pluto ────────────────────────────────────────────────────────
    _moon(901, "Charon", "Pluto", 1212.0, 0.372, 153.294, 105.88, 19591, 0.0002, 0.080, None, 1978),
    _moon(902, "Nix", "Pluto", 49.8, 0.56, None, 0.003, 48694, 0.002, 0.133, None, 2005),
    _moon(903, "Hydra", "Pluto", 51.0, 0.83, None, 0.003, 64738, 0.006, 0.242, None, 2005),
    _moon(904, "Kerberos", "Pluto", 19.0, 0.56, None, None, 57783, 0.003, 0.389, None, 2011),
    _moon(905, "Styx", "Pluto", 16.0, 0.65, None, None, 42656, 0.006, 0.809, None, 2012),
]


def main():
    os.makedirs("cache", exist_ok=True)

    # De-duplicate by spkid (keep first occurrence)
    seen_spkids = set()
    unique_moons = []
    for m in MOONS:
        sid = m.get("spkid")
        key = sid if sid else m["name"]
        if key not in seen_spkids:
            seen_spkids.add(key)
            unique_moons.append(m)

    data = {
        "planets": PLANETS,
        "moons": unique_moons,
        "metadata": {
            "planet_count": len(PLANETS),
            "moon_count": len(unique_moons),
            "sources": [
                "JPL Solar System Dynamics - Planetary Satellite Physical Parameters",
                "NASA Planetary Fact Sheets",
                "IAU Minor Planet Center",
            ],
            "fields_note": "SBDB-compatible format. a = semi-major axis in AU "
                           "(heliocentric for planets, planet-centric for moons). "
                           "a_km = planet-centric semi-major axis in km (moons only).",
        }
    }

    out_path = os.path.join("cache", "planets_moons.json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Generated {out_path}")
    print(f"  Planets: {len(PLANETS)}")
    print(f"  Moons:   {len(unique_moons)}")
    parents = {}
    for m in unique_moons:
        p = m["parent"]
        parents[p] = parents.get(p, 0) + 1
    for p in ["Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]:
        print(f"    {p}: {parents.get(p, 0)}")


if __name__ == "__main__":
    main()
