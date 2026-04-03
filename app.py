# ======================================================
# DropNote - Backup Delivery Instruction System
# app.py
# ======================================================
# This file is the BRAIN of our app.
# It runs a web server and handles saving/reading data.
#
# To run this file:
#   python app.py
#
# Then open your browser and go to:
#   http://127.0.0.1:5000
# ======================================================

from flask import Flask, request, jsonify, render_template, send_from_directory
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename

# Create the Flask app (our web server)
app = Flask(__name__)

# Folder where agent photos are saved
UPLOAD_FOLDER = "/data/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # creates folder if it doesn't exist


# ------------------------------------------------------
# STEP 1: DATABASE SETUP
# We use SQLite - it saves data in a simple file.
# No installation needed. File is created automatically.
# ------------------------------------------------------

def create_table():
    # Connect to database file (creates it if it doesn't exist)
    conn = sqlite3.connect("/data/dropnote.db")

    # Create our table with these columns:
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

    conn.commit()  # save the changes
    conn.close()   # close the connection


# ------------------------------------------------------
# STEP 2: PAGE ROUTES
# A route is a URL that shows a page.
# ------------------------------------------------------

# When someone visits http://127.0.0.1:5000/
@app.route("/")
def customer_page():
    return render_template("customer.html")


# When someone visits http://127.0.0.1:5000/agent
@app.route("/agent")
def agent_page():
    return render_template("agent.html")


# When someone visits http://127.0.0.1:5000/admin
@app.route("/admin")
def admin_page():
    conn = sqlite3.connect("/data/dropnote.db")
    conn.row_factory = sqlite3.Row  # so we can use row["name"] instead of row[0]
    records = conn.execute("SELECT * FROM preferences ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin.html", records=records)


# ------------------------------------------------------
# STEP 3: API ROUTES
# These don't show pages - they handle data.
# Frontend sends data here using fetch().
# ------------------------------------------------------

# Customer saves their backup preference
@app.route("/api/save", methods=["POST"])
def save_preference():
    # Read the data sent from customer.html
    data    = request.get_json()
    name    = data.get("name", "").strip()
    phone   = data.get("phone", "").strip()
    address = data.get("address", "").strip()
    leave_at = data.get("leave_at", "").strip()
    note    = data.get("note", "").strip()

    # Check all required fields are filled
    if not name or not phone or not address or not leave_at:
        return jsonify({"success": False, "message": "Please fill all fields"})

    # Save to database
    conn = sqlite3.connect("/data/dropnote.db")
    conn.execute("""
        INSERT INTO preferences (name, phone, address, leave_at, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, phone, address, leave_at, note, datetime.now().strftime("%d-%m-%Y %H:%M")))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Preference saved!"})


# Agent looks up a customer by phone number
@app.route("/api/lookup", methods=["POST"])
def lookup():
    data  = request.get_json()
    phone = data.get("phone", "").strip()

    if not phone:
        return jsonify({"success": False, "message": "Please enter a phone number"})

    # Search database for this phone number
    conn = sqlite3.connect("/data/dropnote.db")
    conn.row_factory = sqlite3.Row
    record = conn.execute(
        "SELECT * FROM preferences WHERE phone = ? AND status = 'pending' ORDER BY id DESC LIMIT 1",
        (phone,)
    ).fetchone()
    conn.close()

    if not record:
        return jsonify({"success": False, "message": "No preference found for this number"})

    # Return the delivery instructions
    return jsonify({
        "success":  True,
        "id":       record["id"],
        "name":     record["name"],
        "address":  record["address"],
        "leave_at": record["leave_at"],
        "note":     record["note"] or "None"
    })


# Agent uploads photo and marks delivery as done
# Note: photo uploads use request.files (not request.get_json)
# because files cannot be sent as JSON
@app.route("/api/done", methods=["POST"])
def mark_done():
    record_id = request.form.get("id")   # get record ID from form
    photo     = request.files.get("photo")  # get the uploaded photo file

    # Make sure both are provided
    if not record_id:
        return jsonify({"success": False, "message": "Missing record ID"})

    if not photo or photo.filename == "":
        return jsonify({"success": False, "message": "Please upload a photo proof"})

    # Save the photo with a safe filename
    # secure_filename removes any dangerous characters from filename
    filename = secure_filename("proof_" + record_id + "_" + photo.filename)
    photo.save(os.path.join(UPLOAD_FOLDER, filename))

    # Update database - mark as delivered and save photo filename
    conn = sqlite3.connect("/data/dropnote.db")
    conn.execute(
        "UPDATE preferences SET status = 'delivered', photo = ? WHERE id = ?",
        (filename, record_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Delivery marked complete!"})


# Serve uploaded photos when admin clicks them
@app.route("/static/uploads/<filename>")
def uploaded_photo(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ------------------------------------------------------
# START THE SERVER
# ------------------------------------------------------
if __name__ == "__main__":
    create_table()  # make sure our table exists
    print("Server running at http://127.0.0.1:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
