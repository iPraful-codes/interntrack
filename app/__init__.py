"""InternTrack: a small Flask + SQLite app for tracking job applications."""
import sqlite3
from datetime import date
from pathlib import Path

from flask import Flask, g, jsonify, render_template, request

STATUSES = ("Wishlist", "Applied", "Interview", "Offer", "Rejected")
FIELDS = ("company", "role", "location", "status", "applied_on", "link", "notes")
SCHEMA = Path(__file__).with_name("schema.sql")


def validate(data, partial=False):
    """Return (clean_data, errors). Only whitelisted fields are kept."""
    data = {k: v.strip() if isinstance(v, str) else v for k, v in data.items() if k in FIELDS}
    errors = []
    for field in ("company", "role"):
        if (field in data or not partial) and not data.get(field):
            errors.append(f"{field} is required")
    if "status" in data and data["status"] not in STATUSES:
        errors.append(f"status must be one of: {', '.join(STATUSES)}")
    if "applied_on" in data:
        try:
            date.fromisoformat(data["applied_on"])
        except (TypeError, ValueError):
            errors.append("applied_on must be a date in YYYY-MM-DD format")
    if data.get("link") and not data["link"].startswith(("http://", "https://")):
        errors.append("link must start with http:// or https://")
    return data, errors


def create_app(config=None):
    app = Flask(__name__)
    app.config["DATABASE"] = str(Path(app.root_path).parent / "interntrack.db")
    if config:
        app.config.update(config)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def fetch(app_id):
        row = get_db().execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
        return dict(row) if row else None

    with app.app_context():
        get_db().executescript(SCHEMA.read_text())

    @app.get("/")
    def index():
        return render_template("index.html", statuses=STATUSES)

    @app.get("/api/applications")
    def list_applications():
        sql, args = "SELECT * FROM applications WHERE 1 = 1", []
        status = request.args.get("status")
        if status:
            sql += " AND status = ?"
            args.append(status)
        query = request.args.get("q", "").strip()
        if query:
            sql += " AND (company LIKE ? OR role LIKE ?)"
            args += [f"%{query}%"] * 2
        sql += " ORDER BY applied_on DESC, id DESC"
        return jsonify([dict(r) for r in get_db().execute(sql, args)])

    @app.post("/api/applications")
    def create_application():
        data, errors = validate(request.get_json(silent=True) or {})
        if errors:
            return jsonify(errors=errors), 400
        # Column names come from the FIELDS whitelist; values are always parameterised.
        columns = ", ".join(data)
        marks = ", ".join("?" * len(data))
        db = get_db()
        cur = db.execute(f"INSERT INTO applications ({columns}) VALUES ({marks})", list(data.values()))
        db.commit()
        return jsonify(fetch(cur.lastrowid)), 201

    @app.put("/api/applications/<int:app_id>")
    def update_application(app_id):
        if not fetch(app_id):
            return jsonify(errors=["application not found"]), 404
        data, errors = validate(request.get_json(silent=True) or {}, partial=True)
        if not data:
            errors.append("no valid fields to update")
        if errors:
            return jsonify(errors=errors), 400
        assignments = ", ".join(f"{column} = ?" for column in data)
        db = get_db()
        db.execute(f"UPDATE applications SET {assignments} WHERE id = ?", [*data.values(), app_id])
        db.commit()
        return jsonify(fetch(app_id))

    @app.delete("/api/applications/<int:app_id>")
    def delete_application(app_id):
        db = get_db()
        cur = db.execute("DELETE FROM applications WHERE id = ?", (app_id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify(errors=["application not found"]), 404
        return "", 204

    @app.get("/api/stats")
    def stats():
        db = get_db()
        by_status = dict.fromkeys(STATUSES, 0)
        for row in db.execute("SELECT status, COUNT(*) AS n FROM applications GROUP BY status"):
            by_status[row["status"]] = row["n"]
        # Monday of each week; wishlist items are excluded because they were never sent.
        weekly = [
            dict(row)
            for row in db.execute(
                """SELECT date(applied_on, 'weekday 0', '-6 days') AS week_start, COUNT(*) AS n
                   FROM applications WHERE status != 'Wishlist'
                   GROUP BY week_start ORDER BY week_start"""
            )
        ]
        sent = sum(n for status, n in by_status.items() if status != "Wishlist")
        reached = by_status["Interview"] + by_status["Offer"]
        return jsonify(
            total=sum(by_status.values()),
            by_status=by_status,
            weekly=weekly,
            interview_rate=round(100 * reached / sent, 1) if sent else 0,
        )

    return app
