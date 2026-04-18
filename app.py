#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Solar System Small Bodies Explorer
Main Flask application for exploring under-researched small solar system objects
"""

from flask import Flask, render_template, jsonify, request, make_response
from flask_cors import CORS
import requests
import json
import time
import uuid
import sqlite3
import smtplib
import threading
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

# Cache directory
CACHE_DIR = 'cache'
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# ============================================================================
# DATABASE (SQLite)
# ============================================================================

DB_PATH = os.path.join(CACHE_DIR, 'facility.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL COLLATE NOCASE,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            affiliation TEXT,
            email_verified INTEGER DEFAULT 0,
            verify_token TEXT,
            reset_token TEXT,
            reset_token_expires TEXT,
            contribution_count INTEGER DEFAULT 0,
            missions_completed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS contributions (
            id TEXT PRIMARY KEY,
            object_designation TEXT NOT NULL,
            user_id TEXT REFERENCES users(id),
            user_name TEXT NOT NULL,
            kind TEXT NOT NULL CHECK (kind IN ('comment','observation','correction','mission_report')),
            body TEXT,
            structured_data TEXT,
            parent_id TEXT REFERENCES contributions(id),
            source_references TEXT,
            status TEXT DEFAULT 'published',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_contrib_object ON contributions(object_designation);
        CREATE INDEX IF NOT EXISTS idx_contrib_kind ON contributions(kind);
        CREATE INDEX IF NOT EXISTS idx_contrib_parent ON contributions(parent_id);

        CREATE TABLE IF NOT EXISTS exploration_missions (
            id TEXT PRIMARY KEY,
            object_designation TEXT NOT NULL,
            requested_by TEXT REFERENCES users(id),
            requested_by_name TEXT NOT NULL,
            status TEXT DEFAULT 'deploying',
            sources_queried TEXT,
            findings_summary TEXT,
            data_gaps TEXT,
            completeness_score REAL,
            contribution_id TEXT REFERENCES contributions(id),
            duration_seconds REAL,
            started_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_missions_object ON exploration_missions(object_designation);

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id),
            created_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
    """)
    conn.close()

init_db()

# ============================================================================
# SMTP EMAIL HELPER
# ============================================================================

SMTP_HOST = os.environ.get("SMTP_HOST", "mail.zoomoot.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "info@zoomoot.com")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SITE_URL = os.environ.get("SITE_URL", "http://116.203.54.210")
BACKEND_URL_EXT = os.environ.get("BACKEND_URL_EXT", SITE_URL)
NOTIFICATION_EMAIL = os.environ.get("NOTIFICATION_EMAIL", "info@zoomoot.com")


def _send_email(to_email, subject, html_body):
    """Send an email via SMTP in a background thread."""
    if not SMTP_PASS:
        print(f"[SMTP] No SMTP_PASS set, skipping email to {to_email}: {subject}")
        return

    def _do_send():
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"Solar System Facility <{SMTP_USER}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html"))

            if SMTP_PORT == 465:
                with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as srv:
                    srv.login(SMTP_USER, SMTP_PASS)
                    srv.send_message(msg)
            else:
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as srv:
                    srv.starttls()
                    srv.login(SMTP_USER, SMTP_PASS)
                    srv.send_message(msg)
            print(f"[SMTP] Sent to {to_email}: {subject}")
        except Exception as e:
            print(f"[SMTP] Failed to send to {to_email}: {e}")

    threading.Thread(target=_do_send, daemon=True).start()


def _send_verification_email(email, display_name, token):
    link = f"{BACKEND_URL_EXT}/api/auth/verify?token={token}"
    _send_email(email, "Verify your Solar System Facility account", f"""
        <h2>Welcome to the Solar System Facility, {display_name}!</h2>
        <p>Click the link below to verify your email address and activate your account:</p>
        <p><a href="{link}" style="display:inline-block;padding:12px 24px;
            background:#4a9eff;color:white;text-decoration:none;border-radius:6px;
            font-weight:bold;">Verify Email</a></p>
        <p>Or copy this link: <br><code>{link}</code></p>
        <hr>
        <p style="color:#888;font-size:0.85em;">Solar System Facility — Space-Based Data Centre for Intelligent Entities</p>
    """)


def _send_reset_email(email, token):
    link = f"{BACKEND_URL_EXT}/api/auth/reset?token={token}"
    _send_email(email, "Reset your Solar System Facility password", f"""
        <h2>Password Reset</h2>
        <p>Click the link below to reset your password. This link expires in 1 hour.</p>
        <p><a href="{link}" style="display:inline-block;padding:12px 24px;
            background:#4a9eff;color:white;text-decoration:none;border-radius:6px;
            font-weight:bold;">Reset Password</a></p>
        <p>Or copy this link: <br><code>{link}</code></p>
        <p>If you didn't request this, ignore this email.</p>
        <hr>
        <p style="color:#888;font-size:0.85em;">Solar System Facility</p>
    """)


def _send_contribution_notification(contribution):
    """Notify all previous contributors on the same object, plus info@zoomoot.com.

    - Every user who has previously contributed to this object gets notified
    - If this is a reply, the parent post author is always included
    - The author of the new contribution is excluded (they already know)
    - info@zoomoot.com is always CC'd
    """
    kind_labels = {
        "comment": "Discussion Comment",
        "observation": "Observation Report",
        "correction": "Data Correction",
        "mission_report": "Mission Report",
    }
    kind_label = kind_labels.get(contribution["kind"], contribution["kind"])
    is_reply = bool(contribution.get("parent_id"))
    prefix = "Reply" if is_reply else "New"
    obj = contribution["object_designation"]
    author_id = contribution.get("user_id", "")

    body_parts = [
        f"<h2>{prefix} {kind_label} on {obj}</h2>",
        f"<p><strong>From:</strong> {contribution['user_name']}</p>",
    ]
    if contribution.get("body"):
        body_parts.append(f"<blockquote style='border-left:3px solid #4a9eff;"
                          f"padding:8px 12px;margin:12px 0;color:#ddd;'>"
                          f"{contribution['body']}</blockquote>")
    if contribution.get("structured_data"):
        try:
            sd = json.loads(contribution["structured_data"]) if isinstance(
                contribution["structured_data"], str
            ) else contribution["structured_data"]
            if sd:
                body_parts.append(
                    f"<h3>Data</h3><pre>{json.dumps(sd, indent=2)}</pre>"
                )
        except Exception:
            pass
    body_parts.append(
        f'<p><a href="{SITE_URL}" style="display:inline-block;padding:10px 20px;'
        f'background:#4a9eff;color:white;text-decoration:none;border-radius:6px;'
        f'font-weight:bold;">Open Solar System Facility</a></p>'
    )
    body_parts.append(
        f'<hr><p style="color:#888;font-size:0.85em;">'
        f'You received this because you contributed to {obj} on the Solar System Facility. '
        f'</p>'
    )
    html_body = "\n".join(body_parts)
    subject = f"[SSF] {prefix} {kind_label}: {obj}"

    # Collect email addresses of all other contributors on this object
    conn = get_db()
    recipients = set()

    # All distinct users who contributed to this object (except the author)
    rows = conn.execute(
        "SELECT DISTINCT u.id, u.email FROM users u "
        "INNER JOIN contributions c ON c.user_id = u.id "
        "WHERE c.object_designation = ? AND u.id != ? AND u.email_verified = 1",
        (obj, author_id),
    ).fetchall()
    for r in rows:
        recipients.add(r["email"])

    # If it's a reply, ensure the parent post author is included
    if is_reply and contribution.get("parent_id"):
        parent = conn.execute(
            "SELECT u.email FROM users u "
            "INNER JOIN contributions c ON c.user_id = u.id "
            "WHERE c.id = ? AND u.id != ? AND u.email_verified = 1",
            (contribution["parent_id"], author_id),
        ).fetchone()
        if parent:
            recipients.add(parent["email"])

    conn.close()

    # Send individual notification to each subscriber
    for email in recipients:
        _send_email(email, subject, html_body)

    # Always CC info@zoomoot.com (skip if it's already in recipients)
    if NOTIFICATION_EMAIL not in recipients:
        _send_email(NOTIFICATION_EMAIL, subject, html_body)


# ============================================================================
# AUTH API ENDPOINTS
# ============================================================================

@app.route('/api/auth/signup', methods=['POST'])
def auth_signup():
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")
    display_name = (data.get("display_name") or "").strip()
    affiliation = (data.get("affiliation") or "").strip() or None

    if not email or not password or not display_name:
        return jsonify({"error": "Email, password, and display name are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    user_id = str(uuid.uuid4())
    verify_token = str(uuid.uuid4())
    pw_hash = generate_password_hash(password)

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (id, email, display_name, password_hash, affiliation, verify_token) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, email, display_name, pw_hash, affiliation, verify_token),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "An account with this email already exists"}), 409
    conn.close()

    _send_verification_email(email, display_name, verify_token)
    return jsonify({"ok": True, "message": "Account created. Check your email to verify."})


@app.route('/api/auth/verify')
def auth_verify():
    token = request.args.get("token", "")
    if not token:
        return "<h2>Invalid link</h2>", 400

    conn = get_db()
    user = conn.execute(
        "SELECT id, display_name, email_verified FROM users WHERE verify_token = ?",
        (token,),
    ).fetchone()

    if not user:
        conn.close()
        return make_response(f"""
            <html><body style="font-family:sans-serif;text-align:center;padding:60px;">
            <h2>Invalid or expired verification link</h2>
            <p>This link may have already been used.</p>
            <p><a href="{SITE_URL}">Go to Solar System Facility</a></p>
            </body></html>
        """)

    if not user["email_verified"]:
        conn.execute(
            "UPDATE users SET email_verified = 1, verify_token = NULL WHERE id = ?",
            (user["id"],),
        )
        conn.commit()
    conn.close()

    return make_response(f"""
        <html><body style="font-family:sans-serif;text-align:center;padding:60px;">
        <h1>Email Verified!</h1>
        <p>Welcome aboard, <strong>{user['display_name']}</strong>.</p>
        <p>You can now <a href="{SITE_URL}">log in to the Solar System Facility</a>.</p>
        </body></html>
    """)


SESSION_DURATION_DAYS = 30


def _create_session(user_id):
    token = str(uuid.uuid4())
    expires = (datetime.utcnow() + timedelta(days=SESSION_DURATION_DAYS)).isoformat()
    conn = get_db()
    conn.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires),
    )
    conn.commit()
    conn.close()
    return token


def _validate_session(token):
    """Return user dict if session is valid, else None."""
    if not token:
        return None
    conn = get_db()
    row = conn.execute(
        "SELECT s.user_id, s.expires_at, u.id, u.email, u.display_name, "
        "u.affiliation, u.contribution_count, u.missions_completed "
        "FROM sessions s JOIN users u ON s.user_id = u.id "
        "WHERE s.token = ?",
        (token,),
    ).fetchone()
    if not row:
        conn.close()
        return None
    if datetime.utcnow() > datetime.fromisoformat(row["expires_at"]):
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None
    conn.close()
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
        "affiliation": row["affiliation"],
        "contribution_count": row["contribution_count"],
        "missions_completed": row["missions_completed"],
    }


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    if not user["email_verified"]:
        return jsonify({"error": "Please verify your email first. Check your inbox."}), 403

    session_token = _create_session(user["id"])

    return jsonify({
        "ok": True,
        "session_token": session_token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "display_name": user["display_name"],
            "affiliation": user["affiliation"],
            "contribution_count": user["contribution_count"],
            "missions_completed": user["missions_completed"],
        },
    })


@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    """Validate a session token and return the user, or 401."""
    token = request.args.get("token", "")
    user = _validate_session(token)
    if not user:
        return jsonify({"error": "Invalid or expired session"}), 401
    return jsonify({"ok": True, "user": user})


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    data = request.json or {}
    token = data.get("session_token", "")
    if token:
        conn = get_db()
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
    return jsonify({"ok": True})


@app.route('/api/auth/forgot-password', methods=['POST'])
def auth_forgot_password():
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    conn = get_db()
    user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if user:
        reset_token = str(uuid.uuid4())
        expires = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        conn.execute(
            "UPDATE users SET reset_token = ?, reset_token_expires = ? WHERE id = ?",
            (reset_token, expires, user["id"]),
        )
        conn.commit()
        _send_reset_email(email, reset_token)
    conn.close()
    return jsonify({"ok": True, "message": "If that email exists, a reset link has been sent."})


@app.route('/api/auth/reset', methods=['GET'])
def auth_reset_form():
    token = request.args.get("token", "")
    if not token:
        return "<h2>Invalid link</h2>", 400

    conn = get_db()
    user = conn.execute(
        "SELECT id, reset_token_expires FROM users WHERE reset_token = ?",
        (token,),
    ).fetchone()
    conn.close()

    if not user:
        return make_response(f"""
            <html><body style="font-family:sans-serif;text-align:center;padding:60px;">
            <h2>Invalid or expired reset link</h2>
            <p><a href="{SITE_URL}">Go to Solar System Facility</a></p>
            </body></html>
        """)

    if user["reset_token_expires"]:
        try:
            exp = datetime.fromisoformat(user["reset_token_expires"])
            if datetime.utcnow() > exp:
                return make_response(f"""
                    <html><body style="font-family:sans-serif;text-align:center;padding:60px;">
                    <h2>This reset link has expired</h2>
                    <p>Please request a new one from the
                    <a href="{SITE_URL}">Solar System Facility</a>.</p>
                    </body></html>
                """)
        except Exception:
            pass

    return make_response(f"""
        <html><body style="font-family:sans-serif;max-width:400px;margin:60px auto;padding:20px;">
        <h2>Reset Your Password</h2>
        <form method="POST" action="/api/auth/reset">
            <input type="hidden" name="token" value="{token}">
            <p><label>New Password<br>
                <input type="password" name="password" minlength="6"
                    required style="width:100%;padding:8px;margin-top:4px;">
            </label></p>
            <p><label>Confirm Password<br>
                <input type="password" name="password_confirm" minlength="6"
                    required style="width:100%;padding:8px;margin-top:4px;">
            </label></p>
            <p><button type="submit" style="padding:10px 24px;background:#4a9eff;
                color:white;border:none;border-radius:6px;cursor:pointer;font-size:1em;">
                Set New Password</button></p>
        </form>
        </body></html>
    """)


@app.route('/api/auth/reset', methods=['POST'])
def auth_reset_submit():
    token = request.form.get("token") or (request.json or {}).get("token", "")
    password = request.form.get("password") or (request.json or {}).get("password", "")
    password_confirm = request.form.get("password_confirm") or password

    if not token or not password:
        return "<h2>Missing token or password</h2>", 400
    if password != password_confirm:
        return "<h2>Passwords do not match</h2><p>Go back and try again.</p>", 400
    if len(password) < 6:
        return "<h2>Password must be at least 6 characters</h2>", 400

    conn = get_db()
    user = conn.execute(
        "SELECT id, reset_token_expires FROM users WHERE reset_token = ?",
        (token,),
    ).fetchone()

    if not user:
        conn.close()
        return make_response(f"""
            <html><body style="font-family:sans-serif;text-align:center;padding:60px;">
            <h2>Invalid or expired reset link</h2>
            <p><a href="{SITE_URL}">Go to Solar System Facility</a></p>
            </body></html>
        """)

    if user["reset_token_expires"]:
        try:
            if datetime.utcnow() > datetime.fromisoformat(user["reset_token_expires"]):
                conn.close()
                return "<h2>This reset link has expired</h2>", 400
        except Exception:
            pass

    conn.execute(
        "UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expires = NULL WHERE id = ?",
        (generate_password_hash(password), user["id"]),
    )
    conn.commit()
    conn.close()

    return make_response(f"""
        <html><body style="font-family:sans-serif;text-align:center;padding:60px;">
        <h1>Password Updated!</h1>
        <p>You can now <a href="{SITE_URL}">log in with your new password</a>.</p>
        </body></html>
    """)


# ============================================================================
# CONTRIBUTIONS API ENDPOINTS
# ============================================================================

@app.route('/api/contributions', methods=['GET'])
def list_contributions():
    obj = request.args.get("object", "")
    kind = request.args.get("kind", "")
    limit = min(int(request.args.get("limit", "200")), 500)

    if not obj:
        return jsonify({"error": "object parameter required"}), 400

    conn = get_db()
    if kind:
        rows = conn.execute(
            "SELECT * FROM contributions WHERE object_designation = ? AND kind = ? "
            "ORDER BY created_at ASC LIMIT ?",
            (obj, kind, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM contributions WHERE object_designation = ? "
            "ORDER BY created_at ASC LIMIT ?",
            (obj, limit),
        ).fetchall()
    conn.close()

    results = []
    for r in rows:
        entry = dict(r)
        for json_field in ("structured_data", "source_references"):
            if entry.get(json_field):
                try:
                    entry[json_field] = json.loads(entry[json_field])
                except Exception:
                    pass
        results.append(entry)
    return jsonify({"contributions": results})


@app.route('/api/contributions', methods=['POST'])
def create_contribution():
    data = request.json or {}
    obj = data.get("object_designation", "")
    user_id = data.get("user_id", "")
    user_name = data.get("user_name", "")
    kind = data.get("kind", "")
    body = data.get("body", "")
    parent_id = data.get("parent_id") or None
    structured_data = data.get("structured_data")
    source_refs = data.get("source_references")

    if not obj or not user_id or not user_name or not kind:
        return jsonify({"error": "object_designation, user_id, user_name, and kind are required"}), 400

    contrib_id = str(uuid.uuid4())
    sd_json = json.dumps(structured_data) if structured_data else None
    sr_json = json.dumps(source_refs) if source_refs else None

    conn = get_db()
    conn.execute(
        "INSERT INTO contributions (id, object_designation, user_id, user_name, kind, body, "
        "structured_data, parent_id, source_references) VALUES (?,?,?,?,?,?,?,?,?)",
        (contrib_id, obj, user_id, user_name, kind, body, sd_json, parent_id, sr_json),
    )
    conn.execute(
        "UPDATE users SET contribution_count = contribution_count + 1 WHERE id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()

    _send_contribution_notification({
        "object_designation": obj,
        "user_id": user_id,
        "user_name": user_name,
        "kind": kind,
        "body": body,
        "structured_data": structured_data,
        "parent_id": parent_id,
    })

    return jsonify({"ok": True, "id": contrib_id})


@app.route('/api/missions', methods=['GET'])
def list_missions():
    obj = request.args.get("object", "")
    if not obj:
        return jsonify({"error": "object parameter required"}), 400

    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM exploration_missions WHERE object_designation = ? "
        "ORDER BY started_at DESC LIMIT 20",
        (obj,),
    ).fetchall()
    conn.close()

    results = []
    for r in rows:
        entry = dict(r)
        for json_field in ("sources_queried", "data_gaps"):
            if entry.get(json_field):
                try:
                    entry[json_field] = json.loads(entry[json_field])
                except Exception:
                    pass
        results.append(entry)
    return jsonify({"missions": results})


@app.route('/api/missions', methods=['POST'])
def create_mission():
    data = request.json or {}
    mission_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute(
        "INSERT INTO exploration_missions (id, object_designation, requested_by, "
        "requested_by_name, status) VALUES (?,?,?,?,?)",
        (mission_id, data.get("object_designation", ""),
         data.get("requested_by", ""), data.get("requested_by_name", ""), "deploying"),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": mission_id})


@app.route('/api/missions/<mission_id>', methods=['PUT'])
def update_mission(mission_id):
    data = request.json or {}
    fields = []
    values = []
    for key in ("status", "findings_summary", "completeness_score",
                "contribution_id", "duration_seconds", "completed_at"):
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    for json_key in ("sources_queried", "data_gaps"):
        if json_key in data:
            fields.append(f"{json_key} = ?")
            values.append(json.dumps(data[json_key]))

    if not fields:
        return jsonify({"error": "No fields to update"}), 400

    values.append(mission_id)
    conn = get_db()
    conn.execute(f"UPDATE exploration_missions SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route('/api/users/<user_id>', methods=['GET'])
def get_user_profile(user_id):
    conn = get_db()
    user = conn.execute(
        "SELECT id, email, display_name, affiliation, contribution_count, "
        "missions_completed, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(dict(user))


@app.route('/api/users/<user_id>/increment-missions', methods=['POST'])
def increment_missions(user_id):
    conn = get_db()
    conn.execute(
        "UPDATE users SET missions_completed = missions_completed + 1 WHERE id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route('/api/stats/community')
def community_stats():
    conn = get_db()
    users = conn.execute("SELECT COUNT(*) FROM users WHERE email_verified = 1").fetchone()[0]
    missions = conn.execute(
        "SELECT COUNT(*) FROM exploration_missions WHERE status = 'mission_complete'"
    ).fetchone()[0]
    contribs = conn.execute("SELECT COUNT(*) FROM contributions").fetchone()[0]
    conn.close()
    return jsonify({"entities": users, "missions": missions, "contributions": contribs})

# ============================================================================
# DATA SOURCE INTEGRATIONS
# ============================================================================

class JPLSBDBClient:
    """Client for JPL Small-Body Database"""
    BASE_URL = "https://ssd-api.jpl.nasa.gov/sbdb_query.api"
    CAD_URL = "https://ssd-api.jpl.nasa.gov/cad.api"
    
    def __init__(self):
        self.cache_file = os.path.join(CACHE_DIR, 'jpl_sbdb_cache.json')
        self.cache_expiry = timedelta(hours=24)
    
    def query_objects(self, limit=100, offset=0, filters=None):
        """Query SBDB for objects with specific filters"""
        cache_key = f"query_{limit}_{offset}_{str(filters)}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        # Build query parameters
        params = {
            'fields': 'spkid,full_name,pdes,name,prefix,neo,pha,H,diameter,albedo,rot_per,GM,BV,UB,spec_B,spec_T,condition_code,rms,a,e,i,om,w,ma,tp',
            'limit': limit
        }
        
        # Add offset for pagination if specified
        if offset > 0:
            params['offset'] = offset
        
        # Determine sb-kind based on filters
        sb_kind = 'a'  # Default to asteroids
        
        # Add filters if provided
        if filters:
            # Object type filter (sb-class) - THIS WORKS!
            if 'object_types' in filters and filters['object_types']:
                # Map UI names to JPL API sb-class values
                type_map = {
                    'NEO': ['ATE', 'APO', 'AMO'],  # All NEOs (can also use sb-group=neo)
                    'MBA': ['MBA'],  # Main Belt Asteroids (1.3M)
                    'IMB': ['IMB'],  # Inner Main Belt (31,680)
                    'OMB': ['OMB'],  # Outer Main Belt (46,388)
                    'TNO': ['TNO'],  # Trans-Neptunian Objects (5,575)
                    'Centaur': ['CEN'],  # Centaurs (966)
                    'Trojan': ['TJN'],  # Jupiter Trojans (15,456)
                    'IEO': ['IEO'],  # Interior to Earth Orbit (37)
                    'ATE': ['ATE'],  # Aten asteroids (3,192)
                    'APO': ['APO'],  # Apollo asteroids (22,547)
                    'AMO': ['AMO'],  # Amor asteroids (14,060)
                    'Comet': None,  # Comets (4,037) - uses sb-kind=c, no sb-class
                    'ISO': 'special',  # Interstellar Objects (3) - queried individually
                }
                
                # Check if ISO is selected (special handling for interstellar objects)
                if 'ISO' in filters['object_types']:
                    # ISOs are queried individually by designation
                    # Known interstellar objects: 1I/'Oumuamua, 2I/Borisov, 3I/ATLAS
                    iso_designations = ['1I', '2I', '3I']
                    iso_results = {
                        'data': [],
                        'fields': ['spkid', 'full_name', 'pdes', 'name', 'prefix', 'neo', 'pha', 'H', 
                                   'diameter', 'albedo', 'rot_per', 'GM', 'BV', 'UB', 'spec_B', 'spec_T', 
                                   'condition_code', 'rms', 'a', 'e', 'i', 'om', 'w', 'ma', 'tp']
                    }
                    
                    # Fetch ISOs concurrently for better performance
                    def fetch_iso(iso_des):
                        try:
                            iso_data = self.get_object_details(iso_des)
                            if iso_data and 'object' in iso_data:
                                obj = iso_data['object']
                                
                                # Extract name from fullname
                                fullname = obj.get('fullname', '')
                                name = '-'
                                
                                if '(' in fullname:
                                    before_paren = fullname.split('(')[0].strip()
                                    in_paren = fullname.split('(')[1].split(')')[0].strip() if ')' in fullname else ''
                                    
                                    if before_paren and not before_paren.startswith(('A/', 'C/', 'P/')):
                                        name = before_paren.replace("'", "")
                                    elif in_paren and not in_paren.startswith(('A/', 'C/', 'P/', '20')):
                                        name = in_paren
                                
                                return [
                                    obj.get('spkid'),
                                    fullname,
                                    obj.get('des'),
                                    name,
                                    obj.get('prefix'),
                                    'N',  # neo
                                    'N',  # pha
                                    obj.get('H'),
                                    obj.get('diameter'),
                                    obj.get('albedo'),
                                    obj.get('rot_per'),
                                    obj.get('GM'),
                                    obj.get('BV'),
                                    obj.get('UB'),
                                    obj.get('spec_B'),
                                    obj.get('spec_T'),
                                    obj.get('condition_code'),
                                    obj.get('rms')
                                ]
                        except Exception as e:
                            print(f"Error fetching ISO {iso_des}: {e}")
                        return None
                    
                    # Use ThreadPoolExecutor to fetch ISOs in parallel
                    with ThreadPoolExecutor(max_workers=3) as executor:
                        futures = {executor.submit(fetch_iso, iso_des): iso_des for iso_des in iso_designations}
                        for future in as_completed(futures):
                            result = future.result()
                            if result:
                                iso_results['data'].append(result)
                    
                    return iso_results
                
                # Check if Comets is selected
                if 'Comet' in filters['object_types']:
                    # Comets use sb-kind=c and no sb-class
                    sb_kind = 'c'
                else:
                    # Collect all sb-class values for selected asteroid types
                    sb_classes = []
                    for obj_type in filters['object_types']:
                        if obj_type in type_map and type_map[obj_type] and type_map[obj_type] != 'special':
                            sb_classes.extend(type_map[obj_type])
                    
                    if sb_classes:
                        params['sb-class'] = ','.join(sb_classes)
        
        # Set sb-kind
        params['sb-kind'] = sb_kind
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            print(f"JPL SBDB Error: {e}")
            return None
    
    def get_object_details(self, designation):
        """Get detailed info for a specific object"""
        cache_key = f"object_{designation}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        try:
            # Use SBDB API for single object
            url = f"https://ssd-api.jpl.nasa.gov/sbdb.api?sstr={designation}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            print(f"JPL SBDB Detail Error: {e}")
            return None
    
    def _get_cache(self, key):
        """Get cached data if valid"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    if key in cache:
                        entry = cache[key]
                        cached_time = datetime.fromisoformat(entry['timestamp'])
                        if datetime.now() - cached_time < self.cache_expiry:
                            return entry['data']
        except Exception as e:
            print(f"Cache read error: {e}")
        return None
    
    def _set_cache(self, key, data):
        """Set cache data"""
        try:
            cache = {}
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
            
            cache[key] = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f)
        except Exception as e:
            print(f"Cache write error: {e}")


class SsODNetClient:
    """Client for SsODNet (IMCCE) API"""
    BASE_URL = "https://ssp.imcce.fr/webservices/ssodnet/api/ssocard"
    
    def __init__(self):
        self.cache_file = os.path.join(CACHE_DIR, 'ssodnet_cache.json')
        self.cache_expiry = timedelta(hours=24)
    
    def get_sso_card(self, identifier):
        """Get ssoCard for an object using correct API format"""
        cache_key = f"card_{identifier}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        try:
            # Correct API format: append object name/number to URL
            url = f"{self.BASE_URL}/{identifier}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            print(f"SsODNet Error for {identifier}: {e}")
            return None
    
    def search_objects(self, query_params):
        """Search for objects using datacloud"""
        try:
            url = f"{self.BASE_URL}/ssodnet/api/datacloud.php"
            params = {'mime': 'json'}
            params.update(query_params)
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"SsODNet Search Error: {e}")
            return None
    
    def _get_cache(self, key):
        """Get cached data if valid"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    if key in cache:
                        entry = cache[key]
                        cached_time = datetime.fromisoformat(entry['timestamp'])
                        if datetime.now() - cached_time < self.cache_expiry:
                            return entry['data']
        except Exception as e:
            print(f"Cache read error: {e}")
        return None
    
    def _set_cache(self, key, data):
        """Set cache data"""
        try:
            cache = {}
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
            
            cache[key] = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f)
        except Exception as e:
            print(f"Cache write error: {e}")


class WikipediaClient:
    """Client for Wikipedia API to fetch object information"""
    BASE_URL = "https://en.wikipedia.org/api/rest_v1"
    
    def __init__(self):
        self.cache_file = os.path.join(CACHE_DIR, 'wikipedia_cache.json')
        self.cache_expiry = timedelta(days=7)  # Cache Wikipedia data for 7 days
        # Wikipedia requires a User-Agent header
        self.headers = {
            'User-Agent': 'SolarSystemExplorer/1.0 (Educational Research Tool)'
        }
    
    # Planet/moon names that need Wikipedia disambiguation
    _PLANET_NAMES = {"Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"}
    _MAJOR_MOON_NAMES = {
        "Moon", "Phobos", "Deimos", "Io", "Europa", "Ganymede", "Callisto",
        "Titan", "Rhea", "Iapetus", "Dione", "Tethys", "Enceladus", "Mimas",
        "Hyperion", "Phoebe", "Triton", "Nereid", "Charon", "Nix", "Hydra",
        "Ariel", "Umbriel", "Titania", "Oberon", "Miranda", "Proteus",
        "Amalthea", "Himalia", "Pan", "Janus", "Epimetheus",
    }

    def get_object_info(self, designation, name=None):
        """Get Wikipedia summary and link for an object"""
        search_terms = []

        # Detect if this is a planet or moon lookup
        lookup_name = name if name and name != '-' else designation
        is_planet = lookup_name in self._PLANET_NAMES
        is_moon = lookup_name in self._MAJOR_MOON_NAMES

        if designation.isdigit() and name and name != '-':
            search_terms.append(f"{designation} {name}")
        
        if name and name != '-':
            if not is_planet and not is_moon:
                search_terms.append(f"{name} (minor planet)")
                search_terms.append(f"{name} (asteroid)")
        
        if designation:
            search_terms.append(designation)
        
        if name and name != '-':
            if not is_planet and not is_moon:
                search_terms.append(f"{name} asteroid")
                search_terms.append(f"{name} comet")
                search_terms.append(f"{name} TNO")
                search_terms.append(f"{name} minor planet")
            search_terms.append(name)
        
        # Build direct title candidates (exact Wikipedia page titles)
        direct_titles = []
        if designation.isdigit() and name and name != '-':
            direct_titles.append(f"{designation} {name}")
        if name and name != '-':
            direct_titles.append(name)
        
        # Try direct title lookup first (faster, more reliable)
        expanded_titles = []
        # For planets/moons, try specific disambiguation first
        if is_planet:
            expanded_titles.append(f"{lookup_name} (planet)")
            expanded_titles.append(lookup_name)
        elif is_moon:
            expanded_titles.append(f"{lookup_name} (moon)")
            expanded_titles.append(lookup_name)
        else:
            for t in direct_titles:
                expanded_titles.append(t)
            if designation.isdigit() and name and name != '-':
                expanded_titles.append(f"{name} (dwarf planet)")
                expanded_titles.append(f"{name} (planet)")
                expanded_titles.append(f"{name} (minor planet)")
                expanded_titles.append(f"{name} (asteroid)")
                expanded_titles.append(f"{name} (comet)")
        
        for title_guess in expanded_titles:
            cache_key = f"wiki_direct_{title_guess}"
            cached = self._get_cache(cache_key)
            if cached:
                return cached
            try:
                summary_url = f"{self.BASE_URL}/page/summary/{title_guess.replace(' ', '_')}"
                resp = requests.get(summary_url, headers=self.headers, timeout=10)
                if resp.status_code == 200:
                    sd = resp.json()
                    if sd.get('type') == 'standard' and sd.get('extract'):
                        page_title = sd.get('title', title_guess)
                        print(f"  Wikipedia: direct hit for '{title_guess}' -> '{page_title}'")
                        return self._fetch_full_article(page_title, sd, f"wiki_direct_{title_guess}")
            except Exception:
                pass

        # Fall back to search API
        for term in search_terms:
            cache_key = f"wiki_{term}"
            cached = self._get_cache(cache_key)
            if cached:
                return cached
            
            try:
                search_url = f"https://en.wikipedia.org/w/api.php"
                search_params = {
                    'action': 'query',
                    'list': 'search',
                    'srsearch': term,
                    'format': 'json',
                    'srlimit': 3
                }
                
                response = requests.get(search_url, params=search_params, headers=self.headers, timeout=10)
                response.raise_for_status()
                search_data = response.json()
                
                if search_data.get('query', {}).get('search'):
                    # Try up to 3 results to find a good article
                    found_article = False
                    for search_hit in search_data['query']['search']:
                        page_title = search_hit['title']
                        
                        # Skip list/index pages
                        title_lower = page_title.lower()
                        if any(skip in title_lower for skip in [
                            'list of minor planets',
                            'list of numbered minor planets',
                            'meanings of minor-planet',
                            'list of asteroids',
                            'list of comets',
                        ]):
                            print(f"  Wikipedia: skipping list page '{page_title}' for term '{term}'")
                            continue
                    
                        summary_url = f"{self.BASE_URL}/page/summary/{page_title.replace(' ', '_')}"
                        summary_response = requests.get(summary_url, headers=self.headers, timeout=10)
                        summary_response.raise_for_status()
                        summary_data = summary_response.json()
                        
                        if summary_data.get('type') == 'disambiguation':
                            print(f"  Wikipedia: skipping disambiguation '{page_title}' for term '{term}'")
                            continue

                        extract = summary_data.get('extract', '').lower()
                        astronomical_keywords = [
                            'asteroid', 'comet', 'trans-neptunian', 'tno', 'plutino',
                            'kuiper belt', 'centaur', 'trojan', 'near-earth object',
                            'neo', 'dwarf planet', 'minor planet', 'small solar system body',
                            'discovered', 'orbit', 'astronomical', 'celestial body',
                            'solar system', 'planet', 'moon', 'satellite', 'meteoroid',
                            'perihelion', 'aphelion', 'semi-major', 'eccentricity',
                            'designation', 'observatory', 'magnitude', 'albedo',
                            'main-belt', 'amor', 'apollo', 'aten', 'atira',
                            'hilda', 'jupiter', 'scattered disc', 'oort cloud'
                        ]
                        
                        if term == name and name and name != '-':
                            is_astronomical = any(keyword in extract for keyword in astronomical_keywords)
                            if not is_astronomical:
                                continue
                        
                        print(f"  Wikipedia: search hit for '{term}' -> '{page_title}'")
                        return self._fetch_full_article(page_title, summary_data, cache_key)
                    
            except Exception as e:
                print(f"Wikipedia Error for {term}: {e}")
                continue
        
        return None

    def _fetch_full_article(self, page_title, summary_data, cache_key):
        """Fetch full article data given a confirmed page title and summary."""
        summary_extract = summary_data.get('extract', '')
        full_extract = summary_extract
        images_list = []
        categories_list = []
        extlinks_list = []

        api_url = "https://en.wikipedia.org/w/api.php"
        try:
            ext_params = {
                'action': 'query',
                'titles': page_title,
                'prop': 'extracts|images|references|categories|extlinks',
                'explaintext': True,
                'imlimit': 50,
                'cllimit': 50,
                'ellimit': 50,
                'format': 'json',
            }
            ext_resp = requests.get(api_url, params=ext_params,
                                    headers=self.headers, timeout=15)
            ext_resp.raise_for_status()
            pages = ext_resp.json().get('query', {}).get('pages', {})
            for pg in pages.values():
                txt = pg.get('extract', '')
                if len(txt) > len(full_extract):
                    full_extract = txt
                for img in pg.get('images', []):
                    img_title = img.get('title', '')
                    if img_title and not any(x in img_title.lower() for x in [
                        'icon', 'logo', 'commons-logo', 'edit-clear', 'ambox',
                        'question_book', 'folder_hexagonal', 'wiki', 'symbol',
                        'stub', 'flag_of'
                    ]):
                        images_list.append(img_title)
                for cat in pg.get('categories', []):
                    cat_title = cat.get('title', '').replace('Category:', '')
                    if cat_title:
                        categories_list.append(cat_title)
                for el in pg.get('extlinks', []):
                    url_val = el.get('*', el.get('url', ''))
                    if url_val:
                        extlinks_list.append(url_val)
        except Exception:
            pass

        image_urls = []
        for img_title in images_list[:10]:
            try:
                img_params = {
                    'action': 'query',
                    'titles': img_title,
                    'prop': 'imageinfo',
                    'iiprop': 'url|mime',
                    'format': 'json',
                }
                img_resp = requests.get(api_url, params=img_params,
                                        headers=self.headers, timeout=10)
                img_resp.raise_for_status()
                img_pages = img_resp.json().get('query', {}).get('pages', {})
                for ip in img_pages.values():
                    for ii in ip.get('imageinfo', []):
                        mime = ii.get('mime', '')
                        if mime.startswith('image/') and 'svg' not in mime:
                            image_urls.append({
                                'url': ii.get('url', ''),
                                'title': img_title.replace('File:', ''),
                            })
            except Exception:
                continue

        result = {
            'title': summary_data.get('title'),
            'summary': summary_extract,
            'extract': full_extract,
            'url': summary_data.get('content_urls', {}).get('desktop', {}).get('page'),
            'thumbnail': summary_data.get('thumbnail', {}).get('source') if summary_data.get('thumbnail') else None,
            'images': image_urls,
            'categories': categories_list,
            'external_links': extlinks_list,
        }

        self._set_cache(cache_key, result)
        return result
    
    def _get_cache(self, key):
        """Get cached data if valid"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    if key in cache:
                        entry = cache[key]
                        cached_time = datetime.fromisoformat(entry['timestamp'])
                        if datetime.now() - cached_time < self.cache_expiry:
                            return entry['data']
        except Exception as e:
            print(f"Cache read error: {e}")
        return None
    
    def _set_cache(self, key, data):
        """Set cache data"""
        try:
            cache = {}
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
            
            cache[key] = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f)
        except Exception as e:
            print(f"Cache write error: {e}")


class CompletenessAnalyzer:
    """Analyze data completeness and identify research gaps"""
    
    # Key properties to track
    CRITICAL_PROPERTIES = [
        'diameter', 'albedo', 'rot_per', 'H', 'spec_B', 'spec_T',
        'GM', 'BV', 'UB', 'density', 'taxonomy', 'family'
    ]
    
    @staticmethod
    def analyze_object(obj_data, source='jpl'):
        """Analyze completeness of a single object"""
        if source == 'jpl':
            return CompletenessAnalyzer._analyze_jpl_object(obj_data)
        elif source == 'ssodnet':
            return CompletenessAnalyzer._analyze_ssodnet_object(obj_data)
        return None
    
    @staticmethod
    def _analyze_jpl_object(obj):
        """Analyze JPL SBDB object"""
        completeness = {}
        missing = []
        present = []
        
        property_map = {
            'diameter': 'diameter',
            'albedo': 'albedo',
            'rot_per': 'rot_per',
            'H': 'H',
            'spec_B': 'spec_B',
            'spec_T': 'spec_T',
            'GM': 'GM',
            'BV': 'BV',
            'UB': 'UB'
        }
        
        for prop, key in property_map.items():
            if key in obj and obj[key] not in [None, '', 'null', 'N/A']:
                present.append(prop)
            else:
                missing.append(prop)
        
        completeness_score = len(present) / len(property_map) * 100
        
        return {
            'completeness_score': completeness_score,
            'missing_properties': missing,
            'present_properties': present,
            'research_priority': CompletenessAnalyzer._calculate_priority(missing, obj)
        }
    
    @staticmethod
    def _analyze_ssodnet_object(obj):
        """Analyze SsODNet object"""
        # Similar analysis for SsODNet format
        return {
            'completeness_score': 0,
            'missing_properties': [],
            'present_properties': [],
            'research_priority': 'unknown'
        }
    
    @staticmethod
    def _calculate_priority(missing_props, obj):
        """Calculate research priority based on missing properties"""
        # High priority: NEO/PHA with missing physical properties
        is_neo = obj.get('neo') == 'Y'
        is_pha = obj.get('pha') == 'Y'
        
        critical_missing = [p for p in missing_props if p in ['diameter', 'albedo', 'spec_B', 'spec_T']]
        
        if (is_neo or is_pha) and len(critical_missing) >= 2:
            return 'high'
        elif len(critical_missing) >= 3:
            return 'medium'
        else:
            return 'low'


# ============================================================================
# FLASK ROUTES
# ============================================================================

jpl_client = JPLSBDBClient()
ssodnet_client = SsODNetClient()
wikipedia_client = WikipediaClient()
analyzer = CompletenessAnalyzer()

# ── Unified Catalog Loader ──────────────────────────────────────────────
_catalog_cache: dict = {}   # keyed by catalog name -> {objects: [...]}


def _load_catalog(name: str) -> list:
    """Load a unified catalog file by name (e.g. 'core', 'neo', 'neocp').
    Returns a list of unified-schema object dicts.  Cached in memory."""
    if name in _catalog_cache:
        return _catalog_cache[name]
    path = os.path.join(CACHE_DIR, f'catalog_{name}.json')
    if os.path.exists(path):
        with open(path, 'r') as f:
            data = json.load(f)
        objects = data.get('objects', [])
        _catalog_cache[name] = objects
        cats = {}
        for o in objects:
            c = o.get('category', '?')
            cats[c] = cats.get(c, 0) + 1
        print(f"[Catalog:{name}] Loaded {len(objects)} objects — {cats}", flush=True)
    else:
        _catalog_cache[name] = []
        print(f"[Catalog:{name}] WARNING: {path} not found", flush=True)
    return _catalog_cache[name]


def _catalog_objects_for_type(type_code: str) -> list:
    """Return SBDB-compatible dicts from the unified catalog for a given category.
    Converts unified schema back to the flat format the rest of the pipeline expects."""
    catalog = _load_catalog('core')
    results = []
    for obj in catalog:
        if obj.get('category') != type_code:
            continue
        flat = _unified_to_flat(obj)
        results.append(flat)
    return results


def _unified_to_flat(obj: dict) -> dict:
    """Convert a unified-schema catalog object back to the flat SBDB-compatible dict
    that the analysis pipeline and API responses expect."""
    orb = obj.get('orbit', {})
    phys = obj.get('physical', {})
    flat = {
        'name': obj.get('name'),
        'pdes': obj.get('designation'),
        'full_name': obj.get('full_name'),
        'spkid': str(obj.get('spkid')) if obj.get('spkid') else None,
        'parent': obj.get('parent'),
        'type': obj.get('category'),
        'a': orb.get('a'),
        'e': orb.get('e'),
        'i': orb.get('i'),
        'om': orb.get('om'),
        'w': orb.get('w'),
        'ma': orb.get('ma'),
        'tp': orb.get('tp'),
        'per': orb.get('per'),
        'q': orb.get('q'),
        'H': phys.get('H'),
        'diameter': phys.get('diameter_km'),
        'albedo': phys.get('albedo'),
        'rot_per': phys.get('rot_per_h'),
        'GM': phys.get('GM'),
        'spec_B': phys.get('spec_B'),
        'spec_T': phys.get('spec_T'),
        'BV': phys.get('BV'),
        'UB': phys.get('UB'),
        'neo': 'Y' if phys.get('neo') else 'N',
        'pha': 'Y' if phys.get('pha') else 'N',
        'condition_code': phys.get('condition_code'),
        'rms': phys.get('rms'),
    }
    if 'neocp' in obj:
        flat['neocp'] = obj['neocp']
    return flat

# Live selection: updated by /api/objects/search, read by /api/solar_system/researched
_current_selection: list = []
_vr_designations: set | None = None   # None = show all; set = filter to these
_vr_description: str = ""

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/objects/search')
def search_objects():
    """Search for objects across data sources"""
    global _current_selection
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    source = request.args.get('source', 'jpl')
    
    # Parse filters from query parameters
    filters = {}
    
    # Object types (comma-separated)
    object_types = request.args.get('object_types', '')
    if object_types:
        filters['object_types'] = [t.strip() for t in object_types.split(',')]
    
    # Diameter range
    diameter_min = request.args.get('diameter_min', type=float)
    diameter_max = request.args.get('diameter_max', type=float)
    if diameter_min is not None:
        filters['diameter_min'] = diameter_min
    if diameter_max is not None:
        filters['diameter_max'] = diameter_max
    
    if source == 'jpl':
        # Fetch objects separately for each type with full limit per type
        if filters and 'object_types' in filters and filters['object_types']:
            all_analyzed = []
            
            for obj_type in filters['object_types']:
                # Static catalog categories (always from file, never SBDB)
                _STATIC_CATALOG = {
                    "Planet": "core", "Moon": "core", "Notable": "core",
                    "NEOCP": "neocp",
                }
                # SBDB categories that have optional catalog caches
                _SBDB_CATALOG = {
                    "MBA": "mba", "IMB": "imb", "OMB": "omb",
                    "TNO": "tno", "Centaur": "centaur", "Trojan": "trojan",
                    "Comet": "comet", "NEO": "neo",
                }

                if obj_type in _STATIC_CATALOG:
                    cat_name = _STATIC_CATALOG[obj_type]
                    cat_objects = _load_catalog(cat_name)
                    for uobj in cat_objects:
                        if uobj.get('category') != obj_type:
                            continue
                        obj_dict = _unified_to_flat(uobj)
                        obj_dict['type'] = obj_type
                        analysis = analyzer.analyze_object(obj_dict, source='jpl')
                        obj_dict['analysis'] = analysis
                        all_analyzed.append(obj_dict)
                    continue

                # For SBDB categories: try catalog cache first, fall back to live query
                if obj_type in _SBDB_CATALOG:
                    cat_name = _SBDB_CATALOG[obj_type]
                    cat_objects = _load_catalog(cat_name)
                    if cat_objects:
                        count = 0
                        for uobj in cat_objects:
                            if count >= limit:
                                break
                            if uobj.get('category') != obj_type:
                                continue
                            obj_dict = _unified_to_flat(uobj)
                            obj_dict['type'] = obj_type
                            analysis = analyzer.analyze_object(obj_dict, source='jpl')
                            obj_dict['analysis'] = analysis
                            all_analyzed.append(obj_dict)
                            count += 1
                        continue

                type_filters = {'object_types': [obj_type]}
                data = jpl_client.query_objects(limit=limit, offset=offset, filters=type_filters)
                
                if data and 'data' in data:
                    for obj_array in data['data']:
                        obj_dict = {}
                        if 'fields' in data:
                            for i, field in enumerate(data['fields']):
                                obj_dict[field] = obj_array[i] if i < len(obj_array) else None
                        
                        obj_dict['type'] = obj_type
                        
                        analysis = analyzer.analyze_object(obj_dict, source='jpl')
                        obj_dict['analysis'] = analysis
                        all_analyzed.append(obj_dict)
            
            _current_selection = all_analyzed
            print(f"[Selection] Updated: {len(all_analyzed)} objects from type-filtered search")
            return jsonify({
                'success': True,
                'count': len(all_analyzed),
                'objects': all_analyzed,
                'source': 'JPL SBDB'
            })
        else:
            # No type filter - use normal query
            data = jpl_client.query_objects(limit=limit, offset=offset, filters=filters if filters else None)
            
            if data and 'data' in data:
                analyzed = []
                for obj_array in data['data']:
                    obj_dict = {}
                    if 'fields' in data:
                        for i, field in enumerate(data['fields']):
                            obj_dict[field] = obj_array[i] if i < len(obj_array) else None
                    
                    obj_type = 'Unknown'
                    if obj_dict.get('neo') == 'Y':
                        obj_type = 'NEO'
                    
                    obj_dict['type'] = obj_type
                    
                    analysis = analyzer.analyze_object(obj_dict, source='jpl')
                    obj_dict['analysis'] = analysis
                    analyzed.append(obj_dict)
                
                _current_selection = analyzed
                print(f"[Selection] Updated: {len(analyzed)} objects from unfiltered search")
                return jsonify({
                    'success': True,
                    'count': len(analyzed),
                    'objects': analyzed,
                    'source': 'JPL SBDB'
                })
    
    elif source == 'ssodnet':
        # For SsODNet mode, just return JPL data quickly
        # SsODNet enrichment will happen on-demand when user clicks an object
        jpl_data = jpl_client.query_objects(limit=limit)
        
        if not jpl_data or 'data' not in jpl_data:
            return jsonify({'success': False, 'error': 'Could not fetch object list from JPL'})
        
        analyzed = []
        for obj_array in jpl_data['data']:
            # Convert JPL array to dict
            obj_dict = {}
            if 'fields' in jpl_data:
                for i, field in enumerate(jpl_data['fields']):
                    obj_dict[field] = obj_array[i] if i < len(obj_array) else None
            
            # Analyze completeness using JPL data
            analysis = analyzer.analyze_object(obj_dict, source='jpl')
            obj_dict['analysis'] = analysis
            analyzed.append(obj_dict)
        
        _current_selection = analyzed
        print(f"[Selection] Updated: {len(analyzed)} objects from SsODNet search")
        return jsonify({
            'success': True,
            'count': len(analyzed),
            'objects': analyzed,
            'source': 'JPL SBDB (SsODNet available on-demand)'
        })
    
    return jsonify({'success': False, 'error': 'Invalid source or no data'})

@app.route('/api/objects/<designation>')
def get_object_detail(designation):
    """Get detailed information for a specific object from all data sources"""
    jpl_data = jpl_client.get_object_details(designation)
    
    # Try to get object name from JPL data for other queries
    object_name = designation
    if jpl_data and 'object' in jpl_data:
        # Try to extract name from shortname or fullname
        shortname = jpl_data['object'].get('shortname', '')
        fullname = jpl_data['object'].get('fullname', '')
        
        if shortname:
            # Extract name after the number (e.g., "1 Ceres" -> "Ceres")
            parts = shortname.split(maxsplit=1)
            if len(parts) > 1:
                object_name = parts[1]
        elif fullname:
            # For objects without shortname, use fullname (e.g., "15789 (1993 SC)")
            # Extract the provisional designation from parentheses
            import re
            match = re.search(r'\(([^)]+)\)', fullname)
            if match:
                object_name = match.group(1)  # e.g., "1993 SC"
    
    # Fetch data from available sources (on-demand enrichment)
    ssodnet_data = ssodnet_client.get_sso_card(object_name)
    wikipedia_data = wikipedia_client.get_object_info(designation, object_name)
    
    result = {
        'designation': designation,
        'jpl': jpl_data,
        'ssodnet': ssodnet_data,
        'wikipedia': wikipedia_data
    }
    
    return jsonify(result)


# Wikipedia page rendering cache — stores tiles per page
# _wiki_render_cache[cache_key] = { 'tiles': [bytes, ...], 'width': int,
#   'tile_height': int, 'total_height': int, 'total_pages': int, 'time': datetime }
_wiki_render_cache = {}
_wiki_render_cache_ttl = timedelta(hours=6)
WIKI_TILE_HEIGHT = 4096


def _ensure_wiki_render(url):
    """Render a Wikipedia page if not already cached. Returns cache entry or None."""
    import hashlib, io
    cache_key = hashlib.md5(url.encode()).hexdigest()
    cached = _wiki_render_cache.get(cache_key)
    if cached and datetime.now() - cached['time'] < _wiki_render_cache_ttl:
        return cached

    try:
        from playwright.sync_api import sync_playwright
        from PIL import Image

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page(viewport={'width': 900, 'height': 900})
            pg.goto(url, wait_until='networkidle', timeout=30000)

            pg.evaluate("""() => {
                const selectors = [
                    '#mw-navigation', '#mw-head', '#mw-panel', '#footer',
                    '.mw-jump-link', '.vector-header', '.vector-column-end',
                    '.mw-editsection', '#siteSub', '#contentSub',
                    '.navbox', '.sistersitebox', '.side-box',
                    '#catlinks', '.mw-authority-control',
                    '.reflist', '.references', '#See_also',
                    '.mw-references-wrap'
                ];
                selectors.forEach(s => {
                    document.querySelectorAll(s).forEach(el => el.remove());
                });
                document.body.style.margin = '10px';
                document.body.style.background = '#111122';
                const content = document.querySelector('#content') || document.querySelector('#mw-content-text') || document.body;
                content.style.color = '#e0e0e0';
                content.style.background = '#111122';
                content.style.maxWidth = '880px';
                content.style.padding = '15px';
                content.style.fontSize = '18px';
                content.style.lineHeight = '1.6';
                document.querySelectorAll('a').forEach(a => a.style.color = '#6eb5ff');
                document.querySelectorAll('h1,h2,h3,h4').forEach(h => {
                    h.style.color = '#ffffff';
                    h.style.borderBottom = '1px solid #333';
                });
                document.querySelectorAll('.infobox, table.wikitable').forEach(t => {
                    t.style.background = '#1a1a35';
                    t.style.color = '#e0e0e0';
                    t.style.borderColor = '#444';
                });
                document.querySelectorAll('img').forEach(img => {
                    img.style.maxWidth = '400px';
                    img.style.height = 'auto';
                });
            }""")

            raw_bytes = pg.screenshot(full_page=True, type='png')
            browser.close()

        img = Image.open(io.BytesIO(raw_bytes))
        w, h = img.size

        tiles = []
        y = 0
        while y < h:
            tile_h = min(WIKI_TILE_HEIGHT, h - y)
            tile_img = img.crop((0, y, w, y + tile_h))
            buf = io.BytesIO()
            tile_img.save(buf, format='JPEG', quality=80)
            tiles.append(buf.getvalue())
            y += WIKI_TILE_HEIGHT

        entry = {
            'tiles': tiles,
            'width': w,
            'tile_height': WIKI_TILE_HEIGHT,
            'total_height': h,
            'total_pages': len(tiles),
            'time': datetime.now()
        }
        _wiki_render_cache[cache_key] = entry
        print(f"Wikipedia render: {w}x{h}, {len(tiles)} tile(s)")
        return entry

    except Exception as e:
        print(f"Wikipedia render error: {e}")
        return None


@app.route('/api/wikipedia/render')
def wikipedia_render():
    """Render a Wikipedia page tile. ?url=...&page=0 (default page=0)"""
    from flask import send_file
    import io

    url = request.args.get('url', '')
    page_num = int(request.args.get('page', 0))
    if not url or 'wikipedia.org' not in url:
        return jsonify({'error': 'Missing or invalid Wikipedia URL'}), 400

    entry = _ensure_wiki_render(url)
    if entry is None:
        return jsonify({'error': 'Render failed'}), 500

    if page_num < 0 or page_num >= entry['total_pages']:
        return jsonify({'error': f'Invalid page {page_num}, total={entry["total_pages"]}'}), 400

    resp = send_file(io.BytesIO(entry['tiles'][page_num]), mimetype='image/jpeg')
    resp.headers['X-Total-Pages'] = str(entry['total_pages'])
    resp.headers['X-Page-Width'] = str(entry['width'])
    resp.headers['X-Tile-Height'] = str(entry['tile_height'])
    resp.headers['X-Total-Height'] = str(entry['total_height'])
    resp.headers['X-Page-Num'] = str(page_num)
    return resp


# ── 3D Model lookup ──────────────────────────────────────────────────

MODELS_CACHE_DIR = os.path.join(CACHE_DIR, 'models')
if not os.path.exists(MODELS_CACHE_DIR):
    os.makedirs(MODELS_CACHE_DIR)

PLANET_TEXTURES = {
    'sun':      'https://www.solarsystemscope.com/textures/download/2k_sun.jpg',
    'mercury':  'https://www.solarsystemscope.com/textures/download/2k_mercury.jpg',
    'venus':    'https://www.solarsystemscope.com/textures/download/2k_venus_surface.jpg',
    'earth':    'https://www.solarsystemscope.com/textures/download/2k_earth_daymap.jpg',
    'moon':     'https://www.solarsystemscope.com/textures/download/2k_moon.jpg',
    'mars':     'https://www.solarsystemscope.com/textures/download/2k_mars.jpg',
    'jupiter':  'https://www.solarsystemscope.com/textures/download/2k_jupiter.jpg',
    'saturn':   'https://www.solarsystemscope.com/textures/download/2k_saturn.jpg',
    'uranus':   'https://www.solarsystemscope.com/textures/download/2k_uranus.jpg',
    'neptune':  'https://www.solarsystemscope.com/textures/download/2k_neptune.jpg',
    'pluto':    'https://www.solarsystemscope.com/textures/download/2k_makemake_fictional.jpg',
    'ceres':    'https://www.solarsystemscope.com/textures/download/2k_ceres_fictional.jpg',
    'vesta':    'https://www.solarsystemscope.com/textures/download/2k_haumea_fictional.jpg',
    'io':       'https://www.solarsystemscope.com/textures/download/2k_io.jpg',
    'europa':   'https://www.solarsystemscope.com/textures/download/2k_europa.jpg',
    'ganymede': 'https://www.solarsystemscope.com/textures/download/2k_ganymede.jpg',
    'callisto': 'https://www.solarsystemscope.com/textures/download/2k_callisto.jpg',
    'titan':    'https://www.solarsystemscope.com/textures/download/2k_saturn.jpg',
    # Additional moons with available textures
    'phobos':   'https://www.solarsystemscope.com/textures/download/2k_mars.jpg',
    'deimos':   'https://www.solarsystemscope.com/textures/download/2k_mars.jpg',
    'mimas':    'https://www.solarsystemscope.com/textures/download/2k_saturn.jpg',
    'enceladus': 'https://www.solarsystemscope.com/textures/download/2k_saturn.jpg',
    'tethys':   'https://www.solarsystemscope.com/textures/download/2k_saturn.jpg',
    'dione':    'https://www.solarsystemscope.com/textures/download/2k_saturn.jpg',
    'rhea':     'https://www.solarsystemscope.com/textures/download/2k_saturn.jpg',
    'iapetus':  'https://www.solarsystemscope.com/textures/download/2k_saturn.jpg',
    'hyperion': 'https://www.solarsystemscope.com/textures/download/2k_saturn.jpg',
    'phoebe':   'https://www.solarsystemscope.com/textures/download/2k_saturn.jpg',
    'miranda':  'https://www.solarsystemscope.com/textures/download/2k_uranus.jpg',
    'ariel':    'https://www.solarsystemscope.com/textures/download/2k_uranus.jpg',
    'umbriel':  'https://www.solarsystemscope.com/textures/download/2k_uranus.jpg',
    'titania':  'https://www.solarsystemscope.com/textures/download/2k_uranus.jpg',
    'oberon':   'https://www.solarsystemscope.com/textures/download/2k_uranus.jpg',
    'triton':   'https://www.solarsystemscope.com/textures/download/2k_neptune.jpg',
    'nereid':   'https://www.solarsystemscope.com/textures/download/2k_neptune.jpg',
    'charon':   'https://www.solarsystemscope.com/textures/download/2k_makemake_fictional.jpg',
}

DESIGNATION_TO_PLANET = {
    '1': 'ceres', '4': 'vesta',
    '199': 'mercury', '299': 'venus', '399': 'earth',
    '499': 'mars', '599': 'jupiter', '699': 'saturn', '799': 'uranus',
    '899': 'neptune', '999': 'pluto',
    # Moon SPK IDs
    '301': 'moon',
    '401': 'phobos', '402': 'deimos',
    '501': 'io', '502': 'europa', '503': 'ganymede', '504': 'callisto',
    '601': 'mimas', '602': 'enceladus', '603': 'tethys', '604': 'dione',
    '605': 'rhea', '606': 'titan', '607': 'hyperion', '608': 'iapetus', '609': 'phoebe',
    '701': 'ariel', '702': 'umbriel', '703': 'titania', '704': 'oberon', '705': 'miranda',
    '801': 'triton', '802': 'nereid',
    '901': 'charon',
}

# JPL Radar Astronomy direct-download shape models (OBJ/WF format)
JPL_RADAR_SHAPES = {
    '16':     ('Psyche',     'https://echo.jpl.nasa.gov/asteroids/shapes/psyche.v.final.mod.wf'),
    '216':    ('Kleopatra',  'https://echo.jpl.nasa.gov/asteroids/shapes/kleo.obj'),
    '1580':   ('Betulia',    'https://echo.jpl.nasa.gov/asteroids/shapes/betulia.obj'),
    '1620':   ('Geographos', 'https://echo.jpl.nasa.gov/asteroids/shapes/geographos.obj'),
    '2063':   ('Bacchus',    'https://echo.jpl.nasa.gov/asteroids/shapes/bacchus.obj'),
    '2100':   ('Ra-Shalom',  'https://echo.jpl.nasa.gov/asteroids/shapes/rashalom.obj'),
    '4179':   ('Toutatis',   'https://echo.jpl.nasa.gov/asteroids/shapes/toutatis.obj'),
    '4486':   ('Mithra',     'https://echo.jpl.nasa.gov/asteroids/shapes/Mithra.v1.PA.prograde.mod.obj'),
    '4660':   ('Nereus',     'https://echo.jpl.nasa.gov/asteroids/shapes/Nereus_alt1.mod.wf'),
    '4769':   ('Castalia',   'https://echo.jpl.nasa.gov/asteroids/shapes/castalia.obj'),
    '6489':   ('Golevka',    'https://echo.jpl.nasa.gov/asteroids/shapes/golevka.obj'),
    '8567':   ('1996 HW1',   'https://echo.jpl.nasa.gov/asteroids/shapes/1996hw1.obj'),
    '10115':  ('1992 SK',    'https://echo.jpl.nasa.gov/asteroids/shapes/sk.obj'),
    '25143':  ('Itokawa',    'https://echo.jpl.nasa.gov/asteroids/shapes/sf36.v.mod.wf'),
    '29075':  ('1950 DA',    'https://echo.jpl.nasa.gov/asteroids/shapes/1950DA_ProgradeModel.wf'),
    '33342':  ('1998 WT24',  'https://echo.jpl.nasa.gov/asteroids/shapes/wt24.obj'),
    '52760':  ('1998 ML14',  'https://echo.jpl.nasa.gov/asteroids/shapes/ml14.obj'),
    '54509':  ('YORP',       'https://echo.jpl.nasa.gov/asteroids/shapes/yorp.obj'),
    '66391':  ('1999 KW4',   'https://echo.jpl.nasa.gov/asteroids/shapes/kw4a.obj'),
    '136617': ('1994 CC',    'https://echo.jpl.nasa.gov/asteroids/shapes/1994CC_nominal.mod.wf'),
}

_damit_index = None
_damit_index_time = None


def _load_damit_index():
    """Download and cache the DAMIT asteroid_models CSV index."""
    global _damit_index, _damit_index_time
    if _damit_index is not None and _damit_index_time and datetime.now() - _damit_index_time < timedelta(days=7):
        return _damit_index

    index_path = os.path.join(MODELS_CACHE_DIR, 'damit_index.csv')
    need_download = True
    if os.path.exists(index_path):
        age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(index_path))
        if age < timedelta(days=7):
            need_download = False

    if need_download:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            url = 'https://astro.troja.mff.cuni.cz/projects/damit/exports/table/asteroid_models'
            print(f"  3D Models: downloading DAMIT index from {url}", flush=True)
            resp = requests.get(url, timeout=30, verify=False)
            resp.raise_for_status()
            with open(index_path, 'wb') as f:
                f.write(resp.content)
            print(f"  3D Models: DAMIT index downloaded ({len(resp.content)} bytes)", flush=True)
        except Exception as e:
            print(f"  3D Models: DAMIT index download failed: {e}", flush=True)
            if not os.path.exists(index_path):
                _damit_index = {}
                _damit_index_time = datetime.now()
                return _damit_index

    import csv
    index = {}
    try:
        with open(index_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ast_num = row.get('asteroid_id', '').strip().strip('"')
                model_id = None
                for key in row:
                    if key.strip().strip('"').strip('\ufeff') == 'id':
                        model_id = row[key].strip().strip('"')
                        break
                if ast_num and model_id:
                    if ast_num not in index:
                        index[ast_num] = []
                    index[ast_num].append(model_id)
    except Exception as e:
        print(f"  3D Models: DAMIT CSV parse error: {e}", flush=True)

    _damit_index = index
    _damit_index_time = datetime.now()
    print(f"  3D Models: DAMIT index loaded, {len(index)} asteroids")
    return index


# NASA 3D Resources GitHub — STL shape models (format, URL, expected file type)
NASA_GITHUB_MODELS = {
    '101955': ('Bennu',   'https://raw.githubusercontent.com/nasa/NASA-3D-Resources/master/3D%20Printing/Asteroid%20101955%20Bennu/Asteroid%20101955%20Bennu.stl', 'stl'),
    '25143':  ('Itokawa', 'https://raw.githubusercontent.com/nasa/NASA-3D-Resources/master/3D%20Printing/Asteroid%2025143%20Itokawa/Asteroid%2025143%20Itokawa.stl', 'stl'),
    '433':    ('Eros',    'https://raw.githubusercontent.com/nasa/NASA-3D-Resources/master/3D%20Printing/Asteroid%20433%20Eros/Asteroid%20433%20Eros.stl', 'stl'),
}


def _try_nasa_github(designation):
    """Try to download an STL/GLB from NASA 3D Resources on GitHub."""
    des = designation.strip()
    if des not in NASA_GITHUB_MODELS:
        return None, None

    name, url, ftype = NASA_GITHUB_MODELS[des]
    try:
        print(f"  3D Models: downloading NASA GitHub model for {name} ({des})", flush=True)
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200 and len(resp.content) > 100:
            import trimesh
            from io import BytesIO
            mesh = trimesh.load(BytesIO(resp.content), file_type=ftype, process=True)
            if hasattr(mesh, 'geometry'):
                mesh = mesh.to_geometry()
            if hasattr(mesh, 'faces') and len(mesh.faces) > 0:
                buf = BytesIO()
                mesh.export(buf, file_type='obj')
                obj_bytes = buf.getvalue()
                print(f"  3D Models: NASA GitHub {name}: {len(mesh.vertices)} verts, {len(mesh.faces)} faces", flush=True)
                return obj_bytes, url
    except Exception as e:
        print(f"  3D Models: NASA GitHub download error: {e}", flush=True)
    return None, None


def _try_jpl_radar(designation):
    """Try to download a shape model from JPL Radar Astronomy."""
    des = designation.strip()
    if des not in JPL_RADAR_SHAPES:
        return None, None

    name, url = JPL_RADAR_SHAPES[des]
    try:
        print(f"  3D Models: downloading JPL radar shape for {name} ({des})", flush=True)
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200 and len(resp.content) > 100:
            content = resp.content
            text = content.decode('utf-8', errors='ignore')
            if not text.strip().startswith('v ') and not text.strip().startswith('#'):
                return None, None
            print(f"  3D Models: got JPL radar shape ({len(content)} bytes)", flush=True)
            return content, url
    except Exception as e:
        print(f"  3D Models: JPL radar download error: {e}", flush=True)
    return None, None


def _try_3d_asteroids_space(designation, name=None):
    """Try to download an OBJ from 3d-asteroids.space using direct URL patterns.
    The site is behind Cloudflare so we skip page scraping."""
    return None, None


def _try_damit(designation):
    """Try to download an OBJ from DAMIT."""
    if not designation.strip().isdigit():
        return None, None

    index = _load_damit_index()
    ast_num = designation.strip()
    model_ids = index.get(ast_num, [])
    if not model_ids:
        return None, None

    model_id = model_ids[0]
    obj_url = f"https://astro.troja.mff.cuni.cz/projects/damit/asteroid_models/view/{model_id}"
    shape_url = f"https://astro.troja.mff.cuni.cz/projects/damit/generated_files/open/AsteroidModel/{model_id}/shape.obj"

    try:
        print(f"  3D Models: trying DAMIT model {model_id} for asteroid {ast_num}", flush=True)
        resp = requests.get(shape_url, timeout=30, verify=False)
        if resp.status_code == 200 and len(resp.content) > 100:
            print(f"  3D Models: got DAMIT shape.obj ({len(resp.content)} bytes)", flush=True)
            return resp.content, obj_url
    except Exception as e:
        print(f"  3D Models: DAMIT download error: {e}", flush=True)

    return None, None


def _decimate_obj(obj_bytes, target_faces=50000):
    """Decimate an OBJ model if it has too many faces."""
    try:
        import trimesh
        from io import BytesIO
        mesh = trimesh.load(BytesIO(obj_bytes), file_type='obj', process=True)
        if hasattr(mesh, 'faces') and len(mesh.faces) > target_faces:
            current = len(mesh.faces)
            print(f"  3D Models: decimating {current} -> {target_faces} faces", flush=True)
            mesh = mesh.simplify_quadric_decimation(face_count=target_faces)
            print(f"  3D Models: decimated to {len(mesh.vertices)} verts, {len(mesh.faces)} faces", flush=True)
        buf = BytesIO()
        mesh.export(buf, file_type='obj')
        return buf.getvalue(), len(mesh.vertices), len(mesh.faces)
    except Exception as e:
        print(f"  3D Models: decimation failed: {e}", flush=True)
        return obj_bytes, -1, -1


def _count_obj_geometry(obj_bytes):
    """Quick count of vertices and faces in an OBJ without full parsing."""
    verts = 0
    faces = 0
    for line in obj_bytes.decode('utf-8', errors='ignore').split('\n'):
        if line.startswith('v '):
            verts += 1
        elif line.startswith('f '):
            faces += 1
    return verts, faces


@app.route('/api/objects/<designation>/model')
def get_object_model(designation):
    """Look up a 3D shape model or texture for a solar system object."""
    des_lower = designation.lower().strip()
    print(f"  3D Models: looking up '{designation}' (lower='{des_lower}')", flush=True)

    planet_name = DESIGNATION_TO_PLANET.get(designation.strip(), des_lower)
    if planet_name in PLANET_TEXTURES:
        return jsonify({
            'has_model': True,
            'type': 'texture',
            'source': 'Solar System Scope',
            'texture_url': PLANET_TEXTURES[planet_name],
            'name': planet_name.capitalize()
        })

    cache_path = os.path.join(MODELS_CACHE_DIR, f'{designation}.obj')
    meta_path = os.path.join(MODELS_CACHE_DIR, f'{designation}.json')

    # Serve from cache (both OBJ+meta for models, meta-only for no-model)
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            if not meta.get('has_model') or os.path.exists(cache_path):
                print(f"  3D Models: serving cached result for {designation}", flush=True)
                return jsonify(meta)
        except Exception:
            pass

    object_name = None
    try:
        jpl_data = jpl_client.get_object_details(designation)
        if jpl_data and 'object' in jpl_data:
            shortname = jpl_data['object'].get('shortname', '')
            if shortname:
                parts = shortname.split(maxsplit=1)
                if len(parts) > 1:
                    object_name = parts[1]
    except Exception:
        pass

    obj_bytes = None
    source_url = None
    source_name = None

    obj_bytes, source_url = _try_nasa_github(designation)
    if obj_bytes:
        source_name = 'NASA 3D Resources'

    if not obj_bytes:
        obj_bytes, source_url = _try_jpl_radar(designation)
        if obj_bytes:
            source_name = 'JPL Radar Astronomy'

    if not obj_bytes:
        print(f"  3D Models: trying DAMIT for {designation}", flush=True)
        obj_bytes, source_url = _try_damit(designation)
        if obj_bytes:
            source_name = 'DAMIT'

    if not obj_bytes:
        print(f"  3D Models: no model found for {designation}", flush=True)
        no_model = {'has_model': False}
        with open(meta_path, 'w') as f:
            json.dump(no_model, f)
        return jsonify(no_model)

    verts, faces = _count_obj_geometry(obj_bytes)
    if faces > 100000:
        obj_bytes, verts, faces = _decimate_obj(obj_bytes, target_faces=50000)

    with open(cache_path, 'wb') as f:
        f.write(obj_bytes)

    meta = {
        'has_model': True,
        'type': 'obj',
        'source': source_name,
        'obj_url': f'/api/objects/{designation}/model/obj',
        'source_url': source_url,
        'metadata': {'vertices': verts, 'faces': faces}
    }
    with open(meta_path, 'w') as f:
        json.dump(meta, f)

    return jsonify(meta)


@app.route('/api/objects/<designation>/model/obj')
def serve_object_model(designation):
    """Serve a cached OBJ file for a solar system object."""
    from flask import send_file
    cache_path = os.path.join(MODELS_CACHE_DIR, f'{designation}.obj')
    if not os.path.exists(cache_path):
        return jsonify({'error': 'Model not found'}), 404
    return send_file(cache_path, mimetype='text/plain',
                     download_name=f'{designation}.obj')


@app.route('/api/stats/completeness')
def completeness_stats():
    """Get overall completeness statistics"""
    data = jpl_client.query_objects(limit=200)
    
    if not data or 'data' not in data:
        return jsonify({'success': False, 'error': 'No data available'})
    
    stats = {
        'total_objects': len(data['data']),
        'property_coverage': defaultdict(int),
        'priority_distribution': defaultdict(int),
        'completeness_distribution': []
    }
    
    for obj_array in data['data']:
        obj_dict = {}
        if 'fields' in data:
            for i, field in enumerate(data['fields']):
                obj_dict[field] = obj_array[i] if i < len(obj_array) else None
        
        analysis = analyzer.analyze_object(obj_dict, source='jpl')
        
        # Count present properties
        for prop in analysis['present_properties']:
            stats['property_coverage'][prop] += 1
        
        # Priority distribution
        stats['priority_distribution'][analysis['research_priority']] += 1
        
        # Completeness distribution
        stats['completeness_distribution'].append(analysis['completeness_score'])
    
    return jsonify({
        'success': True,
        'stats': stats
    })

@app.route('/api/under-researched')
def get_under_researched():
    """Get list of under-researched objects"""
    min_priority = request.args.get('priority', 'medium')
    limit = request.args.get('limit', 50, type=int)
    
    data = jpl_client.query_objects(limit=500)
    
    if not data or 'data' not in data:
        return jsonify({'success': False, 'error': 'No data available'})
    
    under_researched = []
    priority_order = {'high': 3, 'medium': 2, 'low': 1}
    min_priority_value = priority_order.get(min_priority, 2)
    
    for obj_array in data['data']:
        obj_dict = {}
        if 'fields' in data:
            for i, field in enumerate(data['fields']):
                obj_dict[field] = obj_array[i] if i < len(obj_array) else None
        
        analysis = analyzer.analyze_object(obj_dict, source='jpl')
        
        if priority_order.get(analysis['research_priority'], 0) >= min_priority_value:
            obj_dict['analysis'] = analysis
            under_researched.append(obj_dict)
    
    # Sort by priority and completeness
    under_researched.sort(
        key=lambda x: (
            -priority_order.get(x['analysis']['research_priority'], 0),
            x['analysis']['completeness_score']
        )
    )
    
    return jsonify({
        'success': True,
        'count': len(under_researched[:limit]),
        'objects': under_researched[:limit]
    })

@app.route('/api/object-types/counts')
def get_object_type_counts():
    """Get counts for each object type from cached JSON file"""
    counts_file = os.path.join(CACHE_DIR, 'object_type_counts.json')
    
    try:
        # Try to read from cached file first
        if os.path.exists(counts_file):
            with open(counts_file, 'r') as f:
                cached_data = json.load(f)
                return jsonify({
                    'success': True,
                    'counts': cached_data.get('counts', {}),
                    'last_updated': cached_data.get('last_updated', 'Unknown'),
                    'source': 'cache'
                })
        else:
            # If no cache exists, return default values
            default_counts = {
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
                'AMO': 14060
            }
            return jsonify({
                'success': True,
                'counts': default_counts,
                'last_updated': 'Never',
                'source': 'default'
            })
    
    except Exception as e:
        print(f"Error reading object type counts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/object-types/counts/refresh', methods=['POST'])
def refresh_object_type_counts():
    """Refresh object type counts from JPL API and save to cache"""
    try:
        # Query JPL API for each object type with limit=1 to get count only
        type_map = {
            'NEO': ['ATE', 'APO', 'AMO'],  # All NEOs
            'MBA': ['MBA'],  # Main Belt Asteroids
            'IMB': ['IMB'],  # Inner Main Belt
            'OMB': ['OMB'],  # Outer Main Belt
            'TNO': ['TNO'],  # Trans-Neptunian Objects
            'Centaur': ['CEN'],  # Centaurs
            'Trojan': ['TJN'],  # Jupiter Trojans
            'IEO': ['IEO'],  # Interior to Earth Orbit
            'ATE': ['ATE'],  # Aten asteroids
            'APO': ['APO'],  # Apollo asteroids
            'AMO': ['AMO'],  # Amor asteroids
            'Comet': None,  # Comets - uses sb-kind=c
            'ISO': 'special',  # Interstellar Objects - 3 known objects
        }
        
        counts = {}
        
        for ui_type, sb_classes in type_map.items():
            total_count = 0
            
            if sb_classes == 'special':
                # Special case for ISOs - hardcoded count of 3 known interstellar objects
                total_count = 3
            elif sb_classes is None:
                # Special case for Comets - use sb-kind=c without sb-class
                params = {
                    'fields': 'spkid',
                    'sb-kind': 'c',
                    'limit': 1
                }
                
                try:
                    response = requests.get(jpl_client.BASE_URL, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    
                    if 'count' in data:
                        total_count = int(data['count'])
                except Exception as e:
                    print(f"Error fetching count for {ui_type}: {e}")
            else:
                # Asteroid types - use sb-kind=a with sb-class
                for sb_class in sb_classes:
                    params = {
                        'fields': 'spkid',  # Minimal field to reduce response size
                        'sb-kind': 'a',
                        'sb-class': sb_class,
                        'limit': 1  # We only need the count
                    }
                    
                    try:
                        response = requests.get(jpl_client.BASE_URL, params=params, timeout=10)
                        response.raise_for_status()
                        data = response.json()
                        
                        # JPL API returns 'count' field with total matching objects
                        if 'count' in data:
                            total_count += int(data['count'])
                    except Exception as e:
                        print(f"Error fetching count for {sb_class}: {e}")
                        continue
            
            counts[ui_type] = total_count
        
        # Save to cache file
        counts_file = os.path.join(CACHE_DIR, 'object_type_counts.json')
        cache_data = {
            'counts': counts,
            'last_updated': datetime.now().isoformat()
        }
        
        with open(counts_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        return jsonify({
            'success': True,
            'counts': counts,
            'last_updated': cache_data['last_updated'],
            'source': 'refreshed'
        })
    
    except Exception as e:
        print(f"Error refreshing object type counts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/solar_system/scene')
def solar_system_scene():
    """
    Full 3D solar system scene: heliocentric positions for major bodies + NEOs.

    Query params:
      observer  — "earth" (default), planet name, or NEO designation (e.g. "433")
      time      — ISO-8601 UTC datetime (optional, defaults to now)
      mag_limit — apparent magnitude cutoff (default 20)
    """
    from datetime import datetime as dt_mod, timezone as tz_mod

    observer = request.args.get("observer", "earth").strip()
    mag_limit = request.args.get("mag_limit", 20.0, type=float)

    date_str = request.args.get("time", "").strip()
    dt_utc = None
    if date_str:
        try:
            if "T" in date_str or " " in date_str:
                raw = date_str.replace("Z", "+00:00").replace(" ", "T")
                dt_utc = dt_mod.fromisoformat(raw)
            else:
                dt_utc = dt_mod.strptime(date_str, "%Y-%m-%d").replace(
                    tzinfo=tz_mod.utc, hour=12, minute=0, second=0)
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=tz_mod.utc)
        except ValueError:
            return jsonify({"success": False,
                            "error": "Invalid time= (use ISO-8601 UTC)"}), 400

    try:
        from solar_scene import build_scene
        result = build_scene(observer=observer, dt_utc=dt_utc, mag_limit=mag_limit)
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/vr/selection', methods=['POST'])
def vr_selection():
    """Receive the Streamlit app's current filtered object set for VR mode 3."""
    global _vr_designations, _vr_description
    data = request.get_json(silent=True) or {}
    desigs = data.get("designations")
    if desigs is not None:
        _vr_designations = set(str(d).strip() for d in desigs if d)
    else:
        _vr_designations = None
    _vr_description = str(data.get("description", ""))
    count = len(_vr_designations) if _vr_designations else 0
    print(f"[VR Selection] {count} designations, desc={_vr_description!r}")
    return jsonify({"success": True, "count": count})


@app.route('/api/solar_system/researched')
def solar_system_researched():
    """
    3D scene from objects loaded in the Streamlit Solar System app.

    Uses cached SBDB query results (with orbital elements) to compute positions.
    Falls back to neo_mission_data.json for objects without orbital elements.

    Query params:
      mag_limit — apparent magnitude cutoff (default 25)
      time      — ISO-8601 UTC datetime (optional, defaults to now)
    """
    from datetime import datetime as dt_mod, timezone as tz_mod

    mag_limit = request.args.get("mag_limit", 25.0, type=float)
    include_extras = request.args.get("extras", "true").lower() not in ("false", "0", "no")

    date_str = request.args.get("time", "").strip()
    dt_utc = None
    if date_str:
        try:
            if "T" in date_str or " " in date_str:
                raw = date_str.replace("Z", "+00:00").replace(" ", "T")
                dt_utc = dt_mod.fromisoformat(raw)
            else:
                dt_utc = dt_mod.strptime(date_str, "%Y-%m-%d").replace(
                    tzinfo=tz_mod.utc, hour=12, minute=0, second=0)
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=tz_mod.utc)
        except ValueError:
            return jsonify({"success": False,
                            "error": "Invalid time= (use ISO-8601 UTC)"}), 400

    try:
        from solar_scene import build_researched_scene
        if _vr_designations is not None:
            sel = [o for o in _current_selection
                   if str(o.get("pdes", "")).strip() in _vr_designations
                   or str(o.get("name", "")).strip() in _vr_designations]
        elif _current_selection:
            sel = _current_selection
        else:
            sel = []
        count = len(sel) if sel else 0
        print(f"[Researched] Building scene with {count} objects (filter={'active' if _vr_designations is not None else 'off'})")
        result = build_researched_scene(
            dt_utc=dt_utc, mag_limit=mag_limit, selection=sel,
            include_extras=include_extras,
        )
        result["description"] = _vr_description
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/solar_system/search')
def solar_system_search():
    """Search for objects by name/designation in the local cache."""
    query = request.args.get("q", "").strip()
    limit = request.args.get("limit", 20, type=int)
    if not query:
        return jsonify({"success": False, "error": "Query param 'q' required"}), 400
    try:
        from solar_scene import search_objects
        results = search_objects(query, limit=limit)
        return jsonify({"success": True, "count": len(results), "results": results})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/sky/geocentric')
def sky_geocentric():
    """
    Sun + planets + Moon at one instant.

    Geocentric (default): ICRS x,y,z in AU from Earth center (Skyfield).
    Topocentric: pass lat=, lon= (deg, WGS84) and optional height_m= for
    apparent alt/az + distance (Astropy); azimuth from North toward East.

    Query: optional ?date=YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (UTC).
    """
    from datetime import datetime as dt_mod, timezone as tz_mod

    date_str = request.args.get("date", "").strip()
    dt_utc = None
    if date_str:
        try:
            if "T" in date_str or " " in date_str:
                raw = date_str.replace("Z", "+00:00").replace(" ", "T")
                dt_utc = dt_mod.fromisoformat(raw)
            else:
                dt_utc = dt_mod.strptime(date_str, "%Y-%m-%d").replace(
                    tzinfo=tz_mod.utc
                )
                dt_utc = dt_utc.replace(hour=12, minute=0, second=0)
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=tz_mod.utc)
        except ValueError:
            return jsonify(
                {
                    "success": False,
                    "error": "Invalid date= (use YYYY-MM-DD or ISO-8601 UTC)",
                }
            ), 400

    lat_str = request.args.get("lat", "").strip()
    lon_str = request.args.get("lon", "").strip()
    height_str = request.args.get("height_m", "0").strip()
    use_topo = lat_str != "" and lon_str != ""

    if use_topo:
        try:
            lat_deg = float(lat_str)
            lon_deg = float(lon_str)
            height_m = float(height_str) if height_str else 0.0
        except ValueError:
            return jsonify(
                {
                    "success": False,
                    "error": "lat and lon must be numbers (deg WGS84); height_m optional",
                }
            ), 400
        if not (-90.0 <= lat_deg <= 90.0) or not (-180.0 <= lon_deg <= 180.0):
            return jsonify(
                {
                    "success": False,
                    "error": "lat must be [-90,90], lon must be [-180,180]",
                }
            ), 400

    try:
        if use_topo:
            from solar_sky import get_topocentric_bodies

            time_utc, bodies = get_topocentric_bodies(
                lat_deg, lon_deg, height_m, dt_utc
            )
            return jsonify(
                {
                    "success": True,
                    "time_utc": time_utc,
                    "mode": "topocentric",
                    "frame": "AltAz",
                    "unit": "AU",
                    "observer": {
                        "lat_deg": lat_deg,
                        "lon_deg": lon_deg,
                        "height_m": height_m,
                    },
                    "note": "alt_deg, az_deg: apparent horizon coords; az from geographic North toward East (IAU/Astropy). distance_au from observer.",
                    "bodies": bodies,
                }
            )

        from solar_sky import get_geocentric_bodies

        time_utc, bodies = get_geocentric_bodies(dt_utc)
        return jsonify(
            {
                "success": True,
                "time_utc": time_utc,
                "mode": "geocentric",
                "frame": "ICRS",
                "unit": "AU",
                "origin": "geocenter",
                "note": "x,y,z: vector from Earth center to body, ICRS equatorial (Skyfield).",
                "bodies": bodies,
            }
        )
    except ImportError as e:
        return jsonify(
            {
                "success": False,
                "error": "Missing dependency; pip install -r requirements.txt",
                "detail": str(e),
            }
        ), 503
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# LOCATION
# ============================================================================

_cached_location = None

@app.route('/api/location')
def get_location():
    """Auto-detect server location via IP geolocation. Cached after first call."""
    global _cached_location
    if _cached_location:
        return jsonify(_cached_location)
    try:
        import urllib.request
        resp = urllib.request.urlopen("https://ipinfo.io/json", timeout=5)
        data = json.loads(resp.read().decode())
        loc = data.get("loc", "0,0").split(",")
        _cached_location = {
            "success": True,
            "lat": float(loc[0]),
            "lon": float(loc[1]),
            "city": data.get("city", ""),
            "region": data.get("region", ""),
            "country": data.get("country", ""),
            "timezone": data.get("timezone", ""),
        }
        print(f"Location detected: {_cached_location['city']}, {_cached_location['region']} "
              f"({_cached_location['lat']}, {_cached_location['lon']})")
        return jsonify(_cached_location)
    except Exception as e:
        return jsonify({"success": False, "error": str(e),
                        "lat": 51.5074, "lon": -0.1278, "city": "London"}), 200


# ============================================================================
# MOOT AI ENDPOINTS
# ============================================================================

@app.route('/api/moot/hear', methods=['POST'])
def moot_hear():
    """Transcribe audio to text via Whisper. Accepts WAV or raw PCM in body."""
    if not request.data:
        return jsonify({"success": False, "error": "No audio data in request body"}), 400
    try:
        from moot_brain import hear
        transcript = hear(request.data)
        return jsonify({"success": True, "transcript": transcript})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/moot/chat', methods=['POST'])
def moot_chat():
    """
    Chat with Moot. Accepts JSON: {"text": "...", "scene": {...}, "model": "...", "history": [...]}.
    Returns: {"reply": "...", "audio_url": "...", "actions": [...]}.
    """
    data = request.get_json(silent=True)
    if not data or "text" not in data:
        return jsonify({"success": False, "error": "JSON body with 'text' required"}), 400

    text = data["text"]
    scene = data.get("scene")
    model = data.get("model", "llama3.1:8b")
    history = data.get("history")
    do_tts = data.get("tts", True)

    try:
        from moot_brain import think, speak

        result = think(text, scene, model, history)

        audio_url = None
        if do_tts and result["reply"]:
            audio_path = speak(result["reply"])
            audio_id = os.path.basename(audio_path)
            audio_url = f"/api/moot/tts/{audio_id}"

        return jsonify({
            "success": True,
            "reply": result["reply"],
            "actions": result["actions"],
            "audio_url": audio_url,
            "model": result.get("model"),
            "elapsed_s": result.get("elapsed_s"),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/moot/listen', methods=['POST'])
def moot_listen():
    """
    Full pipeline: audio in -> transcript -> LLM -> TTS audio out.
    Accepts WAV/PCM body + query params: ?model=...&scene=JSON
    """
    if not request.data:
        return jsonify({"success": False, "error": "No audio data in request body"}), 400

    scene_str = request.args.get("scene", "").strip()
    model = request.args.get("model", "llama3.1:8b").strip()
    scene = None
    if scene_str:
        try:
            scene = json.loads(scene_str)
        except json.JSONDecodeError:
            pass

    try:
        from moot_brain import process_audio

        result = process_audio(request.data, scene, model)

        audio_url = None
        if result.get("audio_path"):
            audio_id = os.path.basename(result["audio_path"])
            audio_url = f"/api/moot/tts/{audio_id}"

        return jsonify({
            "success": True,
            "transcript": result["transcript"],
            "reply": result["reply"],
            "actions": result.get("actions", []),
            "audio_url": audio_url,
            "timings": result.get("timings"),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/moot/tts/<filename>')
def moot_tts_file(filename):
    """Serve generated TTS audio files."""
    import tempfile
    from flask import send_from_directory
    audio_dir = os.path.join(tempfile.gettempdir(), "moot_audio")
    if not os.path.exists(os.path.join(audio_dir, filename)):
        return jsonify({"success": False, "error": "Audio file not found"}), 404
    return send_from_directory(audio_dir, filename, mimetype="audio/wav")


# ── Multi-source image search ───────────────────────────────────────

def _resolve_object_ids(designation):
    """Resolve a designation to all known IDs via JPL SBDB."""
    try:
        resp = requests.get(
            "https://ssd-api.jpl.nasa.gov/sbdb.api",
            params={'sstr': designation, 'alt-des': 'true', 'alt-spk': 'true'},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            obj = data.get('object', {})
            return {
                'spkid': obj.get('spkid'),
                'des': obj.get('des'),
                'fullname': obj.get('fullname'),
                'name': obj.get('shortname', '').split(maxsplit=1)[-1] if obj.get('shortname') else None,
                'alt_des': obj.get('alt_des', []),
            }
    except Exception as e:
        print(f"  Images: ID resolve failed: {e}", flush=True)
    return {'spkid': None, 'des': designation, 'fullname': None, 'name': None, 'alt_des': []}


def _search_irsa_most(obj_name, catalog='wise_merge', obs_begin='2010 01 01', obs_end='2024 12 31'):
    """Query IRSA MOST for moving-object images. Returns list of image dicts."""
    results = []
    try:
        resp = requests.get(
            "https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most",
            params={
                'catalog': catalog,
                'input_type': 'name_input',
                'obj_name': obj_name,
                'obs_begin': obs_begin,
                'obs_end': obs_end,
                'output_mode': 'Brief',
            },
            timeout=90,
        )
        if resp.status_code != 200:
            return results

        text = resp.text
        lines = text.strip().split('\n')

        # Parse IPAC fixed-width table using pipe positions for column boundaries
        header_line_idx = None
        for idx, line in enumerate(lines):
            if line.startswith('|') and 'ra_obj' in line:
                header_line_idx = idx
                break

        if header_line_idx is None:
            return results

        raw_header = lines[header_line_idx]
        col_bounds = []
        in_col = False
        start = 0
        for i, ch in enumerate(raw_header):
            if ch == '|':
                if in_col:
                    col_bounds.append((start, i))
                    in_col = False
                start = i + 1
                in_col = True
        headers = [raw_header[s:e].strip() for s, e in col_bounds]

        # Skip the type-definition row(s) (also start with |)
        data_start = None
        for idx in range(header_line_idx + 1, len(lines)):
            line = lines[idx]
            if line.startswith('|'):
                continue
            if line.strip():
                data_start = idx
                break

        if data_start is None:
            return results

        workspace_url = None
        for line in lines:
            if line.startswith('\\output_url'):
                workspace_url = line.split('=', 1)[1].strip().strip('"')
                break

        catalog_label = {
            'wise_merge': 'WISE/NEOWISE',
            'ztf': 'ZTF',
            'ptf': 'PTF',
            '2mass': '2MASS',
        }.get(catalog, catalog.upper())

        for line in lines[data_start:]:
            if not line.strip() or line.startswith('\\') or line.startswith('|'):
                continue
            # Extract values using the same column boundaries as the header
            row = {}
            for (s, e), hdr in zip(col_bounds, headers):
                val = line[s:e].strip() if e <= len(line) else line[s:].strip()
                row[hdr] = val

            ra = row.get('ra_obj', '')
            dec = row.get('dec_obj', '')
            band = row.get('band', '')
            mjd = row.get('mjd_obs', '')
            date_obs = row.get('date_obs', '')

            band_label = band
            if catalog.startswith('wise'):
                band_label = {'1': 'W1 (3.4µm)', '2': 'W2 (4.6µm)',
                              '3': 'W3 (12µm)', '4': 'W4 (22µm)'}.get(band, band)
            elif catalog == 'ztf':
                band_label = {'1': 'ZTF-g', '2': 'ZTF-r', '3': 'ZTF-i'}.get(band, band)

            # Build a cutout URL using IRSA SIA if we have RA/Dec
            image_url = None
            if ra and dec:
                try:
                    ra_f, dec_f = float(ra), float(dec)
                    if catalog.startswith('wise'):
                        image_url = (
                            f"https://irsa.ipac.caltech.edu/ibe/data/wise/merge/merge_p1bm_frm/"
                            f"{row.get('scan_id', '')}/{row.get('frame_num', '')}/"
                            f"{row.get('scan_id', '')}_{row.get('frame_num', '')}-"
                            f"w{band}-int-1b.fits"
                        )
                    elif catalog == 'ztf':
                        image_url = (
                            f"https://irsa.ipac.caltech.edu/ibe/data/ztf/products/sci/"
                        )
                except (ValueError, TypeError):
                    pass

            results.append({
                'source': f'IRSA MOST ({catalog_label})',
                'ra': ra,
                'dec': dec,
                'band': band_label,
                'mjd': mjd,
                'date': date_obs.split()[0] if date_obs else '',
                'time': date_obs.split()[1] if date_obs and ' ' in date_obs else '',
                'image_url': image_url,
                'dist_arcsec': row.get('dist_ctr', ''),
                'vmag': row.get('vmag', ''),
                'phase': row.get('phase', ''),
                'sun_dist': row.get('sun_dist', ''),
                'geo_dist': row.get('geo_dist', ''),
            })
    except Exception as e:
        print(f"  Images: IRSA MOST ({catalog}) error: {e}", flush=True)
    return results


def _search_catch(target):
    """Query CATCH for survey images. Returns list of image dicts."""
    results = []
    try:
        resp = requests.get(
            f"https://catch-api.astro.umd.edu/catch",
            params={'target': target, 'cached': 'true'},
            timeout=30,
        )
        if resp.status_code != 200:
            return results

        data = resp.json()
        job_id = data.get('job_id')
        if not job_id:
            return results

        if data.get('queued'):
            import time
            for _ in range(12):
                time.sleep(5)
                check = requests.get(
                    f"https://catch-api.astro.umd.edu/caught/{job_id}",
                    timeout=15,
                )
                if check.status_code == 200:
                    caught = check.json()
                    if caught.get('data') is not None:
                        data = caught
                        break
            else:
                return results
        else:
            caught_resp = requests.get(
                f"https://catch-api.astro.umd.edu/caught/{job_id}",
                timeout=30,
            )
            if caught_resp.status_code == 200:
                data = caught_resp.json()

        for obs in data.get('data', []):
            cutout = obs.get('cutout_url') or obs.get('thumbnail_url') or obs.get('preview_url')
            product_id = obs.get('product_id', '')
            source_name = obs.get('source', 'CATCH')

            results.append({
                'source': f'CATCH ({source_name})',
                'ra': obs.get('ra'),
                'dec': obs.get('dec'),
                'band': obs.get('filter', ''),
                'date': obs.get('date', obs.get('obsdate', '')),
                'mjd': obs.get('mjd', ''),
                'image_url': cutout,
                'product_id': product_id,
                'dist_arcsec': obs.get('delta', ''),
                'vmag': obs.get('vmag', ''),
                'phase': obs.get('phase', ''),
                'sun_dist': obs.get('rh', ''),
                'geo_dist': obs.get('delta', ''),
            })
    except Exception as e:
        print(f"  Images: CATCH error: {e}", flush=True)
    return results


def _get_wikipedia_images(designation, name=None):
    """Get images from the existing Wikipedia data."""
    results = []
    try:
        wiki_data = wikipedia_client.get_object_info(designation, name or designation)
        if wiki_data and isinstance(wiki_data, dict):
            if wiki_data.get('thumbnail'):
                results.append({
                    'source': 'Wikipedia',
                    'image_url': wiki_data['thumbnail'],
                    'title': wiki_data.get('title', ''),
                    'caption': 'Wikipedia article thumbnail',
                })
            for img in wiki_data.get('images', []):
                url = img.get('url', '')
                if url:
                    results.append({
                        'source': 'Wikipedia',
                        'image_url': url,
                        'title': img.get('title', ''),
                        'caption': img.get('mime', ''),
                    })
    except Exception as e:
        print(f"  Images: Wikipedia error: {e}", flush=True)
    return results


@app.route('/api/objects/<designation>/images')
def get_object_images(designation):
    """Search multiple image archives for a solar system object."""
    print(f"  Images: searching for '{designation}'", flush=True)

    ids = _resolve_object_ids(designation)
    obj_name = ids['des'] or designation
    spkid = ids['spkid']
    common_name = ids['name']

    print(f"  Images: resolved -> name='{obj_name}', spkid={spkid}", flush=True)

    sources_requested = request.args.get('sources', 'all')
    all_images = []
    source_meta = {}

    # IRSA MOST — WISE/NEOWISE
    if sources_requested in ('all', 'wise'):
        wise_imgs = _search_irsa_most(obj_name, catalog='wise_merge')
        all_images.extend(wise_imgs)
        source_meta['wise'] = {
            'name': 'WISE/NEOWISE (IRSA MOST)',
            'count': len(wise_imgs),
            'index_type': 'object name',
            'query_value': obj_name,
        }
        print(f"  Images: WISE/NEOWISE -> {len(wise_imgs)} results", flush=True)

    # IRSA MOST — ZTF (limit to 1 year at a time to avoid timeouts)
    if sources_requested in ('all', 'ztf'):
        ztf_imgs = _search_irsa_most(obj_name, catalog='ztf',
                                      obs_begin='2023 01 01', obs_end='2024 06 30')
        all_images.extend(ztf_imgs)
        source_meta['ztf'] = {
            'name': 'ZTF (IRSA MOST)',
            'count': len(ztf_imgs),
            'index_type': 'object name',
            'query_value': obj_name,
        }
        print(f"  Images: ZTF -> {len(ztf_imgs)} results", flush=True)

    # CATCH — multi-survey (NEAT, LONEOS, Catalina, ATLAS, etc.)
    if sources_requested in ('all', 'catch'):
        catch_target = obj_name.split()[0] if obj_name else designation
        catch_imgs = _search_catch(catch_target)
        all_images.extend(catch_imgs)
        source_meta['catch'] = {
            'name': 'CATCH (NEAT/Catalina/ATLAS/etc.)',
            'count': len(catch_imgs),
            'index_type': 'target designation',
            'query_value': catch_target,
        }
        print(f"  Images: CATCH -> {len(catch_imgs)} results", flush=True)

    # Wikipedia images
    if sources_requested in ('all', 'wikipedia'):
        wiki_imgs = _get_wikipedia_images(designation, common_name)
        all_images.extend(wiki_imgs)
        source_meta['wikipedia'] = {
            'name': 'Wikipedia',
            'count': len(wiki_imgs),
            'index_type': 'article title',
            'query_value': f"{designation} {common_name}" if common_name else designation,
        }
        print(f"  Images: Wikipedia -> {len(wiki_imgs)} results", flush=True)

    print(f"  Images: total {len(all_images)} across {len(source_meta)} sources", flush=True)

    return jsonify({
        'designation': designation,
        'resolved': ids,
        'sources': source_meta,
        'total': len(all_images),
        'images': all_images,
    })


# ── Explorer Dispatch: Autonomous Object Investigation ─────────────

@app.route('/api/objects/<designation>/explore', methods=['POST'])
def explore_object(designation):
    """Deploy a robot IE to autonomously investigate a target object."""
    t0 = time.time()
    print(f"\n[Explorer] Mission dispatched -> {designation}", flush=True)

    ids = _resolve_object_ids(designation)
    obj_name = ids.get('name') or ids.get('des') or designation

    sources_queried = []
    jpl_phys = {}
    ssodnet_phys = {}
    observation_count = 0
    catch_count = 0
    wikipedia_summary = ""
    errors = []

    def _query_jpl():
        nonlocal jpl_phys
        try:
            data = jpl_client.get_object_details(designation)
            if data and 'phys_par' in data:
                for p in (data['phys_par'] or []):
                    jpl_phys[p.get('name', '')] = {
                        'value': p.get('value'),
                        'units': p.get('units', ''),
                        'ref': p.get('ref', ''),
                    }
            if data and 'object' in data:
                obj = data['object']
                oc = obj.get('orbit_class', {})
                jpl_phys['_orbit_class'] = oc.get('name', '') if isinstance(oc, dict) else ''
                jpl_phys['_neo'] = obj.get('neo', False)
                jpl_phys['_pha'] = obj.get('pha', False)
            sources_queried.append('JPL_SBDB')
        except Exception as e:
            errors.append(f"JPL: {e}")

    def _query_ssodnet():
        nonlocal ssodnet_phys
        try:
            data = ssodnet_client.get_sso_card(obj_name)
            if data and isinstance(data, dict):
                phys = data.get('parameters', {})
                if isinstance(phys, dict):
                    phys = phys.get('physical', phys)
                if isinstance(phys, dict):
                    ssodnet_phys = phys
            sources_queried.append('SsODNet')
        except Exception as e:
            errors.append(f"SsODNet: {e}")

    def _query_irsa():
        nonlocal observation_count
        try:
            wise_obs = _search_irsa_most(obj_name, catalog='wise_merge',
                                          obs_begin='2010 01 01', obs_end='2024 12 31')
            observation_count += len(wise_obs)
            sources_queried.append('IRSA_WISE')
        except Exception as e:
            errors.append(f"IRSA: {e}")

    def _query_catch():
        nonlocal catch_count
        try:
            catch_obs = _search_catch(obj_name)
            catch_count = len(catch_obs)
            sources_queried.append('CATCH')
        except Exception as e:
            errors.append(f"CATCH: {e}")

    def _query_wikipedia():
        nonlocal wikipedia_summary
        try:
            wiki = wikipedia_client.get_object_info(designation, obj_name)
            if wiki and isinstance(wiki, dict):
                wikipedia_summary = wiki.get('summary', '')[:500]
            sources_queried.append('Wikipedia')
        except Exception as e:
            errors.append(f"Wikipedia: {e}")

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [
            pool.submit(_query_jpl),
            pool.submit(_query_ssodnet),
            pool.submit(_query_irsa),
            pool.submit(_query_catch),
            pool.submit(_query_wikipedia),
        ]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception:
                pass

    # ── Cross-reference and gap analysis ──
    def _ssod_val(field_data):
        """Extract value from SsODNet field (handles nested dicts)."""
        if field_data is None:
            return None
        if isinstance(field_data, (int, float)):
            return field_data
        if isinstance(field_data, str):
            return field_data or None
        if isinstance(field_data, dict):
            return field_data.get('value')
        return None

    known_fields = {
        'diameter': None, 'albedo': None, 'rotation_period': None,
        'spectral_type': None, 'mass': None, 'density': None,
        'absolute_magnitude': None, 'taxonomy': None,
    }

    # JPL phys_par extraction
    if jpl_phys.get('diameter'):
        known_fields['diameter'] = f"{jpl_phys['diameter'].get('value')} {jpl_phys['diameter'].get('units', 'km')}"
    if jpl_phys.get('albedo'):
        known_fields['albedo'] = jpl_phys['albedo'].get('value')
    if jpl_phys.get('rot_per'):
        known_fields['rotation_period'] = f"{jpl_phys['rot_per'].get('value')} {jpl_phys['rot_per'].get('units', 'h')}"
    if jpl_phys.get('spec_B') or jpl_phys.get('spec_T'):
        known_fields['spectral_type'] = jpl_phys.get('spec_B', {}).get('value') or jpl_phys.get('spec_T', {}).get('value')
    if jpl_phys.get('H'):
        known_fields['absolute_magnitude'] = jpl_phys['H'].get('value')

    # SsODNet extraction (fills gaps left by JPL)
    ssod_diameter = _ssod_val(ssodnet_phys.get('diameter'))
    ssod_albedo = _ssod_val(ssodnet_phys.get('albedo'))
    ssod_mass = _ssod_val(ssodnet_phys.get('mass'))
    ssod_density = _ssod_val(ssodnet_phys.get('density'))
    ssod_absmag = _ssod_val(ssodnet_phys.get('absolute_magnitude'))

    ssod_taxonomy = None
    tax_data = ssodnet_phys.get('taxonomy')
    if isinstance(tax_data, dict):
        ssod_taxonomy = tax_data.get('class') or tax_data.get('complex')
    elif isinstance(tax_data, str):
        ssod_taxonomy = tax_data

    ssod_spin = None
    spins = ssodnet_phys.get('spins', {})
    if isinstance(spins, dict):
        for k, v in spins.items():
            if isinstance(v, dict) and 'value' in v:
                ssod_spin = v['value']
                break

    if ssod_diameter and not known_fields['diameter']:
        known_fields['diameter'] = f"{ssod_diameter} km"
    if ssod_albedo and not known_fields['albedo']:
        known_fields['albedo'] = str(ssod_albedo)
    if ssod_mass:
        known_fields['mass'] = f"{ssod_mass:.3e} kg" if isinstance(ssod_mass, (int, float)) else str(ssod_mass)
    if ssod_density:
        known_fields['density'] = f"{ssod_density} kg/m³" if isinstance(ssod_density, (int, float)) else str(ssod_density)
    if ssod_taxonomy:
        known_fields['taxonomy'] = str(ssod_taxonomy)
    if ssod_absmag and not known_fields['absolute_magnitude']:
        known_fields['absolute_magnitude'] = str(ssod_absmag)
    if ssod_spin and not known_fields['rotation_period']:
        known_fields['rotation_period'] = f"{ssod_spin} h"

    data_gaps = [field for field, val in known_fields.items() if val is None]
    present = [field for field, val in known_fields.items() if val is not None]
    completeness = len(present) / max(len(known_fields), 1)

    # ── Cross-reference checks ──
    cross_refs = {}
    jpl_diam_val = jpl_phys.get('diameter', {}).get('value') if isinstance(jpl_phys.get('diameter'), dict) else None
    if jpl_diam_val and ssod_diameter:
        try:
            j_d = float(jpl_diam_val)
            s_d = float(ssod_diameter)
            if j_d > 0 and s_d > 0:
                pct_diff = abs(j_d - s_d) / j_d * 100
                cross_refs['diameter_agreement'] = {
                    'jpl': j_d, 'ssodnet': s_d,
                    'difference_pct': round(pct_diff, 1),
                    'status': 'consistent' if pct_diff < 20 else 'discrepant',
                }
        except (ValueError, TypeError):
            pass

    # ── Build mission report ──
    report_lines = [
        f"# Exploration Report: {ids.get('fullname') or designation}",
        "",
        f"**SPK ID:** {ids.get('spkid', 'unknown')}  ",
        f"**Designation:** {ids.get('des', designation)}  ",
        f"**Orbit class:** {jpl_phys.get('_orbit_class', 'unknown')}  ",
        f"**NEO:** {'Yes' if jpl_phys.get('_neo') else 'No'} | "
        f"**PHA:** {'Yes' if jpl_phys.get('_pha') else 'No'}",
        "",
        "## Physical Properties",
    ]
    for field, val in known_fields.items():
        label = field.replace('_', ' ').title()
        report_lines.append(f"- **{label}:** {val if val else '❌ MISSING'}")

    report_lines.append("")
    report_lines.append("## Observation Coverage")
    report_lines.append(f"- WISE/NEOWISE detections: {observation_count}")
    report_lines.append(f"- CATCH survey detections: {catch_count}")

    if cross_refs:
        report_lines.append("")
        report_lines.append("## Cross-Reference Analysis")
        for key, info in cross_refs.items():
            label = key.replace('_', ' ').title()
            report_lines.append(
                f"- **{label}:** JPL={info.get('jpl')} vs SsODNet={info.get('ssodnet')} "
                f"({info.get('difference_pct')}% difference — {info.get('status')})"
            )

    report_lines.append("")
    report_lines.append(f"## Completeness: {completeness:.0%}")
    if data_gaps:
        report_lines.append(f"**Data gaps:** {', '.join(g.replace('_', ' ') for g in data_gaps)}")
    else:
        report_lines.append("No data gaps identified — all key fields populated.")

    if wikipedia_summary:
        report_lines.append("")
        report_lines.append("## Context")
        report_lines.append(wikipedia_summary)

    if errors:
        report_lines.append("")
        report_lines.append("## Data Link Errors")
        for err in errors:
            report_lines.append(f"- {err}")

    duration = time.time() - t0
    report_lines.append("")
    report_lines.append(f"---")
    report_lines.append(f"*Mission completed in {duration:.1f}s. "
                        f"Sources queried: {', '.join(sources_queried)}.*")

    findings = "\n".join(report_lines)
    print(f"[Explorer] Mission complete -> {designation} ({duration:.1f}s, "
          f"completeness={completeness:.0%}, gaps={len(data_gaps)})", flush=True)

    return jsonify({
        'designation': designation,
        'resolved': ids,
        'findings_summary': findings,
        'completeness_score': completeness,
        'data_gaps': data_gaps,
        'known_fields': {k: v for k, v in known_fields.items() if v is not None},
        'cross_references': cross_refs,
        'observation_count': observation_count + catch_count,
        'sources_queried': sources_queried,
        'duration_seconds': round(duration, 2),
        'structured_data': {
            'known_fields': known_fields,
            'cross_references': cross_refs,
            'observation_counts': {
                'wise_neowise': observation_count,
                'catch_surveys': catch_count,
            },
            'errors': errors,
        },
    })


if __name__ == '__main__':
    port = 5050
    print(f"\n{'='*60}")
    print(f"Solar System Facility — Space-Based Data Centre")
    print(f"{'='*60}")
    print(f"\nServer starting on http://localhost:{port}")
    print(f"\nAvailable endpoints:")
    print(f"  - Main interface: http://localhost:{port}/")
    print(f"  - Sky (VR):   /api/sky/geocentric?date=YYYY-MM-DD")
    print(f"  - Sky topo:   /api/sky/geocentric?lat=..&lon=..&height_m=0")
    print(f"  - 3D scene:   /api/solar_system/scene?observer=earth&mag_limit=20")
    print(f"  - Search:     /api/solar_system/search?q=eros")
    print(f"  - Explorer:   POST /api/objects/<des>/explore  (deploy robot IE)")
    print(f"  - Moot hear:  POST /api/moot/hear  (WAV body -> transcript)")
    print(f"  - Moot chat:  POST /api/moot/chat  (JSON -> reply + TTS)")
    print(f"  - Moot full:  POST /api/moot/listen (WAV -> transcript+reply+TTS)")
    print(f"  - Moot audio: GET  /api/moot/tts/<file>.wav")
    print(f"\n{'='*60}\n")

    use_debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=use_debug, port=port, host='0.0.0.0')

