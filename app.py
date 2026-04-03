# ======================================================
# DropNote - Backup Delivery Instruction System
# app.py
# ======================================================

from flask import Flask, request, jsonify, render_template, send_from_directory
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

# On Railway /data exists (permanent Volume storage)
# On laptop it doesn't exist so we use local folder
if os.path.exists("/data"):
    DB_PATH       = "/data/dropnote.db"
    UPLOAD_FOLDER = "/data/uploads"
else:
    DB_PATH       = "dropnote.db"
    UPLOAD_FOLDER = "static/uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ------------------------------------------------------
# DATABASE SETUP
# ------------------------------------------------------

def create_table():
    # Creates the table if it doesn't exist yet
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            phone         TEXT NOT NULL,
            address       TEXT NOT NULL,
            leave_at      TEXT NOT NULL,
            note          TEXT,
            status        TEXT DEFAULT 'pending',
            photo         TEXT,
            created_at    TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Runs when app starts — works both locally and on Railway
create_table()


# ------------------------------------------------------
# PAGE ROUTES
# ------------------------------------------------------

@app.route("/")
def customer_page():
    return render_template("customer.html")

@app.route("/agent")
def agent_page():
    return render_template("agent.html")

@app.route("/admin")
def admin_page():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    records = conn.execute("SELECT * FROM preferences ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin.html", records=records)

# Serve uploaded photos
@app.route("/uploads/<filename>")
def uploaded_photo(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ------------------------------------------------------
# API ROUTES
# ------------------------------------------------------

@app.route("/api/save", methods=["POST"])
def save_preference():
    data     = request.get_json()
    name     = data.get("name", "").strip()
    phone    = data.get("phone", "").strip()
    address  = data.get("address", "").strip()
    leave_at = data.get("leave_at", "").strip()
    note     = data.get("note", "").strip()

    if not name or not phone or not address or not leave_at:
        return jsonify({"success": False, "message": "Please fill all fields"})

    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO preferences (name, phone, address, leave_at, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, phone, address, leave_at, note, datetime.now().strftime("%d-%m-%Y %H:%M")))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Preference saved!"})


@app.route("/api/lookup", methods=["POST"])
def lookup():
    data  = request.get_json()
    phone = data.get("phone", "").strip()

    if not phone:
        return jsonify({"success": False, "message": "Please enter a phone number"})

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    record = conn.execute(
        "SELECT * FROM preferences WHERE phone = ? AND status = 'pending' ORDER BY id DESC LIMIT 1",
        (phone,)
    ).fetchone()
    conn.close()

    if not record:
        return jsonify({"success": False, "message": "No preference found for this number"})

    return jsonify({
        "success":  True,
        "id":       record["id"],
        "name":     record["name"],
        "address":  record["address"],
        "leave_at": record["leave_at"],
        "note":     record["note"] or "None"
    })


@app.route("/api/done", methods=["POST"])
def mark_done():
    record_id = request.form.get("id")
    photo     = request.files.get("photo")

    if not record_id:
        return jsonify({"success": False, "message": "Missing record ID"})

    if not photo or photo.filename == "":
        return jsonify({"success": False, "message": "Please upload a photo proof"})

    filename = secure_filename("proof_" + str(record_id) + "_" + photo.filename)
    photo.save(os.path.join(UPLOAD_FOLDER, filename))

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE preferences SET status = 'delivered', photo = ? WHERE id = ?",
        (filename, record_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Delivery marked complete!"})


# ------------------------------------------------------
# START THE SERVER
# ------------------------------------------------------
if __name__ == "__main__":
    print("Server running at http://127.0.0.1:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
