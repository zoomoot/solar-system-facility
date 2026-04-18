#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Streamlit Interface for Solar System Small Bodies Explorer
Interactive data science interface for exploring under-researched objects
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import os
import numpy as np
from io import BytesIO

# Configuration -- prefer secrets, fall back to env, then default
def _get_config(key, default=None):
    try:
        return st.secrets[key]
    except (FileNotFoundError, KeyError):
        return os.environ.get(key, default)

BACKEND_URL = _get_config("BACKEND_URL", "http://localhost:5050")
SUPABASE_URL = _get_config("SUPABASE_URL", "")
SUPABASE_KEY = _get_config("SUPABASE_KEY", "")

# ── Supabase client (lazy, optional) ───────────────────────────────
_sb_client = None

def get_supabase():
    global _sb_client
    if _sb_client is not None:
        return _sb_client
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        from supabase import create_client
        _sb_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _sb_client
    except Exception:
        return None

# Session state for object details dialog
if 'show_object_details' not in st.session_state:
    st.session_state.show_object_details = False
if 'selected_object' not in st.session_state:
    st.session_state.selected_object = None
if 'entity' not in st.session_state:
    st.session_state.entity = None
if 'entity_profile' not in st.session_state:
    st.session_state.entity_profile = None
st.set_page_config(
    page_title="Solar System Explorer",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background-color: #0a0e27;
    }
    .stMetric {
        background-color: rgba(42, 63, 95, 0.4);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #2a3f5f;
    }
    h1, h2, h3 {
        color: #4a9eff;
    }
    .priority-high {
        color: #ff5252;
        font-weight: bold;
    }
    .priority-medium {
        color: #ffc107;
        font-weight: bold;
    }
    .priority-low {
        color: #4caf50;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# ── Threaded dialogue helpers ──────────────────────────────────────
def _build_thread_tree(posts):
    """Organise flat list of posts into a tree structure using parent_id."""
    by_id = {p["id"]: {**p, "_children": []} for p in posts}
    roots = []
    for p in posts:
        node = by_id[p["id"]]
        pid = p.get("parent_id")
        if pid and pid in by_id:
            by_id[pid]["_children"].append(node)
        else:
            roots.append(node)
    return roots


def _render_thread(node, designation, kind, depth=0):
    """Recursively render a post and its replies with visual nesting."""
    indent = "│  " * depth
    sb = get_supabase()
    entity = st.session_state.get("entity")

    author = node.get("entity_name", "Unknown")
    ts = (node.get("created_at") or "")[:16]
    body = node.get("body") or ""
    post_id = node["id"]

    st.markdown(
        f"<div style='margin-left:{depth * 24}px; padding:6px 0; "
        f"border-left: {'2px solid #2a3f5f' if depth > 0 else 'none'}; "
        f"padding-left: {'10px' if depth > 0 else '0'};'>"
        f"<strong>{author}</strong> "
        f"<span style='color:#888; font-size:0.85em;'>{ts}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if body:
        st.markdown(
            f"<div style='margin-left:{depth * 24 + (10 if depth > 0 else 0)}px; "
            f"padding-bottom:4px;'>{body}</div>",
            unsafe_allow_html=True,
        )

    if entity and sb:
        reply_key = f"reply_toggle_{kind}_{post_id}"
        if reply_key not in st.session_state:
            st.session_state[reply_key] = False

        col_reply, _ = st.columns([1, 5])
        with col_reply:
            if st.button("↩ Reply", key=f"reply_btn_{kind}_{post_id}",
                         type="secondary"):
                st.session_state[reply_key] = not st.session_state[reply_key]

        if st.session_state[reply_key]:
            with st.form(key=f"reply_form_{kind}_{post_id}"):
                reply_body = st.text_area(
                    "Reply", key=f"reply_text_{kind}_{post_id}",
                    placeholder="Write your reply...", height=80,
                )
                if st.form_submit_button("Post Reply"):
                    if reply_body.strip():
                        profile = st.session_state.get("entity_profile", {})
                        try:
                            sb.table("contributions").insert({
                                "object_designation": designation,
                                "entity_id": str(entity.id),
                                "entity_name": profile.get("display_name", entity.email),
                                "kind": kind,
                                "body": reply_body.strip(),
                                "parent_id": post_id,
                            }).execute()
                            st.session_state[reply_key] = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {str(e)[:80]}")

    for child in node.get("_children", []):
        _render_thread(child, designation, kind, depth + 1)


def _render_dialogue(designation, kind, label_singular, sb, entity):
    """Render a complete threaded dialogue for a given contribution kind."""
    if not sb:
        st.info("Community features require Supabase configuration.")
        return

    try:
        posts = sb.table("contributions").select("*").eq(
            "object_designation", designation
        ).eq("kind", kind).order("created_at").limit(200).execute()
        post_list = posts.data or []
    except Exception:
        post_list = []

    if post_list:
        tree = _build_thread_tree(post_list)
        for root in tree:
            _render_thread(root, designation, kind)
            st.markdown("---")
    else:
        st.info(f"No {label_singular} yet. Be the first to contribute.")

    if entity:
        with st.form(key=f"new_{kind}_form_{designation}"):
            new_body = st.text_area(
                f"New {label_singular}",
                key=f"new_{kind}_text_{designation}",
                placeholder=f"Start a new {label_singular} thread...",
            )
            if st.form_submit_button(f"Post {label_singular.title()}"):
                if new_body.strip():
                    profile = st.session_state.get("entity_profile", {})
                    try:
                        sb.table("contributions").insert({
                            "object_designation": designation,
                            "entity_id": str(entity.id),
                            "entity_name": profile.get("display_name", entity.email),
                            "kind": kind,
                            "body": new_body.strip(),
                        }).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {str(e)[:80]}")
    else:
        st.caption(f"🔑 Log in to post {label_singular}s")


# Helper Functions
@st.cache_data(ttl=3600)
def fetch_objects(limit=100, source='jpl', filters=None):
    """Fetch objects from backend API with filters"""
    try:
        # Calculate timeout based on number of objects
        # Increased base timeout for ISO queries (which make multiple sequential API calls)
        timeout = max(60, int(limit / 1000) + 60)
        
        # Build query parameters
        params = {"limit": limit, "source": source}
        
        # Add filters if provided
        if filters:
            if 'object_types' in filters and filters['object_types']:
                params['object_types'] = ','.join(filters['object_types'])
            if 'diameter_min' in filters:
                params['diameter_min'] = filters['diameter_min']
            if 'diameter_max' in filters:
                params['diameter_max'] = filters['diameter_max']
        
        response = requests.get(
            f"{BACKEND_URL}/api/objects/search",
            params=params,
            timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            return data.get('objects', [])
        return []
    except Exception as e:
        st.error(f"Error fetching objects: {e}")
        return []

def _neocp_count() -> int:
    """Read the NEOCP catalog file to get the live candidate count."""
    try:
        path = os.path.join(os.path.dirname(__file__), "cache", "catalog_neocp.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            return data.get("count", 0)
    except Exception:
        pass
    return 0


@st.cache_data(ttl=86400)  # Cache for 24 hours
def fetch_object_type_counts():
    """Fetch object type counts from cached JSON file (instant load)"""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/object-types/counts",
            timeout=5  # Quick timeout since reading from file
        )
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            return {
                'counts': data.get('counts', {}),
                'last_updated': data.get('last_updated', 'Unknown'),
                'source': data.get('source', 'unknown')
            }
        return {'counts': {}, 'last_updated': 'Unknown', 'source': 'error'}
    except Exception as e:
        st.warning(f"Could not fetch object type counts: {e}")
        # Return fallback counts if API fails
        return {
            'counts': {
                'NEO': 39799,
                'MBA': 1303383,
                'IMB': 31680,
                'OMB': 46388,
                'TNO': 5575,
                'Centaur': 966,
                'Trojan': 15456,
                'IEO': 37,
                'ATE': 3192,
                'APO': 22547,
                'AMO': 14060,
                'Comet': 4037
            },
            'last_updated': 'Never',
            'source': 'fallback'
        }

def refresh_object_type_counts():
    """Refresh object type counts from JPL API"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/object-types/counts/refresh",
            timeout=60  # Longer timeout for API queries
        )
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            # Clear the cache to force reload
            st.cache_data.clear()
            return True, data.get('counts', {}), data.get('last_updated', 'Unknown')
        return False, {}, "API returned error"
    except Exception as e:
        return False, {}, str(e)


@st.cache_data(ttl=3600)
def fetch_completeness_stats():
    """Fetch completeness statistics"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/stats/completeness", timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            return data.get('stats', {})
        return {}
    except Exception as e:
        st.error(f"Error fetching stats: {e}")
        return {}

@st.cache_data(ttl=3600)
def fetch_under_researched(priority='medium', limit=50):
    """Fetch under-researched objects"""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/under-researched",
            params={"priority": priority, "limit": limit},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            return data.get('objects', [])
        return []
    except Exception as e:
        st.error(f"Error fetching under-researched: {e}")
        return []

def fetch_object_details(designation):
    """Fetch detailed information for a specific object from our backend (includes JPL + SsODNet)"""
    try:
        # Use our backend endpoint which fetches both JPL and SsODNet data
        response = requests.get(
            f"{BACKEND_URL}/api/objects/{designation}",
            timeout=30  # Longer timeout since it fetches from multiple sources
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching object details: {e}")
        return None

def calculate_orbit_3d(a, e, i, om, w, num_points=200):
    """
    Calculate 3D orbital positions from Keplerian elements
    
    Parameters:
    - a: semi-major axis (AU)
    - e: eccentricity
    - i: inclination (degrees)
    - om: longitude of ascending node (degrees)
    - w: argument of perihelion (degrees)
    - num_points: number of points to calculate along the orbit
    
    Returns:
    - x, y, z: arrays of 3D coordinates
    """
    # Convert angles to radians
    i_rad = np.radians(i)
    om_rad = np.radians(om)
    w_rad = np.radians(w)
    
    # True anomaly values (full orbit)
    nu = np.linspace(0, 2*np.pi, num_points)
    
    # Calculate distance from focus
    r = a * (1 - e**2) / (1 + e * np.cos(nu))
    
    # Position in orbital plane
    x_orb = r * np.cos(nu)
    y_orb = r * np.sin(nu)
    
    # Rotation matrices to transform to ecliptic coordinates
    # R3(-om) * R1(-i) * R3(-w)
    cos_om, sin_om = np.cos(om_rad), np.sin(om_rad)
    cos_i, sin_i = np.cos(i_rad), np.sin(i_rad)
    cos_w, sin_w = np.cos(w_rad), np.sin(w_rad)
    
    # Combined rotation
    x = x_orb * (cos_om * cos_w - sin_om * sin_w * cos_i) - y_orb * (cos_om * sin_w + sin_om * cos_w * cos_i)
    y = x_orb * (sin_om * cos_w + cos_om * sin_w * cos_i) - y_orb * (sin_om * sin_w - cos_om * cos_w * cos_i)
    z = x_orb * (sin_w * sin_i) + y_orb * (cos_w * sin_i)
    
    return x, y, z

def create_orbit_visualization(elements, obj_name):
    """Create an interactive 3D orbit visualization using Plotly"""
    try:
        # Extract orbital elements
        a = float(elements.get('a', 0))
        e = float(elements.get('e', 0))
        i = float(elements.get('i', 0))
        om = float(elements.get('om', 0))
        w = float(elements.get('w', 0))
        
        if a == 0:
            return None
        
        # Calculate orbit
        x, y, z = calculate_orbit_3d(a, e, i, om, w)
        
        # Create 3D plot
        fig = go.Figure()
        
        # Add the orbit
        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z,
            mode='lines',
            name=f'{obj_name} Orbit',
            line=dict(color='cyan', width=3),
            hovertemplate='<b>Distance from Sun</b><br>' +
                         'X: %{x:.3f} AU<br>' +
                         'Y: %{y:.3f} AU<br>' +
                         'Z: %{z:.3f} AU<br>' +
                         '<extra></extra>'
        ))
        
        # Add perihelion point
        x_peri, y_peri, z_peri = calculate_orbit_3d(a, e, i, om, w, num_points=1)
        fig.add_trace(go.Scatter3d(
            x=[x_peri[0]], y=[y_peri[0]], z=[z_peri[0]],
            mode='markers',
            name='Perihelion',
            marker=dict(size=8, color='orange', symbol='diamond'),
            hovertemplate=f'<b>Perihelion</b><br>Distance: {a*(1-e):.3f} AU<extra></extra>'
        ))
        
        # Add aphelion point
        x_aph = x[len(x)//2]
        y_aph = y[len(y)//2]
        z_aph = z[len(z)//2]
        fig.add_trace(go.Scatter3d(
            x=[x_aph], y=[y_aph], z=[z_aph],
            mode='markers',
            name='Aphelion',
            marker=dict(size=8, color='lightblue', symbol='diamond'),
            hovertemplate=f'<b>Aphelion</b><br>Distance: {a*(1+e):.3f} AU<extra></extra>'
        ))
        
        # Add the Sun at origin
        fig.add_trace(go.Scatter3d(
            x=[0], y=[0], z=[0],
            mode='markers',
            name='Sun',
            marker=dict(size=15, color='yellow', symbol='circle'),
            hovertemplate='<b>Sun</b><extra></extra>'
        ))
        
        # Calculate visualization range (needed for planetary orbits)
        max_dist = max(a * (1 + e), 1.5)
        
        # Add planetary orbits for reference (as dots)
        # Planetary orbital radii in AU (approximate circular orbits)
        planets = [
            {'name': 'Mercury', 'a': 0.387, 'color': 'gray'},
            {'name': 'Venus', 'a': 0.723, 'color': 'orange'},
            {'name': 'Earth', 'a': 1.000, 'color': 'blue'},
            {'name': 'Mars', 'a': 1.524, 'color': 'red'},
            {'name': 'Jupiter', 'a': 5.203, 'color': 'brown'},
            {'name': 'Saturn', 'a': 9.537, 'color': 'gold'},
        ]
        
        # Only show planets that are within the visualization range
        for planet in planets:
            if planet['a'] <= max_dist:
                # Create orbit as dots (markers)
                theta = np.linspace(0, 2*np.pi, 60)  # 60 points for dotted appearance
                px = planet['a'] * np.cos(theta)
                py = planet['a'] * np.sin(theta)
                pz = np.zeros_like(theta)
                
                fig.add_trace(go.Scatter3d(
                    x=px, y=py, z=pz,
                    mode='markers',
                    name=f"{planet['name']} Orbit ({planet['a']:.2f} AU)",
                    marker=dict(size=2, color=planet['color'], opacity=0.4),
                    hovertemplate=f"<b>{planet['name']}'s Orbit</b><br>{planet['a']:.3f} AU<extra></extra>",
                    showlegend=True
                ))
        
        # Update layout
        fig.update_layout(
            title=f"3D Orbit Visualization: {obj_name}",
            scene=dict(
                xaxis=dict(title='X (AU)', range=[-max_dist, max_dist]),
                yaxis=dict(title='Y (AU)', range=[-max_dist, max_dist]),
                zaxis=dict(title='Z (AU)', range=[-max_dist, max_dist]),
                aspectmode='cube',
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.2)
                )
            ),
            showlegend=True,
            height=600,
            hovermode='closest'
        )
        
        return fig
        
    except Exception as e:
        st.error(f"Error creating orbit visualization: {e}")
        return None

SPECTRAL_CLASS_COLORS = {
    'S':  ((139, 125, 107), (196, 180, 154)),
    'Sq': ((139, 125, 107), (196, 180, 154)),
    'Sr': ((139, 125, 107), (196, 180, 154)),
    'Sa': ((139, 125, 107), (196, 180, 154)),
    'Sl': ((139, 125, 107), (196, 180, 154)),
    'Sk': ((139, 125, 107), (196, 180, 154)),
    'C':  ((58, 58, 58),    (107, 107, 107)),
    'Cb': ((58, 58, 58),    (107, 107, 107)),
    'Cg': ((58, 58, 58),    (107, 107, 107)),
    'Cgh':((58, 58, 58),    (107, 107, 107)),
    'Ch': ((58, 58, 58),    (107, 107, 107)),
    'V':  ((90, 107, 122),  (138, 155, 170)),
    'Q':  ((154, 138, 112), (202, 185, 154)),
    'M':  ((122, 122, 128), (176, 176, 184)),
    'X':  ((90, 90, 90),    (154, 154, 154)),
    'Xe': ((90, 90, 90),    (154, 154, 154)),
    'Xc': ((90, 90, 90),    (154, 154, 154)),
    'Xk': ((90, 90, 90),    (154, 154, 154)),
    'D':  ((90, 58, 42),    (138, 106, 90)),
    'T':  ((74, 58, 58),    (122, 106, 106)),
    'E':  ((160, 160, 160), (216, 216, 216)),
    'P':  ((74, 58, 58),    (122, 106, 106)),
    'B':  ((74, 90, 106),   (122, 138, 154)),
    'F':  ((74, 90, 106),   (122, 138, 154)),
    'A':  ((138, 106, 74),  (186, 154, 122)),
    'K':  ((122, 112, 96),  (170, 160, 138)),
    'L':  ((122, 112, 96),  (170, 160, 138)),
    'R':  ((138, 112, 96),  (186, 160, 138)),
    'O':  ((96, 112, 96),   (138, 154, 138)),
}


def spectral_colorscale(spec_class, albedo=None):
    """Build a Plotly colorscale from asteroid spectral taxonomy and albedo."""
    lo, hi = (100, 100, 100), (170, 170, 170)

    if spec_class:
        key = spec_class.strip().rstrip(':')
        if key in SPECTRAL_CLASS_COLORS:
            lo, hi = SPECTRAL_CLASS_COLORS[key]
        elif len(key) >= 1 and key[0] in SPECTRAL_CLASS_COLORS:
            lo, hi = SPECTRAL_CLASS_COLORS[key[0]]

    brightness = 1.0
    if albedo is not None:
        try:
            a = float(albedo)
            brightness = 0.6 + 0.8 * min(a / 0.5, 1.0)
        except (ValueError, TypeError):
            pass

    def clamp(v):
        return max(0, min(255, int(v * brightness)))

    lo_s = f"rgb({clamp(lo[0])},{clamp(lo[1])},{clamp(lo[2])})"
    hi_s = f"rgb({clamp(hi[0])},{clamp(hi[1])},{clamp(hi[2])})"
    mid_r = (lo[0] + hi[0]) / 2
    mid_g = (lo[1] + hi[1]) / 2
    mid_b = (lo[2] + hi[2]) / 2
    mid_s = f"rgb({clamp(mid_r)},{clamp(mid_g)},{clamp(mid_b)})"

    return [[0, lo_s], [0.5, mid_s], [1, hi_s]]


@st.dialog("Object Details", width="large")
def display_object_details_dialog(obj_data):
    """Display detailed object information in a dialog"""
    designation = obj_data.get('designation', obj_data.get('Designation', ''))
    name = obj_data.get('name', obj_data.get('Name', 'Unknown'))
    
    st.markdown(f"### 🌠 {name}")
    st.markdown(f"**Designation:** {designation}")

    # Gate: require authentication to view full object details
    if st.session_state.entity is None:
        st.markdown("---")
        st.markdown("#### 🔒 Account Required")
        st.markdown(
            "Create a free account or log in to access full object details, "
            "community discussion, and exploration tools."
        )
        sb = get_supabase()
        if sb is None:
            st.info("Authentication is not yet configured on this instance.")
            return

        gate_action = st.radio(
            "Action", ["Login", "Sign Up", "Reset Password"],
            horizontal=True, key="gate_auth_action", label_visibility="collapsed"
        )
        if gate_action == "Login":
            g_email = st.text_input("Email", key="gate_login_email")
            g_pw = st.text_input("Password", type="password", key="gate_login_pw")
            if st.button("Login", key="gate_login_btn", type="primary"):
                if g_email and g_pw:
                    try:
                        res = sb.auth.sign_in_with_password({"email": g_email, "password": g_pw})
                        st.session_state.entity = res.user
                        try:
                            prof = sb.table("entity_profiles").select("*").eq(
                                "id", str(res.user.id)
                            ).single().execute()
                            st.session_state.entity_profile = prof.data
                        except Exception:
                            st.session_state.entity_profile = {}
                        st.rerun()
                    except Exception as e:
                        err = str(e)
                        if "Invalid login" in err or "invalid" in err.lower():
                            st.error("Invalid email or password")
                        elif "Email not confirmed" in err or "not confirmed" in err.lower():
                            st.error("Please confirm your email first. Check your inbox.")
                        else:
                            st.error(f"Login failed: {err[:80]}")
                else:
                    st.warning("Enter email and password")
        elif gate_action == "Sign Up":
            g_name = st.text_input("Display Name", key="gate_signup_name")
            g_email = st.text_input("Email", key="gate_signup_email")
            g_pw = st.text_input("Password", type="password", key="gate_signup_pw")
            g_affil = st.text_input(
                "Affiliation (optional)",
                placeholder="e.g. Backyard Observatory, UK",
                key="gate_signup_affil"
            )
            if st.button("Sign Up", key="gate_signup_btn", type="primary"):
                if g_name and g_email and g_pw:
                    try:
                        res = sb.auth.sign_up({"email": g_email, "password": g_pw})
                        if res.user:
                            try:
                                sb.table("entity_profiles").insert({
                                    "id": str(res.user.id),
                                    "display_name": g_name,
                                    "affiliation": g_affil or None,
                                    "contribution_count": 0,
                                    "missions_completed": 0,
                                }).execute()
                            except Exception:
                                pass
                            st.success(
                                "Account created! Check your email to verify, then log in."
                            )
                    except Exception as e:
                        st.error(f"Sign up failed: {str(e)[:80]}")
                else:
                    st.warning("Name, email, and password required")
        else:
            g_email = st.text_input("Email", key="gate_reset_email")
            if st.button("Send Reset Link", key="gate_reset_btn", type="primary"):
                if g_email:
                    try:
                        sb.auth.reset_password_email(g_email)
                        st.success("Password reset link sent. Check your email.")
                    except Exception as e:
                        st.error(f"Failed: {str(e)[:80]}")
                else:
                    st.warning("Enter your email address")
        return
    
    # Fetch full API data (includes JPL, SsODNet, and Wikipedia)
    with st.spinner("Fetching detailed data from available sources (JPL, SsODNet, Wikipedia)..."):
        api_response = fetch_object_details(designation)
    
    # Extract data from available sources (JPL + SsODNet + Wikipedia)
    jpl_data = api_response.get('jpl', {}) if api_response else {}
    ssodnet_data = api_response.get('ssodnet', {}) if api_response else {}
    wikipedia_data = api_response.get('wikipedia', {}) if api_response else {}
    
    # Create tabs for different data sections
    detail_tabs = st.tabs([
        "📊 Summary", 
        "🔬 Physical Properties", 
        "🛰️ Orbital Data", 
        "🌐 SsODNet Data",
        "📖 Wikipedia",
        "📡 Raw API Data",
        "🔭 Pan-STARRS DR2",
        "🧊 3D Model",
        "🖼️ Images",
        "🛰 Community"
    ])
    
    with detail_tabs[0]:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Object Type", obj_data.get('object_type', obj_data.get('Type', 'N/A')))
            st.metric("H Magnitude", obj_data.get('H', 'N/A'))
            st.metric("Priority", str(obj_data.get('priority', obj_data.get('Priority', 'unknown'))).upper())
        
        with col2:
            diameter = obj_data.get('diameter_km', obj_data.get('Diameter (km)', 'N/A'))
            if diameter and diameter != 'N/A' and str(diameter).lower() != 'none':
                st.metric("Diameter", f"{diameter} km")
            else:
                st.metric("Diameter", "Unknown")
            
            albedo = obj_data.get('albedo', obj_data.get('Albedo', 'N/A'))
            if albedo and albedo != 'N/A' and str(albedo).lower() != 'none':
                st.metric("Albedo", f"{albedo:.3f}" if isinstance(albedo, (int, float)) else albedo)
            else:
                st.metric("Albedo", "Unknown")
            
            pha = obj_data.get('pha', obj_data.get('PHA', False))
            st.metric("PHA", "Yes" if str(pha).lower() == 'yes' or pha == True else "No")
        
        with col3:
            rotation = obj_data.get('rotation_period_h', obj_data.get('Rotation Period (h)', 'N/A'))
            if rotation and rotation != 'N/A' and str(rotation).lower() != 'none':
                st.metric("Rotation Period", f"{rotation} hours")
            else:
                st.metric("Rotation Period", "Unknown")
            
            spectral_bus = obj_data.get('spectral_type_bus', obj_data.get('Spectral Type (Bus)', 'N/A'))
            st.metric("Spectral Type (Bus)", spectral_bus if spectral_bus and str(spectral_bus).lower() != 'none' else "Unknown")
            
            spectral_tholen = obj_data.get('spectral_type_tholen', obj_data.get('Spectral Type (Tholen)', 'N/A'))
            st.metric("Spectral Type (Tholen)", spectral_tholen if spectral_tholen and str(spectral_tholen).lower() != 'none' else "Unknown")
        
        # Completeness bar
        completeness = obj_data.get('completeness_pct', obj_data.get('Completeness (%)', 0))
        if completeness:
            st.markdown(f"**Data Completeness: {completeness:.1f}%**")
            st.progress(float(completeness) / 100)
    
    with detail_tabs[1]:
        st.markdown("#### Physical Characteristics")
        phys_data = {
            "Property": ["Diameter (km)", "Albedo", "Absolute Magnitude (H)", "Rotation Period (h)", 
                        "Spectral Type (Bus)", "Spectral Type (Tholen)"],
            "Value": [
                obj_data.get('diameter_km', obj_data.get('Diameter (km)', 'Unknown')),
                obj_data.get('albedo', obj_data.get('Albedo', 'Unknown')),
                obj_data.get('H', 'Unknown'),
                obj_data.get('rotation_period_h', obj_data.get('Rotation Period (h)', 'Unknown')),
                obj_data.get('spectral_type_bus', obj_data.get('Spectral Type (Bus)', 'Unknown')),
                obj_data.get('spectral_type_tholen', obj_data.get('Spectral Type (Tholen)', 'Unknown'))
            ]
        }
        st.dataframe(pd.DataFrame(phys_data), use_container_width=True, hide_index=True)
        
        if jpl_data and 'object' in jpl_data:
            st.markdown("#### Additional Physical Data from JPL")
            obj_info = jpl_data['object']
            st.write(f"**Full Name:** {obj_info.get('fullname', 'N/A')}")
            st.write(f"**Kind:** {obj_info.get('kind', 'N/A')}")
            st.write(f"**NEO:** {obj_info.get('neo', 'N/A')}")
            st.write(f"**PHA:** {obj_info.get('pha', 'N/A')}")
    
    with detail_tabs[2]:
        st.markdown("#### Orbital Elements")
        if jpl_data and 'orbit' in jpl_data:
            orbit = jpl_data['orbit']
            if 'elements' in orbit:
                elements_raw = orbit['elements']
                
                # JPL returns elements as a list of objects with 'name', 'value', 'title', etc.
                # Convert to a simple dict for easier access
                elements = {}
                if isinstance(elements_raw, list):
                    for elem in elements_raw:
                        if isinstance(elem, dict) and 'name' in elem and 'value' in elem:
                            elements[elem['name']] = elem['value']
                elif isinstance(elements_raw, dict):
                    elements = elements_raw
                
                if elements:
                    # Create two columns: one for the table, one for the visualization
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        orbit_df = pd.DataFrame([
                            {"Element": "Semi-major Axis (au)", "Value": elements.get('a', 'N/A')},
                            {"Element": "Eccentricity", "Value": elements.get('e', 'N/A')},
                            {"Element": "Inclination (deg)", "Value": elements.get('i', 'N/A')},
                            {"Element": "Longitude of Asc. Node (deg)", "Value": elements.get('om', 'N/A')},
                            {"Element": "Argument of Perihelion (deg)", "Value": elements.get('w', 'N/A')},
                            {"Element": "Mean Anomaly (deg)", "Value": elements.get('ma', 'N/A')},
                            {"Element": "Perihelion Distance (au)", "Value": elements.get('q', 'N/A')},
                            {"Element": "Aphelion Distance (au)", "Value": elements.get('ad', 'N/A')},
                            {"Element": "Orbital Period (days)", "Value": elements.get('per', 'N/A')},
                        ])
                        st.dataframe(orbit_df, use_container_width=True, hide_index=True)
                    
                    with col2:
                        st.markdown("**Orbit Characteristics:**")
                        # Quick orbital facts
                        try:
                            a_val = float(elements.get('a', 0))
                            e_val = float(elements.get('e', 0))
                            if a_val > 0:
                                st.write(f"• Orbit size: {a_val:.3f} AU")
                                st.write(f"• Orbit shape: {'Nearly circular' if e_val < 0.1 else 'Elliptical' if e_val < 0.5 else 'Highly elliptical'}")
                                st.write(f"• Perihelion: {a_val*(1-e_val):.3f} AU")
                                st.write(f"• Aphelion: {a_val*(1+e_val):.3f} AU")
                        except:
                            pass
                    
                    # Add 3D visualization below
                    st.markdown("---")
                    st.markdown("#### 3D Orbit Visualization")
                    
                    orbit_fig = create_orbit_visualization(elements, name)
                    if orbit_fig:
                        st.plotly_chart(orbit_fig, use_container_width=True)
                        st.caption("💡 **Interactive 3D View:** Drag to rotate, scroll to zoom, double-click to reset")
                    else:
                        st.warning("Could not generate orbit visualization")
            
            st.markdown("---")
            st.markdown("#### Orbit Determination")
            st.write(f"**Epoch:** {orbit.get('epoch', 'N/A')}")
            st.write(f"**Data Arc (days):** {orbit.get('data_arc', 'N/A')}")
            st.write(f"**Number of Observations:** {orbit.get('n_obs_used', 'N/A')}")
            st.write(f"**Condition Code:** {orbit.get('condition_code', 'N/A')}")
        else:
            st.info("Orbital data not available. The object may not be in JPL SBDB or the API request failed.")
    
    with detail_tabs[3]:
        st.markdown("#### SsODNet Data")
        st.markdown("**Data Source:** SsODNet (IMCCE)")
        
        if ssodnet_data:
            # Show key SsODNet information
            st.markdown("##### Object Classification")
            st.write(f"**Type:** {ssodnet_data.get('type', 'N/A')}")
            st.write(f"**Class:** {ssodnet_data.get('class', 'N/A')}")
            
            # Physical parameters from SsODNet
            if 'parameters' in ssodnet_data and 'physical' in ssodnet_data['parameters']:
                physical = ssodnet_data['parameters']['physical']
                
                st.markdown("##### Physical Parameters")
                
                # Diameter
                if 'diameter' in physical and physical['diameter'].get('value'):
                    diam = physical['diameter']
                    st.write(f"**Diameter:** {diam.get('value', 'N/A')} km (± {diam.get('error', 'N/A')})")
                    st.write(f"  - Method: {diam.get('method', 'N/A')}")
                    st.write(f"  - Bibliography: {diam.get('bibref', 'N/A')}")
                
                # Albedo
                if 'albedo' in physical and physical['albedo'].get('value'):
                    alb = physical['albedo']
                    st.write(f"**Albedo:** {alb.get('value', 'N/A')} (± {alb.get('error', 'N/A')})")
                    st.write(f"  - Method: {alb.get('method', 'N/A')}")
                    st.write(f"  - Bibliography: {alb.get('bibref', 'N/A')}")
                
                # Taxonomy
                if 'taxonomy' in physical and physical['taxonomy'].get('class'):
                    tax = physical['taxonomy']
                    st.write(f"**Taxonomy:** {tax.get('class', 'N/A')}")
                    st.write(f"  - Scheme: {tax.get('scheme', 'N/A')}")
                    st.write(f"  - Bibliography: {tax.get('bibref', 'N/A')}")
                
                # Rotation period
                if 'spins' in physical and isinstance(physical['spins'], list) and len(physical['spins']) > 0:
                    spin = physical['spins'][0]
                    if 'period' in spin and spin['period'].get('value'):
                        per = spin['period']
                        st.write(f"**Rotation Period:** {per.get('value', 'N/A')} hours (± {per.get('error', 'N/A')})")
                        st.write(f"  - Bibliography: {per.get('bibref', 'N/A')}")
            
            # Link to SsODNet
            st.markdown("---")
            st.markdown(f"[🔗 View on SsODNet](https://ssp.imcce.fr/webservices/ssodnet/api/ssocard/{name})")
        else:
            st.info("No SsODNet data available for this object")
    
    with detail_tabs[4]:  # Wikipedia tab
        st.markdown("#### 📖 Wikipedia Reference")
        st.markdown("**Data Source:** Wikipedia API")
        
        if wikipedia_data and isinstance(wikipedia_data, dict):
            st.success("✅ Wikipedia article found")
            
            # Display thumbnail if available
            if wikipedia_data.get('thumbnail'):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.image(wikipedia_data['thumbnail'], use_container_width=True)
                with col2:
                    st.markdown(f"### {wikipedia_data.get('title', 'Unknown')}")
                    if wikipedia_data.get('extract'):
                        st.markdown(wikipedia_data['extract'])
            else:
                st.markdown(f"### {wikipedia_data.get('title', 'Unknown')}")
                if wikipedia_data.get('extract'):
                    st.markdown(wikipedia_data['extract'])
            
            # Link to full article and option to load full content
            st.markdown("---")
            
            # Buttons side by side
            col1, col2 = st.columns(2)
            with col1:
                if wikipedia_data.get('url'):
                    st.link_button("📖 Read Full Article on Wikipedia", wikipedia_data['url'], use_container_width=True)
            with col2:
                load_full = st.button("📄 Load Full Article Here", use_container_width=True, key=f"load_wiki_{designation}")
            
            # Full article display at full width (outside columns)
            if load_full:
                # Fetch full article content
                page_title = wikipedia_data.get('title', '').replace(' ', '_')
                if page_title:
                    with st.spinner("Loading full article..."):
                        try:
                            # Use Wikipedia's parse API to get full HTML content
                            parse_url = "https://en.wikipedia.org/w/api.php"
                            params = {
                                'action': 'parse',
                                'page': page_title,
                                'format': 'json',
                                'prop': 'text',
                                'disableeditsection': True,
                                'disabletoc': True
                            }
                            headers = {'User-Agent': 'SolarSystemExplorer/1.0 (Educational Research Tool)'}
                            response = requests.get(parse_url, params=params, headers=headers, timeout=30)
                            
                            if response.status_code == 200:
                                data = response.json()
                                if 'parse' in data and 'text' in data['parse']:
                                    html_content = data['parse']['text']['*']
                                    
                                    # Display full article in an expander at full width
                                    with st.expander("📄 Full Wikipedia Article", expanded=True):
                                        st.markdown(f"**Article:** {wikipedia_data.get('title')}")
                                        st.markdown("---")
                                        # Display HTML content (Wikipedia returns formatted HTML)
                                        st.components.v1.html(
                                            f"""
                                            <style>
                                                body {{ font-family: sans-serif; line-height: 1.6; padding: 0; margin: 0; }}
                                                img {{ max-width: 100%; height: auto; }}
                                                table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
                                                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                                                th {{ background-color: #f2f2f2; }}
                                                .mw-parser-output {{ max-width: 100%; }}
                                            </style>
                                            <div style="width: 100%; max-height: 600px; overflow-y: auto; padding: 20px; box-sizing: border-box;">
                                                {html_content}
                                            </div>
                                            """,
                                            height=650,
                                            scrolling=True
                                        )
                                else:
                                    st.error("Could not parse article content")
                            else:
                                st.error(f"Failed to load article (Status: {response.status_code})")
                        except Exception as e:
                            st.error(f"Error loading full article: {e}")
            
            # Show search term used
            if wikipedia_data.get('search_term'):
                st.caption(f"🔍 Found using search term: **{wikipedia_data['search_term']}**")
        else:
            st.info("No Wikipedia article found for this object.")
            st.caption("💡 **Note:** Wikipedia may not have articles for all small solar system bodies, especially recently discovered or unnumbered objects.")
    
    with detail_tabs[5]:
        st.markdown("#### Raw API Response")
        
        # JPL Data
        st.markdown("##### JPL Small-Body Database")
        st.markdown(f"**API Endpoint:** `https://ssd-api.jpl.nasa.gov/sbdb.api?sstr={designation}`")
        
        col1, col2 = st.columns(2)
        with col1:
            st.link_button("🔗 View on JPL", f"https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr={designation}", use_container_width=True)
        
        if jpl_data:
            with st.expander("Show JPL JSON Data"):
                st.json(jpl_data)
        else:
            st.warning("JPL data not available")
        
        # SsODNet Data
        st.markdown("---")
        st.markdown("##### SsODNet (IMCCE)")
        st.markdown(f"**API Endpoint:** `https://ssp.imcce.fr/webservices/ssodnet/api/ssocard/{name}`")
        
        if ssodnet_data:
            with st.expander("Show SsODNet JSON Data"):
                st.json(ssodnet_data)
        else:
            st.info("SsODNet data not available")
        
        # Wikipedia Data
        st.markdown("---")
        st.markdown("##### Wikipedia")
        st.markdown("**API Endpoint:** Wikipedia REST API v1")
        
        if wikipedia_data:
            with st.expander("Show Wikipedia JSON Data"):
                st.json(wikipedia_data)
        else:
            st.info("Wikipedia data not available")
    
    with detail_tabs[6]:
        st.markdown("#### 🔭 Pan-STARRS DR2 Image Search")
        st.info("Testing visual survey search integration - fetches actual images from Pan-STARRS archive")
        
        # Get position for search - try to get real ephemeris position
        test_ra = None
        test_dec = None
        position_source = "test"
        
        # Date selection for ephemeris
        col_date1, col_date2 = st.columns([3, 1])
        with col_date1:
            from datetime import datetime, date
            # Default to a good Pan-STARRS date (2015 was peak survey year)
            default_date = date(2015, 6, 1)
            search_date = st.date_input(
                "Search date (Pan-STARRS survey: 2009-2024)",
                value=default_date,
                min_value=date(2000, 1, 1),
                max_value=date(2024, 12, 31),
                help="Choose a date to get object's position. Pan-STARRS data available 2009-2024. Default: 2015-06-01 (peak survey year)"
            )
        with col_date2:
            if st.button("🔄 Update Position", use_container_width=True):
                st.rerun()
        
        # Try to get ephemeris position using JPL Horizons
        try:
            from ephemeris_generator import EphemerisGenerator
            
            with st.spinner("Getting position from JPL Horizons..."):
                ephem_gen = EphemerisGenerator()
                
                # Generate ephemeris for selected date
                # Note: Horizons requires end_date > start_date, so add 1 day
                from datetime import timedelta
                date_str = search_date.strftime('%Y-%m-%d')
                end_date = (search_date + timedelta(days=1)).strftime('%Y-%m-%d')
                
                # Try multiple designation formats for best chance of success
                # Priority: numeric ID > comet formats > full designation > name
                designations_to_try = []
                
                # Handle comets specially (start with P/ or C/ or end with P)
                if 'P/' in designation or 'C/' in designation or designation.endswith('P'):
                    # For periodic comets like "67P" or "67P/Name"
                    if designation.split('/')[0].replace('P','').replace('C','').isdigit():
                        comet_num = designation.split('/')[0]
                        designations_to_try.append(f"DES={comet_num};")
                    # Try the designation as-is (might have proper format)
                    designations_to_try.append(designation)
                # Handle asteroids
                elif designation.split()[0].isdigit():
                    # Extract numeric ID if available (e.g., "433" from "433 Eros")
                    numeric_id = designation.split()[0]
                    designations_to_try.append(numeric_id)
                    designations_to_try.append(designation)
                else:
                    # Try the full designation
                    designations_to_try.append(designation)
                
                # Try extracting name from JPL data
                if jpl_data and 'object' in jpl_data:
                    obj_name = jpl_data['object'].get('fullname', '')
                    if obj_name and obj_name not in designations_to_try:
                        designations_to_try.append(obj_name)
                
                # Try each designation until one works
                for idx, des in enumerate(designations_to_try):
                    if idx > 0:
                        st.info(f"Retrying with: {des}...")
                    
                    ephemeris = ephem_gen.generate(
                        designation=des,
                        start_date=date_str,
                        end_date=end_date,  # Must be after start_date
                        step='1d'
                    )
                    
                    if ephemeris:
                        break  # Success!
                
                if ephemeris and len(ephemeris) > 0:
                    test_ra = ephemeris[0]['ra']
                    test_dec = ephemeris[0]['dec']
                    vmag = ephemeris[0].get('vmag', 'N/A')
                    position_source = "horizons"
                    st.success(f"✓ Position on {date_str}: RA={test_ra:.4f}°, Dec={test_dec:.4f}°, Vmag={vmag}")
                    
                    # Check if position is likely in Pan-STARRS coverage
                    if test_dec < -30:
                        st.warning(f"⚠️ Object at Dec={test_dec:.1f}° (southern sky, outside Pan-STARRS coverage)")
                        st.info("💡 Try a different date when object was in northern sky (Dec > -30°)")
                else:
                    st.warning("⚠️ Could not get current position from Horizons, using test coordinates")
                    test_ra = 45.0
                    test_dec = 15.0
        except Exception as e:
            st.warning(f"⚠️ Could not get ephemeris")
            with st.expander("Show error details"):
                st.code(str(e))
                import traceback
                st.code(traceback.format_exc())
            st.info("Using test coordinates instead. Note: Test coordinates are random sky positions and won't have object images.")
            test_ra = 45.0
            test_dec = 15.0
        
        # Default cutout size
        cutout_size = 240.0
        
        # User can override position and cutout size
        with st.expander("🎯 Override Test Position & Size"):
            col1, col2, col3 = st.columns(3)
            with col1:
                test_ra = st.number_input("RA (degrees)", value=test_ra, min_value=0.0, max_value=360.0, format="%.4f")
            with col2:
                test_dec = st.number_input("Dec (degrees)", value=test_dec, min_value=-90.0, max_value=90.0, format="%.4f")
            with col3:
                cutout_size = st.number_input("Size (arcsec)", value=cutout_size, min_value=30.0, max_value=600.0, step=30.0, 
                                            help="Cutout size in arcseconds. 240\" ≈ 4 arcmin")
        
        # Search mode selection
        search_mode = st.radio(
            "Search Mode:",
            ["Single Image", "Blink Comparator (10 frames)", "Difference Imaging"],
            horizontal=True,
            help="Single: One image. Blink: Animated GIF. Difference: Subtract two epochs to isolate moving object"
        )
        
        # Mode-specific info
        if search_mode == "Blink Comparator (10 frames)":
            st.info("💡 **TRUE Blink Comparator:** Uses FIXED star field with REAL multi-epoch observations. " +
                   "Watch the asteroid move naturally through a consistent star field!")
            st.caption("ℹ️ Note: Grid lines visible in some frames are Pan-STARRS skycell boundaries (normal processing artifact)")
        elif search_mode == "Difference Imaging":
            st.info("🔬 **Modern Asteroid Detection:** Subtracts two epochs to isolate moving objects. " +
                   "Stars cancel out, asteroid appears as bright/dark pair!")
            st.caption("✨ This is how Pan-STARRS, ZTF, and other surveys actually detect asteroids!")
        
        # Test button
        if st.button("🔍 Search Pan-STARRS", type="primary"):
            st.markdown("---")
            
            # Check which mode
            if search_mode == "Blink Comparator (10 frames)":
                # TRUE Blink comparator mode - fixed star field with real multi-epoch observations!
                st.markdown("### 🎬 Creating TRUE Blink Comparator Animation")
                st.info("🔭 Fetching REAL multi-epoch observations at FIXED sky position. This may take 1-2 minutes...")
                st.caption("💡 Stars stay fixed, asteroid moves naturally through real observations from different dates!")
                
                try:
                    from blink_comparator import BlinkComparator
                    
                    with st.spinner("Querying Pan-STARRS warp images..."):
                        blink = BlinkComparator()
                        
                        gif_bytes = blink.create_true_blink_animation(
                            designation=designation,
                            start_date=search_date.strftime('%Y-%m-%d'),
                            num_frames=10,  # Will use best available observations
                            band='i',  # i-band for blink
                            size=cutout_size
                        )
                        
                        if gif_bytes:
                            st.success("✓ TRUE Blink Comparator Created!")
                            
                            # Display the animated GIF
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.image(gif_bytes, caption="TRUE Blink Comparator - Fixed Star Field, Multi-Epoch Observations")
                                st.caption("⭐ **REAL observations** from different dates at FIXED sky position - watch asteroid move!")
                            
                            with col2:
                                st.markdown("**Animation Type:**")
                                st.success("✓ FIXED STAR FIELD BLINK")
                                st.write(f"• Object: {designation}")
                                st.write(f"• Reference: {search_date.strftime('%Y-%m-%d')}")
                                st.write(f"• Frames: Multi-epoch observations")
                                st.write(f"• Band: i")
                                st.write(f"• Size: {cutout_size}\"")
                                st.markdown("---")
                                st.markdown("**What you're seeing:**")
                                st.caption("✓ FIXED sky position (same stars)")
                                st.caption("✓ REAL observations from different dates")
                                st.caption("✓ Asteroid moves naturally")
                                st.caption("✓ Same skycell (minimal grid changes)")
                                st.caption("✓ Stars perfectly aligned")
                                st.markdown("---")
                                st.markdown("**How to spot asteroid:**")
                                st.caption("👁️ Stars stay perfectly still")
                                st.caption("🚀 Moving object = asteroid!")
                                st.caption("⚡ Watch for position changes")
                                
                                # Download button
                                st.download_button(
                                    label="💾 Download Animation",
                                    data=gif_bytes,
                                    file_name=f"blink_true_{designation.replace(' ', '_')}.gif",
                                    mime="image/gif",
                                    use_container_width=True
                                )
                        else:
                            st.error("❌ Failed to create animation - not enough multi-epoch observations at this position")
                            st.info("💡 Try a different date or object. Best results with objects in Pan-STARRS survey region (Dec > -30°) during 2010-2014")
                            
                except Exception as e:
                    st.error(f"❌ Error creating animation: {str(e)}")
                    with st.expander("Show error details"):
                        import traceback
                        st.code(traceback.format_exc())
            
            elif search_mode == "Difference Imaging":
                # Difference imaging mode - subtract two epochs
                st.markdown("### 🔬 Creating Difference Image")
                st.info("🔭 Subtracting two epochs to isolate moving object. This may take 30-60 seconds...")
                st.caption("💡 Modern technique: Stars cancel out, asteroid appears as bright/dark pair!")
                
                try:
                    from image_difference import ImageDifferencer
                    from surveys.panstarrs import PanSTARRSClient
                    
                    with st.spinner("Querying available observations..."):
                        ps_client = PanSTARRSClient()
                        
                        # Get warp images at object position
                        warp_files = ps_client.get_file_list(test_ra, test_dec, image_type='warp')
                        
                        if not warp_files:
                            st.error("❌ No warp images found at this position")
                        else:
                            # Filter for i-band
                            i_warps = [w for w in warp_files if w['filter'] == 'i']
                            if not i_warps:
                                st.error("❌ No i-band images found")
                            elif len(i_warps) < 2:
                                st.error("❌ Need at least 2 epochs for differencing")
                            else:
                                i_warps.sort(key=lambda x: x['mjd'])
                                
                                st.success(f"✓ Found {len(i_warps)} i-band observations")
                                
                                # Select two epochs with good separation
                                ref_warp = i_warps[0]
                                new_warp = i_warps[len(i_warps)//2]  # Middle epoch
                                
                                from datetime import datetime, timedelta
                                mjd_epoch = datetime(1858, 11, 17)
                                ref_date = mjd_epoch + timedelta(days=ref_warp['mjd'])
                                new_date = mjd_epoch + timedelta(days=new_warp['mjd'])
                                
                                st.write(f"**Selected epochs:**")
                                st.write(f"  • Reference: {ref_date.strftime('%Y-%m-%d')}")
                                st.write(f"  • New: {new_date.strftime('%Y-%m-%d')}")
                                st.write(f"  • Separation: {(new_date-ref_date).days} days")
                                
                                with st.spinner("Creating difference image..."):
                                    differ = ImageDifferencer()
                                    result = differ.create_difference_image(
                                        ra=test_ra,
                                        dec=test_dec,
                                        filename1=ref_warp['filename'],
                                        filename2=new_warp['filename'],
                                        size=cutout_size
                                    )
                                    
                                    if result:
                                        st.success("✓ Difference Image Created!")
                                        
                                        # Display results
                                        col1, col2, col3 = st.columns(3)
                                        
                                        with col1:
                                            st.image(result['im1_vis'], caption=f"Reference\n{ref_date.strftime('%Y-%m-%d')}")
                                        
                                        with col2:
                                            st.image(result['im2_vis'], caption=f"New\n{new_date.strftime('%Y-%m-%d')}")
                                        
                                        with col3:
                                            st.image(result['diff_vis'], caption="Difference\n(New - Reference)")
                                        
                                        st.markdown("---")
                                        st.markdown("### 📊 Difference Image Analysis")
                                        
                                        col_a, col_b = st.columns([2, 1])
                                        
                                        with col_a:
                                            st.image(result['diff_vis'], caption="Difference Image (Enhanced)", use_container_width=True)
                                            st.caption("🔵 **Blue** = object was here (reference). 🔴 **Red** = object is here now (new)")
                                            st.caption("⭐ Stars cancel out. 🚀 Moving objects appear as blue/red pairs!")
                                        
                                        with col_b:
                                            st.markdown("**Statistics:**")
                                            diff_data = result['diff']
                                            st.write(f"• Mean: {np.mean(diff_data):.2f}")
                                            st.write(f"• Std: {np.std(diff_data):.2f}")
                                            st.write(f"• Min: {np.min(diff_data):.2f}")
                                            st.write(f"• Max: {np.max(diff_data):.2f}")
                                            
                                            st.markdown("---")
                                            st.markdown("**Technique:**")
                                            st.caption("✓ Subtract pixel-by-pixel")
                                            st.caption("✓ Stars align perfectly")
                                            st.caption("✓ Background cancels")
                                            st.caption("✓ Moving object revealed!")
                                            
                                            # Download FITS
                                            from astropy.io import fits
                                            fits_io = BytesIO()
                                            hdu = fits.PrimaryHDU(result['diff'])
                                            hdu.writeto(fits_io)
                                            
                                            st.download_button(
                                                label="💾 Download FITS",
                                                data=fits_io.getvalue(),
                                                file_name=f"diff_{designation.replace(' ', '_')}.fits",
                                                mime="application/fits",
                                                use_container_width=True
                                            )
                                    else:
                                        st.error("❌ Failed to create difference image")
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    with st.expander("Show error details"):
                        import traceback
                        st.code(traceback.format_exc())
            
            else:
                # Single image mode
                try:
                    # Import survey client
                    from surveys import get_survey_client
                    
                    with st.spinner("Initializing Pan-STARRS client..."):
                        ps_client = get_survey_client('panstarrs')
                        
                        if ps_client is None:
                            st.error("❌ Pan-STARRS client could not be initialized")
                            st.info("Check that surveys/ directory and modules are properly installed")
                        else:
                            st.success(f"✓ Client initialized: {ps_client.name}")
                            
                            # Show client info
                            with st.expander("📋 Survey Information"):
                                st.write(f"**Name:** {ps_client.name}")
                                st.write(f"**Coverage:** δ > -30° (3/4 of sky)")
                                st.write(f"**Limiting Magnitude:** {ps_client.limiting_magnitude} mag")
                                st.write(f"**Bands:** {', '.join(ps_client.bands)}")
                                st.write(f"**Years:** {ps_client.years[0]}-{ps_client.years[1]}")
                                st.write(f"**Priority:** {ps_client.priority}/5")
                    
                    # Check coverage
                    with st.spinner("Checking footprint coverage..."):
                        in_footprint = ps_client.check_coverage(test_ra, test_dec)
                        
                        if in_footprint:
                            st.success(f"✓ Position (RA={test_ra:.4f}°, Dec={test_dec:.4f}°) is within Pan-STARRS footprint")
                        else:
                            st.warning(f"⚠️ Position (RA={test_ra:.4f}°, Dec={test_dec:.4f}°) is outside Pan-STARRS coverage")
                            st.info("Pan-STARRS covers most of the sky north of Dec = -30°")
                    
                    # Try to fetch images
                    if in_footprint:
                        st.markdown("#### 📸 Fetching Images")
                        
                        # Try multiple bands
                        bands_to_try = ['r', 'g', 'i']
                        
                        for band in bands_to_try:
                            with st.spinner(f"Requesting {band}-band cutout..."):
                                try:
                                    cutout = ps_client.get_cutout(
                                        ra=test_ra,
                                        dec=test_dec,
                                        size=cutout_size,
                                        band=band
                                    )
                                    
                                    if cutout:
                                        st.success(f"✓ {band}-band image retrieved!")
                                        
                                        # Display image
                                        col1, col2 = st.columns([2, 1])
                                        with col1:
                                            # Use PIL image if available, fall back to URL
                                            if 'image_pil' in cutout:
                                                st.image(cutout['image_pil'], 
                                                        caption=f"Pan-STARRS {band}-band ({cutout['size_arcsec']:.0f}\" cutout)",
                                                        use_container_width=True)
                                            else:
                                                st.image(cutout['image_url'], 
                                                        caption=f"Pan-STARRS {band}-band ({cutout['size_arcsec']:.0f}\" cutout)",
                                                        use_container_width=True)
                                            
                                            # Add target identification help
                                            st.caption("🎯 **Red dashed circle** marks expected object position")
                                        
                                        with col2:
                                            st.markdown("**Image Details:**")
                                            st.write(f"• Filter: {cutout['filter']}")
                                            st.write(f"• RA: {cutout['ra']:.4f}°")
                                            st.write(f"• Dec: {cutout['dec']:.4f}°")
                                            st.write(f"• Size: {cutout['size_arcsec']}\"")
                                            st.write(f"• Pixel scale: {cutout['pixel_scale']}\"/px")
                                            
                                            st.markdown("---")
                                            st.markdown("**Target Info:**")
                                            if ephemeris and len(ephemeris) > 0:
                                                vmag = ephemeris[0].get('vmag')
                                                if vmag:
                                                    st.write(f"• Expected mag: **{vmag:.1f}**")
                                                    # Provide context
                                                    if vmag < 14:
                                                        st.caption("✓ Should be visible")
                                                    elif vmag < 18:
                                                        st.caption("⚠️ Faint, look carefully")
                                                    else:
                                                        st.caption("⚠️ Very faint")
                                            st.caption("Look for object at center (red circle)")
                                            
                                            # Download button
                                            if 'image_data' in cutout:
                                                filename = f"panstarrs_{band}_{designation.replace(' ', '_')}_ra{cutout['ra']:.2f}_dec{cutout['dec']:.2f}.jpg"
                                                st.download_button(
                                                    label=f"💾 Download {band}-band",
                                                    data=cutout['image_data'],
                                                    file_name=filename,
                                                    mime="image/jpeg",
                                                    use_container_width=True,
                                                    key=f"download_{band}"
                                                )
                                            
                                            # Link to full resolution
                                            st.link_button(
                                                label=f"🔗 View on STScI",
                                                url=cutout['image_url'],
                                                use_container_width=True
                                            )
                                        
                                        st.markdown("---")
                                        
                                    else:
                                        st.warning(f"⚠️ No {band}-band image available at this position")
                                        
                                except Exception as e:
                                    st.error(f"❌ Error fetching {band}-band: {str(e)}")
                                    with st.expander("Show error details"):
                                        st.code(str(e))
                        
                        st.markdown("---")
                        st.success("✓ Pan-STARRS integration test complete!")
                        st.info("💡 **Next step:** Full Visual Survey Search tab with ephemeris generation and multi-survey support coming soon!")
                    
                except ImportError as e:
                    st.error("❌ Survey modules not found")
                    st.code(str(e))
                    st.info("Make sure the surveys/ directory is in the project root")
                except Exception as e:
                    st.error(f"❌ Unexpected error: {str(e)}")
                    with st.expander("Show full error"):
                        import traceback
                        st.code(traceback.format_exc())
        
        else:
            st.markdown("---")
            st.info("👆 Click the button above to test Pan-STARRS image retrieval")
            st.markdown("""
            **What this test does:**
            1. Gets object's current position from JPL Horizons
            2. Initializes Pan-STARRS client
            3. Checks if position is in survey footprint (δ > -30°)
            4. Requests image cutouts in r, g, and i bands
            5. Displays images and metadata
            
            **Status:**
            - ✅ Pan-STARRS client implemented
            - ✅ Ephemeris generation integrated
            - ✅ Real-time position lookup
            - 📋 Multi-timeframe search coming soon
            
            **Note:** Pan-STARRS covers most of the sky with δ > -30°. Objects currently 
            in the southern sky (or that were faint during survey years 2009-2024) may 
            not have images available.
            """)

    # ── 3D Model Tab ─────────────────────────────────────────────────
    with detail_tabs[7]:
        st.markdown("#### 🧊 3D Shape Model")

        spec_class = (obj_data.get('Spectral Type (Bus)')
                      or obj_data.get('spec_B')
                      or obj_data.get('Spectral Type (Tholen)')
                      or obj_data.get('spec_T')
                      or '')
        if not spec_class and ssodnet_data:
            phys = ssodnet_data.get('parameters', {}).get('physical', {})
            tax = phys.get('taxonomy', {})
            if isinstance(tax, dict):
                spec_class = tax.get('class', '')

        obj_albedo = obj_data.get('Albedo') or obj_data.get('albedo')
        if not obj_albedo and ssodnet_data:
            phys = ssodnet_data.get('parameters', {}).get('physical', {})
            alb = phys.get('albedo', {})
            if isinstance(alb, dict):
                obj_albedo = alb.get('value')

        model_designation = designation
        model_data = None

        with st.spinner("Searching for 3D shape model..."):
            try:
                resp = requests.get(
                    f"{BACKEND_URL}/api/objects/{model_designation}/model",
                    timeout=60
                )
                if resp.status_code == 200:
                    model_data = resp.json()
            except Exception as e:
                st.error(f"Could not reach model API: {e}")

        if model_data and model_data.get('has_model'):
            model_type = model_data.get('type', '')
            source = model_data.get('source', 'Unknown')
            st.success(f"Model found from **{source}**")

            if model_type == 'texture':
                tex_url = model_data.get('texture_url', '')
                body_name = model_data.get('name', designation)
                st.markdown(f"**Equirectangular texture map** for {body_name.capitalize()}")
                if tex_url:
                    st.image(tex_url, caption=f"{body_name.capitalize()} surface texture (Solar System Scope, CC-BY-4.0)", use_container_width=True)

                    st.markdown("**Interactive 3D Globe**")
                    try:
                        import numpy as np
                        theta = np.linspace(0, 2 * np.pi, 60)
                        phi = np.linspace(0, np.pi, 30)
                        theta_grid, phi_grid = np.meshgrid(theta, phi)
                        x = np.sin(phi_grid) * np.cos(theta_grid)
                        y = np.sin(phi_grid) * np.sin(theta_grid)
                        z = np.cos(phi_grid)
                        fig = go.Figure(data=[go.Surface(
                            x=x, y=y, z=z,
                            colorscale='gray',
                            showscale=False,
                            lighting=dict(ambient=0.6, diffuse=0.5, specular=0.2),
                            lightposition=dict(x=100, y=200, z=300),
                        )])
                        fig.update_layout(
                            scene=dict(
                                aspectmode='data',
                                bgcolor='#0e1117',
                                xaxis=dict(visible=False),
                                yaxis=dict(visible=False),
                                zaxis=dict(visible=False),
                            ),
                            margin=dict(l=0, r=0, t=30, b=0),
                            height=500,
                            title=f"{body_name.capitalize()} (rotate with mouse)"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Could not render 3D globe: {e}")

                    st.caption("Texture: [Solar System Scope](https://www.solarsystemscope.com/textures/) (CC-BY-4.0)")

            elif model_type == 'obj':
                obj_url = model_data.get('obj_url', '')
                meta = model_data.get('metadata', {})
                source_url = model_data.get('source_url', '')
                verts = meta.get('vertices', '?')
                faces = meta.get('faces', '?')

                col_info1, col_info2, col_info3 = st.columns(3)
                col_info1.metric("Vertices", f"{verts:,}" if isinstance(verts, int) else str(verts))
                col_info2.metric("Faces", f"{faces:,}" if isinstance(faces, int) else str(faces))
                col_info3.metric("Source", source)

                col_ctrl1, col_ctrl2 = st.columns(2)
                opacity = col_ctrl1.slider("Opacity", 0.3, 1.0, 0.9, 0.05, key="model_opacity")
                color_choice = col_ctrl2.selectbox("Color", [
                    'Spectral', 'gray', 'Viridis', 'Cividis', 'Inferno', 'Magma', 'Earth', 'Ice'
                ], key="model_colorscale")

                if color_choice == 'Spectral':
                    colorscale = spectral_colorscale(spec_class, obj_albedo)
                    spec_label = spec_class if spec_class else 'Unknown'
                    alb_label = str(obj_albedo) if obj_albedo else 'Unknown'
                    st.caption(f"Spectral class: **{spec_label}** | Albedo: **{alb_label}**")
                else:
                    colorscale = color_choice

                obj_bytes = None
                with st.spinner("Loading 3D model..."):
                    try:
                        obj_resp = requests.get(
                            f"{BACKEND_URL}{obj_url}",
                            timeout=30
                        )
                        if obj_resp.status_code == 200:
                            obj_bytes = obj_resp.content
                            import trimesh
                            from io import BytesIO
                            mesh = trimesh.load(
                                BytesIO(obj_bytes),
                                file_type='obj', process=True
                            )

                            fig = go.Figure(data=[go.Mesh3d(
                                x=mesh.vertices[:, 0],
                                y=mesh.vertices[:, 1],
                                z=mesh.vertices[:, 2],
                                i=mesh.faces[:, 0],
                                j=mesh.faces[:, 1],
                                k=mesh.faces[:, 2],
                                opacity=opacity,
                                colorscale=colorscale,
                                intensity=mesh.vertices[:, 2],
                                lighting=dict(ambient=0.4, diffuse=0.6, specular=0.2, roughness=0.5),
                                lightposition=dict(x=100, y=200, z=300),
                            )])
                            fig.update_layout(
                                scene=dict(
                                    aspectmode='data',
                                    bgcolor='#0e1117',
                                    xaxis=dict(visible=False),
                                    yaxis=dict(visible=False),
                                    zaxis=dict(visible=False),
                                ),
                                margin=dict(l=0, r=0, t=30, b=0),
                                height=600,
                                title=f"{name} — 3D Shape Model (rotate with mouse)"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.error(f"Failed to download OBJ model (HTTP {obj_resp.status_code})")
                    except Exception as e:
                        st.error(f"Error rendering 3D model: {e}")

                if source_url:
                    st.caption(f"Source: [{source}]({source_url})")

                if obj_bytes:
                    st.download_button(
                        "Download OBJ file",
                        data=obj_bytes,
                        file_name=f"{designation}.obj",
                        mime="text/plain",
                    )

        elif model_data and not model_data.get('has_model'):
            st.info(f"No 3D shape model found for **{name}** ({designation})")
            st.markdown("""
            Not all solar system objects have 3D models. Models are available for:
            - **~1,600 asteroids** from [3d-asteroids.space](https://3d-asteroids.space/)
            - **~2,500 asteroids** from [DAMIT](https://astro.troja.mff.cuni.cz/projects/damit/) (lightcurve inversion)
            - **Major planets and moons** have texture maps

            You can check manually:
            """)
            if designation.isdigit():
                st.markdown(f"- [Search 3d-asteroids.space](https://3d-asteroids.space/asteroids/{designation})")
                st.markdown(f"- [Search DAMIT](https://astro.troja.mff.cuni.cz/projects/damit/asteroids/browse?number={designation})")
        else:
            st.warning("Could not check for 3D models. Is the backend running?")

    # ── Images Tab ──────────────────────────────────────────────────────
    with detail_tabs[8]:
        st.markdown("#### 🖼️ Multi-Source Image Search")

        spkid_display = None
        if jpl_data and 'object' in jpl_data:
            spkid_display = jpl_data['object'].get('spkid')
        st.markdown(
            f"**Designation:** `{designation}`"
            + (f"  |  **SPK ID:** `{spkid_display}`" if spkid_display else "")
        )
        st.caption(
            "Searches IRSA MOST (WISE/NEOWISE, ZTF), CATCH (NEAT, Catalina, ATLAS, …), "
            "and Wikipedia for images linked to this object."
        )

        source_filter = st.multiselect(
            "Sources to search",
            ["WISE/NEOWISE", "ZTF", "CATCH (surveys)", "Wikipedia"],
            default=["WISE/NEOWISE", "ZTF", "CATCH (surveys)", "Wikipedia"],
            key=f"img_sources_{designation}",
        )

        img_state_key = f"img_results_{designation}"

        if st.button("🔍 Search All Image Archives", type="primary", key=f"img_search_{designation}"):
            source_map = {
                "WISE/NEOWISE": "wise",
                "ZTF": "ztf",
                "CATCH (surveys)": "catch",
                "Wikipedia": "wikipedia",
            }
            active_sources = [source_map[s] for s in source_filter if s in source_map]

            all_images = []
            source_meta = {}
            resolved = None

            progress_bar = st.progress(0, text="Starting image search…")
            status_area = st.empty()

            for step, src_key in enumerate(active_sources):
                frac = (step) / len(active_sources)
                label_map = {
                    'wise': 'WISE/NEOWISE (IRSA)',
                    'ztf': 'ZTF (IRSA)',
                    'catch': 'CATCH (multi-survey)',
                    'wikipedia': 'Wikipedia',
                }
                progress_bar.progress(frac, text=f"Querying {label_map.get(src_key, src_key)}…")

                try:
                    resp = requests.get(
                        f"{BACKEND_URL}/api/objects/{designation}/images",
                        params={'sources': src_key},
                        timeout=120,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        all_images.extend(data.get('images', []))
                        for k, v in data.get('sources', {}).items():
                            source_meta[k] = v
                        if resolved is None:
                            resolved = data.get('resolved')
                except Exception as e:
                    status_area.warning(f"Error querying {src_key}: {e}")

            progress_bar.progress(1.0, text="Search complete")

            st.session_state[img_state_key] = {
                'images': all_images,
                'source_meta': source_meta,
                'resolved': resolved,
            }

        cached = st.session_state.get(img_state_key)

        if cached:
            all_images = cached['images']
            source_meta = cached['source_meta']
            resolved = cached.get('resolved')

            if not all_images and not source_meta:
                st.info("No images found across the selected archives.")
            else:
                total_count = sum(v.get('count', 0) for v in source_meta.values())
                st.success(f"Found **{total_count}** image records across **{len(source_meta)}** sources")

                cols_metric = st.columns(max(len(source_meta), 1))
                for col, (sk, sv) in zip(cols_metric, source_meta.items()):
                    col.metric(sv.get('name', sk), sv.get('count', 0))

                if resolved:
                    with st.expander("🔗 Resolved Object Identifiers"):
                        id_cols = st.columns(4)
                        id_cols[0].code(f"SPK ID: {resolved.get('spkid', '?')}")
                        id_cols[1].code(f"Designation: {resolved.get('des', '?')}")
                        id_cols[2].code(f"Full name: {resolved.get('fullname', '?')}")
                        alt = resolved.get('alt_des', [])
                        id_cols[3].code(f"Aliases: {', '.join(alt) if alt else 'none'}")

                from collections import defaultdict
                by_source = defaultdict(list)
                for img in all_images:
                    by_source[img.get('source', 'Unknown')].append(img)

                for source_name, imgs in by_source.items():
                    date_range = ""
                    dates = [im.get('date', '') for im in imgs if im.get('date')]
                    if dates:
                        dates_sorted = sorted(d for d in dates if d)
                        if dates_sorted:
                            date_range = f" ({dates_sorted[0]} → {dates_sorted[-1]})"
                    with st.expander(f"**{source_name}** — {len(imgs)} record(s){date_range}", expanded=(len(imgs) <= 20)):
                        if source_name == 'Wikipedia':
                            wiki_cols = st.columns(min(len(imgs), 4))
                            for idx, img in enumerate(imgs[:12]):
                                url = img.get('image_url', '')
                                cap = img.get('caption', '') or img.get('title', '')
                                if url:
                                    with wiki_cols[idx % len(wiki_cols)]:
                                        st.image(url, caption=cap[:60], use_container_width=True)
                        else:
                            if not imgs:
                                st.info("No observations found.")
                                continue

                            safe_src = source_name.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '')

                            table_rows = []
                            for i, im in enumerate(imgs):
                                table_rows.append({
                                    '#': i + 1,
                                    'Date': im.get('date', ''),
                                    'Band': im.get('band', ''),
                                    'RA': im.get('ra', ''),
                                    'Dec': im.get('dec', ''),
                                    'V mag': im.get('vmag', ''),
                                    'Phase (°)': im.get('phase', ''),
                                    'Sun (AU)': im.get('sun_dist', ''),
                                    'Geo (AU)': im.get('geo_dist', ''),
                                    'Offset (″)': im.get('dist_arcsec', ''),
                                })

                            df = pd.DataFrame(table_rows)

                            st.markdown(f"**{len(imgs)}** observations — select a row to view the image")

                            selected = st.dataframe(
                                df,
                                use_container_width=True,
                                hide_index=True,
                                on_select="rerun",
                                selection_mode="single-row",
                                key=f"img_table_{designation}_{safe_src}",
                            )

                            sel_rows = selected.get("selection", {}).get("rows", []) if selected else []

                            if sel_rows:
                                row_idx = sel_rows[0]
                                sel_im = imgs[row_idx]
                                sel_ra = sel_im.get('ra', '')
                                sel_dec = sel_im.get('dec', '')
                                sel_date = sel_im.get('date', '')
                                sel_band = sel_im.get('band', '')
                                sel_time = sel_im.get('time', '')

                                st.markdown("---")
                                st.markdown(f"##### Observation #{row_idx + 1}: {sel_date} {sel_time}  —  {sel_band}")

                                info_cols = st.columns(5)
                                info_cols[0].metric("RA", f"{sel_ra}")
                                info_cols[1].metric("Dec", f"{sel_dec}")
                                info_cols[2].metric("V mag", sel_im.get('vmag', '?'))
                                info_cols[3].metric("Phase", f"{sel_im.get('phase', '?')}°")
                                info_cols[4].metric("Offset", f"{sel_im.get('dist_arcsec', '?')}″")

                                try:
                                    ra_f = float(sel_ra)
                                    dec_f = float(sel_dec)
                                except (ValueError, TypeError):
                                    ra_f, dec_f = None, None

                                if ra_f is None:
                                    st.info("No viewable image — RA/Dec not available for this observation.")
                                else:
                                    @st.cache_data(ttl=3600, show_spinner=False)
                                    def _fetch_panstarrs(ra, dec, size=240, out=512):
                                        try:
                                            fn_r = requests.get(
                                                f"https://ps1images.stsci.edu/cgi-bin/ps1filenames.py"
                                                f"?ra={ra}&dec={dec}&filters=i&type=stack",
                                                timeout=15,
                                            )
                                            lines = fn_r.text.strip().split('\n')
                                            if len(lines) < 2:
                                                return None
                                            fname = lines[1].split()[7]
                                            img_r = requests.get(
                                                f"https://ps1images.stsci.edu/cgi-bin/fitscut.cgi"
                                                f"?red={fname}&ra={ra}&dec={dec}"
                                                f"&size={size}&format=jpg&output_size={out}",
                                                timeout=30,
                                            )
                                            if img_r.status_code == 200 and img_r.headers.get('Content-Type', '').startswith('image/'):
                                                return img_r.content
                                        except Exception:
                                            pass
                                        return None

                                    @st.cache_data(ttl=3600, show_spinner=False)
                                    def _fetch_dss2(ra, dec, fov=0.15):
                                        try:
                                            r = requests.get(
                                                f"https://alasky.cds.unistra.fr/hips-image-services/hips2fits"
                                                f"?hips=CDS/P/DSS2/color&width=512&height=512"
                                                f"&fov={fov}&projection=TAN"
                                                f"&ra={ra}&dec={dec}&format=jpg",
                                                timeout=30,
                                            )
                                            if r.status_code == 200 and r.headers.get('Content-Type', '').startswith('image/'):
                                                return r.content
                                        except Exception:
                                            pass
                                        return None

                                    img_bytes = None
                                    img_label = None

                                    with st.spinner("Loading sky image…"):
                                        if dec_f > -30:
                                            img_bytes = _fetch_panstarrs(ra_f, dec_f)
                                            if img_bytes:
                                                img_label = f"Pan-STARRS i-band at RA={ra_f:.4f} Dec={dec_f:.4f}"

                                        if img_bytes is None:
                                            img_bytes = _fetch_dss2(ra_f, dec_f)
                                            if img_bytes:
                                                img_label = f"DSS2 color at RA={ra_f:.4f} Dec={dec_f:.4f}"

                                    if img_bytes:
                                        view_cols = st.columns([2, 1])
                                        with view_cols[0]:
                                            st.image(img_bytes, caption=img_label, use_container_width=True)
                                        with view_cols[1]:
                                            st.markdown("**Sky position at observation time**")
                                            st.markdown(f"- **RA:** {ra_f:.6f}°")
                                            st.markdown(f"- **Dec:** {dec_f:.6f}°")
                                            st.markdown(f"- **Sun dist:** {sel_im.get('sun_dist', '?')} AU")
                                            st.markdown(f"- **Geo dist:** {sel_im.get('geo_dist', '?')} AU")
                                            survey = "Pan-STARRS" if "Pan-STARRS" in img_label else "DSS2"
                                            st.caption(f"{survey} stacked image at this sky position. "
                                                       "The asteroid may not be visible in the stack "
                                                       "(it moves between exposures).")
                                    else:
                                        st.warning("Could not load a sky image for this position.")

                                if ra_f is not None:
                                    link_cols = st.columns(3)
                                    link_cols[0].link_button(
                                        "🔭 View in Aladin Lite",
                                        f"https://aladin.cds.unistra.fr/AladinLite/?target={ra_f}+{dec_f}&fov=0.15",
                                        use_container_width=True,
                                    )
                                    link_cols[1].link_button(
                                        "🌐 View in WorldWide Telescope",
                                        f"https://worldwidetelescope.org/webclient/#ra={ra_f/15:.6f}&dec={dec_f:.6f}&fov=0.15",
                                        use_container_width=True,
                                    )
                                    link_cols[2].link_button(
                                        "📡 IRSA Finder Chart",
                                        f"https://irsa.ipac.caltech.edu/applications/finderchart/#id=Hydra_finderchart_finderchart&RequestClass=ServerRequest&DoSearch=true&subsize=0.08333333&RA={ra_f}&DEC={dec_f}",
                                        use_container_width=True,
                                    )
                            else:
                                st.info("👆 Click a row in the table above to view the sky image at that observation's position.")

                            st.caption(f"Query: object name `{designation}` via "
                                       f"{'IRSA MOST' if 'IRSA' in source_name else 'CATCH API'}")

        else:
            st.markdown("""
            Click **Search All Image Archives** to query:

            | Source | Index Method | Surveys |
            |---|---|---|
            | **IRSA MOST** | Object name / NAIF ID | WISE, NEOWISE, ZTF, PTF, 2MASS, Spitzer |
            | **CATCH** | Target designation | NEAT, Catalina, LONEOS, ATLAS, SkyMapper |
            | **Wikipedia** | Article title | Curated article images |

            The search resolves your object's designation via **JPL SBDB** to get the SPK ID
            and all known aliases, then queries each archive with the appropriate identifier.
            """)

    # ── Community Tab ──────────────────────────────────────────────────
    with detail_tabs[9]:
        st.markdown("#### 🛰 Community Knowledge Base")
        st.caption(f"Object: `{designation}`")

        sb = get_supabase()
        entity = st.session_state.get("entity")

        comm_tabs = st.tabs([
            "💬 Discussion",
            "🔭 Observations",
            "📝 Corrections",
            "🚀 Mission Reports"
        ])

        # ── Discussion sub-tab ──
        with comm_tabs[0]:
            _render_dialogue(designation, "comment", "comment", sb, entity)

        # ── Observations sub-tab ──
        with comm_tabs[1]:
            if sb and entity:
                with st.form(key=f"obs_form_{designation}"):
                    st.markdown("**Report an Observation**")
                    obs_cols = st.columns(3)
                    obs_date = obs_cols[0].date_input("Date", key=f"obs_date_{designation}")
                    obs_telescope = obs_cols[1].text_input("Telescope", key=f"obs_tel_{designation}")
                    obs_mag = obs_cols[2].text_input("Magnitude", key=f"obs_mag_{designation}")
                    obs_cols2 = st.columns(3)
                    obs_filter = obs_cols2[0].text_input("Filter/Band", key=f"obs_filt_{designation}")
                    obs_seeing = obs_cols2[1].text_input("Seeing (arcsec)", key=f"obs_see_{designation}")
                    obs_location = obs_cols2[2].text_input("Location", key=f"obs_loc_{designation}")
                    obs_notes = st.text_area("Notes", key=f"obs_notes_{designation}")

                    if st.form_submit_button("Submit Observation"):
                        profile = st.session_state.get("entity_profile", {})
                        structured = {
                            "obs_date": str(obs_date),
                            "telescope": obs_telescope,
                            "magnitude": obs_mag,
                            "filter": obs_filter,
                            "seeing_arcsec": obs_seeing,
                            "location": obs_location,
                        }
                        try:
                            sb.table("contributions").insert({
                                "object_designation": designation,
                                "entity_id": str(entity.id),
                                "entity_name": profile.get("display_name", entity.email),
                                "kind": "observation",
                                "body": obs_notes,
                                "structured_data": structured,
                            }).execute()
                            st.success("Observation recorded.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {str(e)[:80]}")

            st.markdown("##### Observation Dialogue")
            _render_dialogue(designation, "observation", "observation", sb, entity)

        # ── Corrections sub-tab ──
        with comm_tabs[2]:
            if sb and entity:
                with st.form(key=f"corr_form_{designation}"):
                    st.markdown("**Suggest a Data Correction**")
                    corr_field = st.selectbox("Field", [
                        "diameter", "albedo", "rotation_period", "spectral_type",
                        "mass", "density", "absolute_magnitude", "other"
                    ], key=f"corr_field_{designation}")
                    corr_cols = st.columns(2)
                    corr_current = corr_cols[0].text_input("Current value", key=f"corr_cur_{designation}")
                    corr_suggested = corr_cols[1].text_input("Suggested value", key=f"corr_sug_{designation}")
                    corr_source = st.text_input(
                        "Source reference (DOI, URL, etc.)",
                        key=f"corr_src_{designation}"
                    )
                    corr_justification = st.text_area("Justification", key=f"corr_just_{designation}")

                    if st.form_submit_button("Submit Correction"):
                        if corr_suggested.strip():
                            profile = st.session_state.get("entity_profile", {})
                            try:
                                sb.table("contributions").insert({
                                    "object_designation": designation,
                                    "entity_id": str(entity.id),
                                    "entity_name": profile.get("display_name", entity.email),
                                    "kind": "correction",
                                    "body": corr_justification,
                                    "structured_data": {
                                        "field": corr_field,
                                        "current": corr_current,
                                        "suggested": corr_suggested,
                                    },
                                    "source_references": [corr_source] if corr_source.strip() else [],
                                }).execute()
                                st.success("Correction submitted for review.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {str(e)[:80]}")
                        else:
                            st.warning("Suggested value is required")

            st.markdown("##### Correction Dialogue")
            _render_dialogue(designation, "correction", "correction", sb, entity)

        # ── Mission Reports sub-tab ──
        with comm_tabs[3]:
            if sb:
                try:
                    missions = sb.table("exploration_missions").select("*").eq(
                        "object_designation", designation
                    ).order("started_at", desc=True).limit(20).execute()
                    if missions.data:
                        for m in missions.data:
                            status_map = {
                                "deploying": "🟡 Deploying",
                                "in_transit": "🔵 In Transit",
                                "investigating": "🟠 Investigating",
                                "returning_data": "🔄 Returning Data",
                                "mission_complete": "✅ Mission Complete",
                                "mission_failed": "❌ Mission Failed",
                            }
                            st.markdown(
                                f"**{status_map.get(m.get('status', ''), m.get('status', '?'))}** "
                                f"— requested by {m.get('requested_by_name', '?')} "
                                f"at {(m.get('started_at') or '')[:16]}"
                            )
                            if m.get("findings_summary"):
                                with st.expander("View mission report"):
                                    st.markdown(m["findings_summary"])
                                    gaps = m.get("data_gaps") or []
                                    if gaps:
                                        st.markdown("**Data gaps identified:** " + ", ".join(gaps))
                                    score = m.get("completeness_score")
                                    if score is not None:
                                        st.metric("Completeness Score", f"{score:.0%}")
                                    sources = m.get("sources_queried") or []
                                    if sources:
                                        st.caption(f"Sources queried: {', '.join(sources)}")
                                    dur = m.get("duration_seconds")
                                    if dur:
                                        st.caption(f"Mission duration: {dur:.1f}s")
                            st.markdown("---")
                    else:
                        st.info("No exploration missions yet for this object.")
                except Exception:
                    st.info("No exploration missions yet for this object.")

            deploy_col1, deploy_col2 = st.columns([2, 1])
            with deploy_col1:
                st.markdown("**Deploy a Robot Explorer** to autonomously investigate this object "
                            "across all available data sources.")
            with deploy_col2:
                can_deploy = entity is not None
                if st.button(
                    f"🚀 Deploy Explorer to {designation}",
                    key=f"deploy_explorer_{designation}",
                    type="primary",
                    disabled=not can_deploy,
                ):
                    profile = st.session_state.get("entity_profile", {})
                    entity_name = profile.get("display_name", entity.email) if entity else "?"

                    mission_id = None
                    if sb:
                        try:
                            m_res = sb.table("exploration_missions").insert({
                                "object_designation": designation,
                                "requested_by": str(entity.id),
                                "requested_by_name": entity_name,
                                "status": "deploying",
                            }).execute()
                            if m_res.data:
                                mission_id = m_res.data[0].get("id")
                        except Exception:
                            pass

                    with st.spinner("🚀 Explorer deployed... investigating..."):
                        try:
                            resp = requests.post(
                                f"{BACKEND_URL}/api/objects/{designation}/explore",
                                timeout=180,
                            )
                            if resp.status_code == 200:
                                report = resp.json()
                                if sb and mission_id:
                                    try:
                                        cont = sb.table("contributions").insert({
                                            "object_designation": designation,
                                            "entity_id": str(entity.id),
                                            "entity_name": f"Explorer (dispatched by {entity_name})",
                                            "kind": "mission_report",
                                            "body": report.get("findings_summary", ""),
                                            "structured_data": report.get("structured_data", {}),
                                            "source_references": report.get("sources_queried", []),
                                        }).execute()
                                        contrib_id = cont.data[0]["id"] if cont.data else None

                                        sb.table("exploration_missions").update({
                                            "status": "mission_complete",
                                            "findings_summary": report.get("findings_summary", ""),
                                            "data_gaps": report.get("data_gaps", []),
                                            "completeness_score": report.get("completeness_score"),
                                            "sources_queried": report.get("sources_queried", []),
                                            "contribution_id": contrib_id,
                                            "duration_seconds": report.get("duration_seconds"),
                                            "completed_at": datetime.utcnow().isoformat(),
                                        }).eq("id", mission_id).execute()

                                        sb.table("entity_profiles").update({
                                            "missions_completed": (profile.get("missions_completed", 0) or 0) + 1
                                        }).eq("id", str(entity.id)).execute()
                                    except Exception:
                                        pass

                                st.success("✅ Explorer has returned. Mission report filed.")
                                st.rerun()
                            else:
                                st.error(f"Explorer mission failed (HTTP {resp.status_code})")
                                if sb and mission_id:
                                    try:
                                        sb.table("exploration_missions").update({
                                            "status": "mission_failed",
                                            "completed_at": datetime.utcnow().isoformat(),
                                        }).eq("id", mission_id).execute()
                                    except Exception:
                                        pass
                        except Exception as e:
                            st.error(f"Explorer lost contact: {str(e)[:80]}")
                            if sb and mission_id:
                                try:
                                    sb.table("exploration_missions").update({
                                        "status": "mission_failed",
                                    }).eq("id", mission_id).execute()
                                except Exception:
                                    pass

                if not can_deploy:
                    st.caption("🔑 Log in to deploy explorers")

            st.markdown("##### Mission Dialogue")
            _render_dialogue(designation, "mission_report", "mission comment", sb, entity)


def objects_to_dataframe(objects):
    """Convert objects list to pandas DataFrame"""
    if not objects:
        return pd.DataFrame()
    
    rows = []
    has_parent = any(obj.get('parent') for obj in objects)
    has_neocp = any(obj.get('type') == 'NEOCP' for obj in objects)
    for obj in objects:
        analysis = obj.get('analysis', {})
        row = {
            'Designation': obj.get('pdes', obj.get('spkid', 'Unknown')),
            'Name': obj.get('name', '-'),
            'Type': obj.get('type', 'NEO' if obj.get('neo') == 'Y' else 'MBA'),
            'PHA': 'Yes' if obj.get('pha') == 'Y' else 'No',
            'H': obj.get('H', None),
            'Diameter (km)': obj.get('diameter', None),
            'Albedo': obj.get('albedo', None),
            'Rotation Period (h)': obj.get('rot_per', None),
            'Spectral Type (Bus)': obj.get('spec_B', None),
            'Spectral Type (Tholen)': obj.get('spec_T', None),
            'Completeness (%)': analysis.get('completeness_score', 0),
            'Priority': analysis.get('research_priority', 'unknown'),
            'Missing Properties': ', '.join(analysis.get('missing_properties', []))
        }
        if has_parent:
            row['Parent'] = obj.get('parent', '-')
        if has_neocp:
            neocp = obj.get('neocp', {})
            row['Score'] = neocp.get('score', '-') if neocp else '-'
            row['V mag'] = neocp.get('V_mag', '-') if neocp else '-'
            row['Obs'] = neocp.get('n_obs', '-') if neocp else '-'
            row['Arc (d)'] = neocp.get('arc_days', '-') if neocp else '-'
        rows.append(row)
    
    return pd.DataFrame(rows)

def get_priority_color(priority):
    """Get color for priority level"""
    colors = {
        'high': '#ff5252',
        'medium': '#ffc107',
        'low': '#4caf50',
        'unknown': '#888888'
    }
    return colors.get(priority, '#888888')

def sync_vr_selection(designations: list, description: str):
    """POST the current filtered object designations to Flask for VR mode 3."""
    try:
        requests.post(
            f"{BACKEND_URL}/api/vr/selection",
            json={"designations": designations, "description": description},
            timeout=2,
        )
    except Exception:
        pass

# ── Entity Authentication Sidebar ──────────────────────────────────
def render_entity_auth_sidebar():
    """Render login/signup/profile in the sidebar. Returns entity dict or None."""
    sb = get_supabase()
    if sb is None:
        st.sidebar.caption("🔒 Auth not configured")
        return None

    if st.session_state.entity is not None:
        profile = st.session_state.entity_profile or {}
        name = profile.get('display_name', st.session_state.entity.email)
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**🛰 {name}**")
        missions = profile.get('missions_completed', 0)
        contribs = profile.get('contribution_count', 0)
        st.sidebar.caption(f"{missions} missions | {contribs} contributions")
        if st.sidebar.button("Logout", key="entity_logout"):
            try:
                sb.auth.sign_out()
            except Exception:
                pass
            st.session_state.entity = None
            st.session_state.entity_profile = None
            st.rerun()
        st.sidebar.markdown("---")
        return st.session_state.entity

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 🔑 Station Access")
    auth_action = st.sidebar.radio(
        "Action", ["Login", "Sign Up", "Reset Password"], horizontal=True,
        key="auth_action", label_visibility="collapsed"
    )

    if auth_action == "Login":
        email = st.sidebar.text_input("Email", key="login_email")
        pw = st.sidebar.text_input("Password", type="password", key="login_pw")
        if st.sidebar.button("Login", key="login_btn", type="primary"):
            if email and pw:
                try:
                    res = sb.auth.sign_in_with_password({"email": email, "password": pw})
                    st.session_state.entity = res.user
                    try:
                        prof = sb.table("entity_profiles").select("*").eq(
                            "id", str(res.user.id)
                        ).single().execute()
                        st.session_state.entity_profile = prof.data
                    except Exception:
                        st.session_state.entity_profile = {}
                    st.rerun()
                except Exception as e:
                    err = str(e)
                    if "Invalid login" in err or "invalid" in err.lower():
                        st.sidebar.error("Invalid email or password")
                    elif "Email not confirmed" in err or "not confirmed" in err.lower():
                        st.sidebar.error("Please confirm your email first. Check your inbox.")
                    else:
                        st.sidebar.error(f"Login failed: {err[:80]}")
            else:
                st.sidebar.warning("Enter email and password")
    elif auth_action == "Sign Up":
        new_name = st.sidebar.text_input("Display Name", key="signup_name")
        new_email = st.sidebar.text_input("Email", key="signup_email")
        new_pw = st.sidebar.text_input("Password", type="password", key="signup_pw")
        affiliation = st.sidebar.text_input(
            "Affiliation (optional)",
            placeholder="e.g. Backyard Observatory, UK",
            key="signup_affiliation"
        )
        if st.sidebar.button("Sign Up", key="signup_btn", type="primary"):
            if new_name and new_email and new_pw:
                try:
                    res = sb.auth.sign_up({"email": new_email, "password": new_pw})
                    if res.user:
                        try:
                            sb.table("entity_profiles").insert({
                                "id": str(res.user.id),
                                "display_name": new_name,
                                "affiliation": affiliation or None,
                                "contribution_count": 0,
                                "missions_completed": 0,
                            }).execute()
                        except Exception:
                            pass
                        st.sidebar.success("Check your email to confirm, then log in.")
                except Exception as e:
                    st.sidebar.error(f"Sign up failed: {str(e)[:80]}")
            else:
                st.sidebar.warning("Name, email, and password required")
    else:
        reset_email = st.sidebar.text_input("Email", key="reset_email")
        if st.sidebar.button("Send Reset Link", key="reset_btn", type="primary"):
            if reset_email:
                try:
                    sb.auth.reset_password_email(reset_email)
                    st.sidebar.success("Password reset link sent. Check your email.")
                except Exception as e:
                    st.sidebar.error(f"Failed: {str(e)[:80]}")
            else:
                st.sidebar.warning("Enter your email address")

    st.sidebar.caption("Browse freely as guest — log in to access object details")
    st.sidebar.markdown("---")
    return None


# Main App
def main():
    # Header
    st.title("🛰 Solar System Facility")
    st.markdown("### Space-Based Data Centre for Intelligent Entities")

    # Station status bar
    sb_client = get_supabase()
    station_cols = st.columns(4)
    if sb_client:
        try:
            entity_count = sb_client.table("entity_profiles").select(
                "id", count="exact"
            ).execute().count or 0
        except Exception:
            entity_count = 0
        try:
            mission_count = sb_client.table("exploration_missions").select(
                "id", count="exact"
            ).eq("status", "mission_complete").execute().count or 0
        except Exception:
            mission_count = 0
        try:
            contrib_count = sb_client.table("contributions").select(
                "id", count="exact"
            ).execute().count or 0
        except Exception:
            contrib_count = 0
        station_cols[0].metric("Entities Aboard", entity_count)
        station_cols[1].metric("Missions Completed", mission_count)
        station_cols[2].metric("Knowledge Entries", contrib_count)
        station_cols[3].metric("Station Status", "🟢 Online")
    else:
        station_cols[0].metric("Station Status", "🟢 Online")
        station_cols[1].metric("Mode", "Local Dev")
        station_cols[2].metric("Auth", "Not Configured")
        station_cols[3].metric("Backend", BACKEND_URL.split("//")[-1])

    # Test objects info expander
    with st.expander("ℹ️ Test Objects - Real API Data", expanded=False):
        st.markdown("""
        **Test objects with real data from multiple APIs:**
        
        | Object | JPL | SsODNet | Wikipedia | Notes |
        |--------|-----|---------|-----------|-------|
        | **1 Ceres** | ✓ | ✓ | ✓ | Dwarf planet, most complete data |
        | **4 Vesta** | ✓ | ✓ | ✓ | Large asteroid, well-studied |
        | **433 Eros** | ✓ | ✓ | ✓ | NEO, spacecraft visit |
        | **20000 Varuna** | ✓ | ✓ | ✓ | TNO with rotation data |
        | **134340 Pluto** | ✓ | ✓ | ✓ | Dwarf planet (New Horizons) |
        | **136199 Eris** | ✓ | ✓ | ✓ | Dwarf planet with moon |
        
        💡 **Tip:** Click on any object row to view detailed information including Wikipedia references!
        """)
        
        st.success("""
        **✅ All Data Sources Use Real APIs:**
        - 🚀 **JPL SBDB**: NASA's Small-Body Database (real-time API)
        - 🌐 **SsODNet**: IMCCE Solar System Object Database (real-time API)
        - 📖 **Wikipedia**: Encyclopedia articles and references (real-time API)
        """)

    
    # Entity auth at top of sidebar
    entity = render_entity_auth_sidebar()

    # Sidebar - Search Filters
    with st.sidebar:
        st.header("🔍 Search Filters")
        
        # API Filters
        st.markdown("#### API Filters")
        st.caption("Filters applied at JPL API level (reduces dataset size)")
        
        # Object Type filter with checkboxes
        st.markdown("**Object Type**")
        
        # Fetch dynamic counts from cached JSON file (instant load)
        counts_data = fetch_object_type_counts()
        type_counts = counts_data.get('counts', {})
        last_updated = counts_data.get('last_updated', 'Unknown')
        source = counts_data.get('source', 'unknown')
        
        # Show last updated info and refresh button
        col1, col2 = st.columns([2, 1])
        with col1:
            if source == 'cache':
                st.caption(f"📅 Updated: {last_updated[:10] if last_updated != 'Unknown' else 'Unknown'}")
            elif source == 'default':
                st.caption("⚠️ Using default counts")
            else:
                st.caption(f"ℹ️ Source: {source}")
        with col2:
            if st.button("🔄", help="Refresh counts from JPL API", key="refresh_counts"):
                with st.spinner("Refreshing counts from JPL API..."):
                    success, new_counts, new_timestamp = refresh_object_type_counts()
                    if success:
                        st.success("✅ Counts updated!")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed: {new_timestamp}")
        
        # Define object types with full details
        object_type_options = [
            ("Planet", "Planets", 8),
            ("Moon", "Natural Satellites", 164),
            ("Notable", "Dwarf Planets & Notable Bodies", 11),
            ("NEOCP", "MPC NEOCP Candidates (pre-JPL)", _neocp_count()),
            ("NEO", "All Near-Earth Objects", type_counts.get('NEO', 0)),
            ("MBA", "Main Belt Asteroids", type_counts.get('MBA', 0)),
            ("IMB", "Inner Main Belt", type_counts.get('IMB', 0)),
            ("OMB", "Outer Main Belt", type_counts.get('OMB', 0)),
            ("TNO", "Trans-Neptunian Objects", type_counts.get('TNO', 0)),
            ("Centaur", "Centaurs", type_counts.get('Centaur', 0)),
            ("Trojan", "Jupiter Trojans", type_counts.get('Trojan', 0)),
            ("IEO", "Interior to Earth Orbit", type_counts.get('IEO', 0)),
            ("ATE", "Aten asteroids (NEO subtype)", type_counts.get('ATE', 0)),
            ("APO", "Apollo asteroids (NEO subtype)", type_counts.get('APO', 0)),
            ("AMO", "Amor asteroids (NEO subtype)", type_counts.get('AMO', 0)),
            ("Comet", "Comets", type_counts.get('Comet', 0)),
            ("ISO", "Interstellar Objects", type_counts.get('ISO', 0)),
        ]
        
        # Create checkboxes for each type
        object_types = []
        for code, name, count in object_type_options:
            if st.checkbox(f"**{code}** - {name} ({count:,} objects)", key=f"obj_type_{code}"):
                object_types.append(code)
        
        st.divider()
        
        # Max results limit
        max_results = st.slider("Max Results per Type", 100, 100000, 1000, 100)
        st.caption("Maximum objects to load from API for each selected type")
        
        # Search button
        if st.button("🔄 Search & Load Data", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        
        # Info
        st.info("""
        **Data Sources:**
        - **Primary:** JPL SBDB (NASA's Small-Body Database)
        - **Enrichment:** SsODNet (IMCCE) - loaded on-demand when viewing object details
        - **References:** Wikipedia - encyclopedia articles and context
        
        **Backend:** http://localhost:5050
        
        💡 **Tip:** Click on any object row to view detailed information including SsODNet data and Wikipedia references!
        """)
    
    # Check if any object types are selected
    if not object_types:
        st.info("👆 **Please select at least one Object Type to begin exploring!**")
        st.markdown("---")
        st.markdown("""
        ### Getting Started
        
        1. **Select Object Types** in the sidebar (e.g., NEO, MBA, TNO)
        2. **Adjust Max Results** slider to control how many objects to load
        3. **Click "Search & Load Data"** to fetch objects from JPL SBDB
        
        ### Available Object Types
        - **NEO**: Near-Earth Objects (39,799 total)
        - **MBA**: Main Belt Asteroids (1.3M total)
        - **TNO**: Trans-Neptunian Objects (5,575 total)
        - And 8 more types available in the sidebar!
        """)
        return
    
    # Build filters dictionary
    api_filters = {}
    if object_types:
        api_filters['object_types'] = object_types
    
    # Fetch data from API with filters
    num_types = len(object_types)
    total_expected = max_results * num_types
    filter_desc = f" ({', '.join(object_types)})" if object_types else ""
    with st.spinner(f"Loading up to {max_results:,} objects per type (≈{total_expected:,} total){filter_desc} from JPL SBDB..."):
        objects = fetch_objects(limit=max_results, source="jpl", filters=api_filters if api_filters else None)
    
    if not objects:
        st.warning("No objects found matching your filters. Try adjusting the search criteria.")
        st.info("**Tip:** Remove some filters or increase diameter range to get more results.")
        return
    
    st.success(f"✅ Found {len(objects):,} objects matching your criteria!")
    
    # Convert to DataFrame
    df = objects_to_dataframe(objects)
    
    # Dashboard Metrics
    st.header("📊 Dashboard")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Objects", len(df))
    
    with col2:
        high_priority = len(df[df['Priority'] == 'high'])
        st.metric("High Priority", high_priority)
    
    with col3:
        avg_completeness = df['Completeness (%)'].mean()
        st.metric("Avg Completeness", f"{avg_completeness:.1f}%")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Object Explorer",
        "📈 Data Analytics", 
        "🎯 Under-Researched",
        "🤖 AI Analysis"
    ])
    
    # Tab 1: Object Explorer
    with tab1:
        st.header("Object Explorer")
        
        # Get available types and ranges from loaded data
        available_types = sorted(df['Type'].unique().tolist())
        # Always show all priority options, not just those in the data
        all_priorities = ['high', 'medium', 'low', 'unknown']
        available_priorities = all_priorities  # Show all options regardless of data
        min_completeness = 0  # Always start from 0% to show all objects by default
        max_completeness = 100  # Always go to 100% to show all objects by default
        
        # Diameter range - always start from 0 to largest
        diameter_numeric = pd.to_numeric(df['Diameter (km)'], errors='coerce')
        min_diameter = 0.0  # Always start from 0
        max_diameter = float(diameter_numeric.max()) if not diameter_numeric.isna().all() else 10000.0
        
        # Filters - Row 1
        col1, col2 = st.columns(2)
        
        with col1:
            type_filter = st.multiselect(
                "Object Type",
                options=available_types,
                default=available_types,
                help=f"Types in loaded data: {', '.join(available_types)}"
            )
        
        with col2:
            priority_filter = st.multiselect(
                "Priority",
                options=available_priorities,
                default=available_priorities,
                help=f"Priorities in loaded data"
            )
        
        # Filters - Row 2
        col3, col4 = st.columns(2)
        
        with col3:
            diameter_range = st.slider(
                "Diameter Range (km)",
                min_diameter, max_diameter, (min_diameter, max_diameter),
                help=f"Range in data: {min_diameter:.2f} - {max_diameter:.2f} km"
            )
        
        with col4:
            completeness_range = st.slider(
                "Completeness Range (%)",
                min_completeness, max_completeness, (min_completeness, max_completeness),
                help=f"Range in data: {min_completeness}% - {max_completeness}%"
            )
        
        # Apply filters
        # Convert diameter to numeric for filtering
        df_with_numeric_diameter = df.copy()
        df_with_numeric_diameter['Diameter_numeric'] = pd.to_numeric(df['Diameter (km)'], errors='coerce')
        
        # Apply filters
        # Diameter logic: Include NaN only when min=0, exclude NaN when min>0
        if diameter_range[0] == 0:
            # When min=0, include objects with no diameter data
            diameter_filter = (
                df_with_numeric_diameter['Diameter_numeric'].isna() |
                (
                    (df_with_numeric_diameter['Diameter_numeric'] >= diameter_range[0]) &
                    (df_with_numeric_diameter['Diameter_numeric'] <= diameter_range[1])
                )
            )
        else:
            # When min>0, exclude objects with no diameter data
            diameter_filter = (
                (df_with_numeric_diameter['Diameter_numeric'] >= diameter_range[0]) &
                (df_with_numeric_diameter['Diameter_numeric'] <= diameter_range[1])
            )
        
        filtered_df = df_with_numeric_diameter[
            (df_with_numeric_diameter['Type'].isin(type_filter)) &
            (df_with_numeric_diameter['Priority'].isin(priority_filter)) &
            diameter_filter &
            (df_with_numeric_diameter['Completeness (%)'] >= completeness_range[0]) &
            (df_with_numeric_diameter['Completeness (%)'] <= completeness_range[1])
        ].drop(columns=['Diameter_numeric'])

        # Sync filtered view to VR mode 3
        vr_desigs = filtered_df['Designation'].tolist()
        parts = [', '.join(type_filter)]
        if diameter_range[0] > 0 or diameter_range[1] < max_diameter:
            parts.append(f"diam {diameter_range[0]:.0f}-{diameter_range[1]:.0f} km")
        if completeness_range != (min_completeness, max_completeness):
            parts.append(f"comp {completeness_range[0]}-{completeness_range[1]}%")
        vr_desc = f"{len(vr_desigs)} objects | {' | '.join(parts)}"
        sync_vr_selection(vr_desigs, vr_desc)
        
        st.write(f"Showing {len(filtered_df)} of {len(df)} objects")
        
        # Display table with clickable names
        event = st.dataframe(
            filtered_df,
            use_container_width=True,
            height=400,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Completeness (%)": st.column_config.ProgressColumn(
                    "Completeness",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
                "Priority": st.column_config.TextColumn(
                    "Priority",
                ),
                "Name": st.column_config.TextColumn(
                    "Name",
                    help="Click on a row to view detailed information"
                ),
            }
        )
        
        # Handle row selection
        if len(event.selection.rows) > 0:
            selected_idx = event.selection.rows[0]
            selected_row = filtered_df.iloc[selected_idx]
            display_object_details_dialog(selected_row.to_dict())
        
        # Download button
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"solar_system_objects_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Tab 2: Data Analytics
    with tab2:
        st.header("Data Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Completeness distribution
            st.subheader("Completeness Distribution")
            fig = px.histogram(
                df,
                x='Completeness (%)',
                nbins=20,
                title="Object Completeness Distribution",
                color_discrete_sequence=['#4a9eff']
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#e0e0e0'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Priority distribution
            st.subheader("Priority Distribution")
            priority_counts = df['Priority'].value_counts()
            colors = [get_priority_color(p) for p in priority_counts.index]
            
            fig = px.pie(
                values=priority_counts.values,
                names=priority_counts.index,
                title="Research Priority Distribution",
                color_discrete_sequence=colors
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#e0e0e0'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Property coverage
        st.subheader("Property Coverage Analysis")
        
        properties = [
            'Diameter (km)', 'Albedo', 'Rotation Period (h)',
            'Spectral Type (Bus)', 'Spectral Type (Tholen)'
        ]
        
        coverage_data = []
        for prop in properties:
            total = len(df)
            present = df[prop].notna().sum()
            percentage = (present / total * 100) if total > 0 else 0
            coverage_data.append({
                'Property': prop,
                'Coverage (%)': percentage,
                'Present': present,
                'Missing': total - present
            })
        
        coverage_df = pd.DataFrame(coverage_data)
        
        fig = px.bar(
            coverage_df,
            x='Property',
            y='Coverage (%)',
            title="Property Coverage Across Dataset",
            color='Coverage (%)',
            color_continuous_scale='RdYlGn',
            text='Coverage (%)'
        )
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#e0e0e0',
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed coverage table
        st.dataframe(coverage_df, use_container_width=True)
    
    # Tab 3: Under-Researched
    with tab3:
        st.header("Under-Researched Objects")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            priority_level = st.selectbox(
                "Minimum Priority",
                ["high", "medium", "low"],
                format_func=lambda x: x.capitalize()
            )
            
            max_results = st.number_input(
                "Max Results",
                min_value=10,
                max_value=200,
                value=50,
                step=10
            )
        
        with col2:
            st.info("""
            **Priority Criteria:**
            - **High**: NEOs/PHAs missing 2+ critical properties
            - **Medium**: Any object missing 3+ critical properties  
            - **Low**: Objects with <3 missing properties
            
            Critical properties: diameter, albedo, rotation period, spectral type
            """)
        
        # Filter from loaded data instead of calling API
        priority_map = {"high": ["high"], "medium": ["high", "medium"], "low": ["high", "medium", "low"]}
        allowed_priorities = priority_map.get(priority_level, ["high", "medium", "low"])
        
        ur_df = df[df['Priority'].isin(allowed_priorities)].copy()
        ur_df = ur_df.sort_values('Completeness (%)', ascending=True).head(max_results)
        
        if len(ur_df) > 0:
            
            st.write(f"Found {len(ur_df)} under-researched objects")
            
            # Display with ranking
            ur_df.insert(0, 'Rank', range(1, len(ur_df) + 1))
            
            ur_event = st.dataframe(
                ur_df,
                use_container_width=True,
                height=500,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "Rank": st.column_config.NumberColumn(
                        "Rank",
                        format="#%d"
                    ),
                    "Completeness (%)": st.column_config.ProgressColumn(
                        "Completeness",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                    ),
                    "Name": st.column_config.TextColumn(
                        "Name",
                        help="Click on a row to view detailed information"
                    ),
                }
            )
            
            # Handle row selection
            if len(ur_event.selection.rows) > 0:
                selected_idx = ur_event.selection.rows[0]
                selected_row = ur_df.iloc[selected_idx]
                display_object_details_dialog(selected_row.to_dict())
            
            # Recommendations
            st.subheader("📋 Observation Recommendations")
            
            neos_missing_spectral = ur_df[
                (ur_df['Type'] == 'NEO') & 
                (ur_df['Missing Properties'].str.contains('spec', na=False))
            ]
            
            phas_missing_size = ur_df[
                (ur_df['PHA'] == 'Yes') & 
                (ur_df['Missing Properties'].str.contains('diameter|albedo', na=False))
            ]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "NEOs Missing Spectral Data",
                    len(neos_missing_spectral),
                    help="High priority for ground-based spectroscopy"
                )
                if len(neos_missing_spectral) > 0:
                    st.write("**Top 5 Targets:**")
                    for i, row in neos_missing_spectral.head(5).iterrows():
                        st.write(f"• {row['Designation']} - {row['Name']}")
            
            with col2:
                st.metric(
                    "PHAs Missing Size Data",
                    len(phas_missing_size),
                    help="Critical for impact risk assessment"
                )
                if len(phas_missing_size) > 0:
                    st.write("**Top 5 Targets:**")
                    for i, row in phas_missing_size.head(5).iterrows():
                        st.write(f"• {row['Designation']} - {row['Name']}")
        else:
            st.warning("No under-researched objects found with current criteria.")
    
    # Tab 4: AI Analysis
    with tab4:
        st.header("🤖 AI-Powered Analysis")
        
        st.info("""
        **MCP Server Integration**
        
        The Solar System Explorer includes an MCP (Model Context Protocol) server that allows
        AI assistants to directly query and analyze the data.
        
        Configure your AI client to use:
        ```
        python3 /home/gwil/Cursor/Astronomy/Solar-System/mcp_server_simple.py
        ```
        
        See `MCP_README.md` for setup instructions.
        """)
        
        st.subheader("Quick Analysis")
        
        # NEO Analysis
        neos_df = df[df['Type'] == 'NEO']
        phas_df = df[df['PHA'] == 'Yes']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total NEOs", len(neos_df))
            if len(neos_df) > 0:
                avg_neo_completeness = neos_df['Completeness (%)'].mean()
                st.metric("Avg NEO Completeness", f"{avg_neo_completeness:.1f}%")
        
        with col2:
            st.metric("PHAs", len(phas_df))
            if len(phas_df) > 0:
                high_priority_phas = len(phas_df[phas_df['Priority'] == 'high'])
                st.metric("High Priority PHAs", high_priority_phas)
        
        with col3:
            missing_diameter = len(df[df['Diameter (km)'].isna()])
            missing_spectral = len(df[
                (df['Spectral Type (Bus)'].isna()) & 
                (df['Spectral Type (Tholen)'].isna())
            ])
            st.metric("Missing Diameter", missing_diameter)
            st.metric("Missing Spectral Type", missing_spectral)
        
        # Insights
        st.subheader("💡 Key Insights")
        
        insights = []
        
        if len(neos_df) > 0:
            neo_completeness = neos_df['Completeness (%)'].mean()
            if neo_completeness < 70:
                insights.append(f"⚠️ NEO characterization is below 70% ({neo_completeness:.1f}%). Priority should be given to NEO observations.")
        
        if len(phas_df[phas_df['Priority'] == 'high']) > 0:
            insights.append(f"🚨 {len(phas_df[phas_df['Priority'] == 'high'])} PHAs are high priority for characterization (planetary defense).")
        
        if missing_spectral > len(df) * 0.5:
            insights.append(f"🔬 Over 50% of objects lack spectral classification. Ground-based spectroscopy campaigns recommended.")
        
        if missing_diameter > len(df) * 0.3:
            insights.append(f"📏 {missing_diameter} objects lack diameter measurements. Radar or thermal IR observations needed.")
        
        for insight in insights:
            st.write(insight)
        
        if not insights:
            st.success("✅ Dataset has good overall coverage. Continue routine observations.")

# Run the app
if __name__ == "__main__":
    main()

