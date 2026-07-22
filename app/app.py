from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
import psycopg2
import psycopg2.extras
import os
import subprocess
import platform
import time
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# Prometheus Gauges - ye labels ke saath device counts track karenge
DEVICES_UP = Gauge("netmonitor_devices_up", "Number of devices currently up")
DEVICES_DOWN = Gauge("netmonitor_devices_down", "Number of devices currently down")
DEVICES_TOTAL = Gauge("netmonitor_devices_total", "Total number of devices being monitored")

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "netmonitor")
DB_USER = os.environ.get("DB_USER", "netadmin")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "netpass123")
DB_PORT = os.environ.get("DB_PORT", "5432")


def get_db_connection(retries=10, delay=2):
    """Postgres container thoda late start hota hai - isliye retry logic zaroori hai."""
    last_error = None
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT,
            )
            return conn
        except psycopg2.OperationalError as e:
            last_error = e
            time.sleep(delay)
    raise last_error


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            ip_address VARCHAR(50) NOT NULL,
            device_type VARCHAR(50) NOT NULL,
            location VARCHAR(100),
            status VARCHAR(20) DEFAULT 'unknown',
            last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def ping_host(ip_address):
    """Actual ping karta hai device ko - up/down status ke liye."""
    param = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        result = subprocess.run(
            ["ping", param, "1", "-W", "2", ip_address],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
        return "up" if result.returncode == 0 else "down"
    except Exception:
        return "down"


@app.route("/")
def index():
    search = request.args.get("search", "").strip()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if search:
        cur.execute(
            "SELECT * FROM devices WHERE name ILIKE %s OR device_type ILIKE %s ORDER BY id DESC",
            (f"%{search}%", f"%{search}%"),
        )
    else:
        cur.execute("SELECT * FROM devices ORDER BY id DESC")
    devices = cur.fetchall()
    cur.close()
    conn.close()

    up_count = sum(1 for d in devices if d["status"] == "up")
    down_count = sum(1 for d in devices if d["status"] == "down")

    return render_template(
        "index.html",
        devices=devices,
        search=search,
        total=len(devices),
        up_count=up_count,
        down_count=down_count,
    )


@app.route("/add", methods=["POST"])
def add_device():
    name = request.form["name"]
    ip_address = request.form["ip_address"]
    device_type = request.form["device_type"]
    location = request.form.get("location", "")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO devices (name, ip_address, device_type, location) VALUES (%s, %s, %s, %s)",
        (name, ip_address, device_type, location),
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("index"))


@app.route("/delete/<int:device_id>")
def delete_device(device_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM devices WHERE id = %s", (device_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("index"))


@app.route("/check/<int:device_id>")
def check_device(device_id):
    """Ek device ko ping karke status update karta hai."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT ip_address FROM devices WHERE id = %s", (device_id,))
    device = cur.fetchone()

    if device:
        status = ping_host(device["ip_address"])
        cur.execute(
            "UPDATE devices SET status = %s, last_checked = CURRENT_TIMESTAMP WHERE id = %s",
            (status, device_id),
        )
        conn.commit()

    cur.close()
    conn.close()
    return redirect(url_for("index"))


@app.route("/check-all")
def check_all_devices():
    """Saare devices ko ek saath ping karta hai."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, ip_address FROM devices")
    devices = cur.fetchall()

    for device in devices:
        status = ping_host(device["ip_address"])
        cur.execute(
            "UPDATE devices SET status = %s, last_checked = CURRENT_TIMESTAMP WHERE id = %s",
            (status, device["id"]),
        )

    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("index"))


# Prometheus / monitoring ke liye simple JSON metrics endpoint (Phase 3 mein use hoga)
@app.route("/api/metrics")
def api_metrics():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT status, COUNT(*) as count FROM devices GROUP BY status")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({row["status"]: row["count"] for row in rows})


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/metrics")
def metrics():
    """Prometheus is endpoint ko periodically scrape karega."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT status, COUNT(*) as count FROM devices GROUP BY status")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    counts = {row["status"]: row["count"] for row in rows}
    up = counts.get("up", 0)
    down = counts.get("down", 0)
    total = up + down + counts.get("unknown", 0)

    DEVICES_UP.set(up)
    DEVICES_DOWN.set(down)
    DEVICES_TOTAL.set(total)

    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
