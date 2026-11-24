import os
from urllib.parse import quote
from datetime import date

from flask import Flask, jsonify, request, send_from_directory, render_template, render_template_string, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error

from email_service import send_appointment_email


app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "careplus-local-development-key-change-before-deployment"
)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

DB_CONFIG = {
    "host": os.getenv("CAREPLUS_DB_HOST"),
    "port": int(os.getenv("CAREPLUS_DB_PORT", "4000")),
    "user": os.getenv("CAREPLUS_DB_USER"),
    "password": os.getenv("CAREPLUS_DB_PASSWORD"),
    "database": os.getenv("CAREPLUS_DB_NAME", "careplus_db"),
    "ssl_verify_cert": True,
    "ssl_verify_identity": True,
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def close_db(conn, cur):
    if cur:
        cur.close()
    if conn and conn.is_connected():
        conn.close()


def db_error(error):
    app.logger.exception("CarePlus database error: %s", error)
    return jsonify({
        "success": False,
        "message": "Database connection/query failed. Check XAMPP MySQL and config."
    }), 500


def convert_dates(rows):
    for row in rows:
        for key, value in row.items():
            if hasattr(value, "isoformat"):
                row[key] = value.isoformat()
            elif hasattr(value, "total_seconds"):
                row[key] = str(value)
    return rows


# HOME PAGE
@app.get("/")
def home():
    return render_template("index.html")


# NAVIGATION PAGES
# The Hospitals menu uses the existing hospital-and-doctor listing.
@app.get("/hospitals")
def hospitals_page():
    return redirect("/doctors")


@app.get("/about")
def about_page():
    return render_template_string("""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>About CarePlus</title>
      <style>
        *{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;color:#17365d;background:#f4f8fc}
        nav{background:#fff;padding:20px 5%;display:flex;justify-content:space-between;align-items:center;box-shadow:0 2px 12px #17365d12}
        .brand{font-size:28px;font-weight:800;color:#147db8;text-decoration:none}.brand span{color:#16b6a5}
        nav a{color:#244766;text-decoration:none;margin-left:22px;font-weight:600}
        .hero{padding:65px 20px;text-align:center;background:linear-gradient(120deg,#e8f5ff,#e5faf5)}
        .hero h1{font-size:42px;margin:0 0 14px}.hero p{font-size:18px;color:#61758b}
        main{max-width:1000px;margin:35px auto;padding:0 20px}
        .panel{background:white;padding:30px;border-radius:18px;box-shadow:0 8px 30px #17365d0c;margin-bottom:20px;line-height:1.8}
        h2{color:#117eb7;margin-top:0}.back{display:inline-block;margin-top:10px;padding:12px 20px;border:1px solid #1685c5;border-radius:10px;color:#117eb7;text-decoration:none;font-weight:700}
        @media(max-width:650px){nav{align-items:flex-start;gap:12px;flex-direction:column}nav a{margin:0 14px 0 0}.hero h1{font-size:32px}}
      </style>
    </head>
    <body>
      <nav><a class="brand" href="/">Care<span>Plus</span></a>
        <div><a href="/">Home</a><a href="/hospitals">Hospitals</a><a href="/doctors">Hospitals &amp; Doctors</a><a href="/contact">Contact</a></div>
      </nav>
      <header class="hero"><h1>About CarePlus</h1>
        <p>Making hospital appointments simpler, faster and more convenient.</p></header>
      <main>
        <section class="panel"><h2>Who We Are</h2>
          <p>CarePlus is an online hospital appointment system designed to help patients explore hospitals, discover doctors and find appointment slots in one place.</p>
        </section>
        <section class="panel"><h2>Our Mission</h2>
          <p>Our aim is to reduce avoidable waiting and make the appointment process easier for patients and hospital staff through a simple digital experience.</p>
        </section>
        <section class="panel"><h2>What You Can Do</h2>
          <p>Explore listed hospitals, view doctors associated with a hospital, check available appointment slots, book an appointment and review your appointments from your patient account.</p>
          <a class="back" href="/hospitals">Explore Hospitals</a>
        </section>
      </main>
    </body></html>
    """)


@app.get("/contact")
def contact_page():
    return render_template_string("""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Contact CarePlus</title>
      <style>
        *{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;color:#17365d;background:#f4f8fc}
        nav{background:#fff;padding:20px 5%;display:flex;justify-content:space-between;align-items:center;box-shadow:0 2px 12px #17365d12}
        .brand{font-size:28px;font-weight:800;color:#147db8;text-decoration:none}.brand span{color:#16b6a5}
        nav a{color:#244766;text-decoration:none;margin-left:22px;font-weight:600}
        .hero{padding:60px 20px;text-align:center;background:linear-gradient(120deg,#e8f5ff,#e5faf5)}
        .hero h1{font-size:42px;margin:0 0 14px}.hero p{font-size:18px;color:#61758b}
        main{max-width:900px;margin:35px auto;padding:0 20px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px}
        .card{background:#fff;padding:26px;border-radius:16px;box-shadow:0 8px 30px #17365d0c}
        h2{margin-top:0;color:#117eb7}.card p{line-height:1.7;color:#61758b}.card a{color:#117eb7;font-weight:700;text-decoration:none;overflow-wrap:anywhere}
        .note{margin-top:22px;background:#e8f5ff;padding:18px;border-radius:12px;line-height:1.7}
        @media(max-width:650px){nav{align-items:flex-start;gap:12px;flex-direction:column}nav a{margin:0 14px 0 0}.hero h1{font-size:32px}}
      </style>
    </head>
    <body>
      <nav><a class="brand" href="/">Care<span>Plus</span></a>
        <div><a href="/">Home</a><a href="/hospitals">Hospitals</a><a href="/doctors">Hospitals &amp; Doctors</a><a href="/about">About Us</a></div>
      </nav>
      <header class="hero"><h1>Contact Us</h1>
        <p>We're here to help you with the CarePlus appointment system.</p></header>
      <main>
        <div class="grid">
          <section class="card"><h2>General Support</h2><p>For help using the website or booking an appointment, please contact the CarePlus project team.</p></section>
          <section class="card"><h2>Email</h2><p>Send your questions by email:</p><a href="mailto:careplus.support@example.com">careplus.support@example.com</a><p><small>Demo contact address for this college project.</small></p></section>
          <section class="card"><h2>Emergency</h2><p>For a medical emergency, contact your local emergency services or visit the nearest emergency department. Do not use this demo website for emergency care.</p></section>
        </div>
        <div class="note"><strong>Note:</strong> CarePlus is a college project demonstration. Appointment details shown on this website depend on the data entered in the project database.</div>
      </main>
    </body></html>
    """)


# LOGIN AND REGISTRATION PAGES
@app.get("/login")
def login_page():
    if session.get("user_id"):
        return redirect("/patient/dashboard")
    return render_template("login.html")


@app.get("/register")
def register_page():
    if session.get("user_id"):
        return redirect("/patient/dashboard")
    return render_template("register.html")


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/login")


# PATIENT REGISTRATION API
@app.post("/api/register")
def register_patient():
    data = request.get_json(silent=True) or {}

    full_name = str(data.get("full_name", "")).strip()
    gender = str(data.get("gender", "")).strip()
    dob = str(data.get("date_of_birth", "")).strip()
    phone = str(data.get("phone", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not all([full_name, gender, dob, phone, email, password]):
        return jsonify({
            "success": False,
            "message": "Please fill in all required fields."
        }), 400

    if len(full_name) > 100:
        return jsonify({
            "success": False,
            "message": "Name must be 100 characters or fewer."
        }), 400

    if gender not in ("Male", "Female", "Other"):
        return jsonify({
            "success": False,
            "message": "Please select a valid gender."
        }), 400

    try:
        birth_date = date.fromisoformat(dob)
        if birth_date >= date.today():
            return jsonify({
                "success": False,
                "message": "Date of birth must be in the past."
            }), 400
    except ValueError:
        return jsonify({
            "success": False,
            "message": "Please enter a valid date of birth."
        }), 400

    if not phone.isdigit() or not 10 <= len(phone) <= 15:
        return jsonify({
            "success": False,
            "message": "Enter a valid phone number (10 to 15 digits)."
        }), 400

    if "@" not in email or "." not in email.rsplit("@", 1)[-1] or len(email) > 150:
        return jsonify({
            "success": False,
            "message": "Enter a valid email address."
        }), 400

    if len(password) < 8:
        return jsonify({
            "success": False,
            "message": "Password must be at least 8 characters."
        }), 400

    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            "SELECT id FROM users WHERE LOWER(email) = %s LIMIT 1",
            (email,)
        )
        if cur.fetchone():
            return jsonify({
                "success": False,
                "message": "This email is already registered. Please login."
            }), 409

        cur.execute(
            "SELECT id FROM users WHERE phone = %s LIMIT 1",
            (phone,)
        )
        if cur.fetchone():
            return jsonify({
                "success": False,
                "message": "This phone number is already registered."
            }), 409

        password_hash = generate_password_hash(password)

        cur.execute("""
            INSERT INTO users
                (full_name, gender, date_of_birth, phone, email,
                 password_hash, role, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'patient', 'active')
        """, (
            full_name, gender, birth_date, phone,
            email, password_hash
        ))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Registration successful. Please login.",
            "user_id": cur.lastrowid
        }), 201

    except Error as e:
        if conn and conn.is_connected():
            conn.rollback()

        app.logger.exception("Patient registration error: %s", e)

        return jsonify({
            "success": False,
            "message": "Registration could not be completed. Please check the details and try again."
        }), 500

    finally:
        close_db(conn, cur)


# PATIENT LOGIN API
@app.post("/api/login")
def login_patient():
    data = request.get_json(silent=True) or {}

    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Enter your email and password."
        }), 400

    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT id, full_name, email, password_hash, role, status
            FROM users
            WHERE LOWER(email) = %s
            LIMIT 1
        """, (email,))

        user = cur.fetchone()

        if (
            not user
            or user.get("role") != "patient"
            or user.get("status") != "active"
            or not check_password_hash(
                user.get("password_hash") or "", password
            )
        ):
            return jsonify({
                "success": False,
                "message": "Invalid email or password, or account is inactive."
            }), 401

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["full_name"]
        session["user_email"] = user["email"]
        session["user_role"] = user["role"]

        return jsonify({
            "success": True,
            "message": "Login successful.",
            "redirect": "/patient/dashboard"
        })

    except Error as e:
        app.logger.exception("Patient login error: %s", e)

        return jsonify({
            "success": False,
            "message": "Login service is temporarily unavailable."
        }), 500

    finally:
        close_db(conn, cur)


# PATIENT DASHBOARD
@app.get("/patient/dashboard")
def patient_dashboard():
    if not session.get("user_id"):
        return redirect("/login")

    return render_template(
        "patient_dashboard.html",
        patient_name=session.get("user_name"),
        patient_email=session.get("user_email")
    )


# SEPARATE PATIENT PAGES
@app.get("/patient/appointments")
def patient_appointments_page():
    if not session.get("user_id") or session.get("user_role") != "patient":
        return redirect("/login")
    return render_template("my_appointments.html", patient_name=session.get("user_name"))


@app.get("/patient/profile")
def patient_profile_page():
    if not session.get("user_id") or session.get("user_role") != "patient":
        return redirect("/login")
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT full_name, gender, date_of_birth, phone, email
                       FROM users WHERE id = %s AND role = 'patient' LIMIT 1""",
                    (session["user_id"],))
        patient = cur.fetchone()
        if not patient:
            session.clear()
            return redirect("/login")
        if patient.get("date_of_birth"):
            patient["date_of_birth"] = patient["date_of_birth"].isoformat()
        return render_template("my_profile.html", patient=patient)
    except Error as e:
        app.logger.exception("Patient profile page error: %s", e)
        return "Could not load profile. Please check the database.", 500
    finally:
        close_db(conn, cur)


@app.post("/api/my-profile")
def update_patient_profile():
    if not session.get("user_id") or session.get("user_role") != "patient":
        return jsonify({"success": False, "message": "Please login first."}), 401
    data = request.get_json(silent=True) or {}
    full_name = str(data.get("full_name", "")).strip()
    gender = str(data.get("gender", "")).strip()
    dob = str(data.get("date_of_birth", "")).strip()
    phone = str(data.get("phone", "")).strip()
    if not full_name or len(full_name) > 100:
        return jsonify({"success": False, "message": "Enter a valid full name."}), 400
    if gender not in ("Male", "Female", "Other"):
        return jsonify({"success": False, "message": "Select a valid gender."}), 400
    try:
        birth_date = date.fromisoformat(dob)
        if birth_date >= date.today():
            raise ValueError
    except ValueError:
        return jsonify({"success": False, "message": "Enter a valid date of birth."}), 400
    if not phone.isdigit() or not 10 <= len(phone) <= 15:
        return jsonify({"success": False, "message": "Enter a valid phone number."}), 400
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE phone = %s AND id <> %s LIMIT 1",
                    (phone, session["user_id"]))
        if cur.fetchone():
            return jsonify({"success": False, "message": "This phone number is already registered."}), 409
        cur.execute("""UPDATE users SET full_name=%s, gender=%s,
                       date_of_birth=%s, phone=%s WHERE id=%s AND role='patient'""",
                    (full_name, gender, birth_date, phone, session["user_id"]))
        conn.commit()
        session["user_name"] = full_name
        return jsonify({"success": True, "message": "Profile updated successfully."})
    except Error as e:
        if conn and conn.is_connected(): conn.rollback()
        return db_error(e)
    finally:
        close_db(conn, cur)


# LOGGED-IN PATIENT APPOINTMENTS
@app.get("/api/my-appointments")
def my_appointments():
    if not session.get("user_id"):
        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT
                a.id AS appointment_id,
                a.reason,
                a.status,
                d.full_name AS doctor_name,
                d.specialization,
                h.hospital_name,
                s.available_date,
                s.start_time,
                s.end_time
            FROM appointments a
            INNER JOIN doctors d ON a.doctor_id = d.id
            INNER JOIN doctor_slots s ON a.slot_id = s.id
            LEFT JOIN hospitals h ON s.hospital_id = h.id
            WHERE a.patient_id = %s
            ORDER BY a.created_at DESC
        """, (session["user_id"],))

        appointments = convert_dates(cur.fetchall())

        return jsonify({
            "success": True,
            "count": len(appointments),
            "appointments": appointments
        })

    except Error as e:
        return db_error(e)

    finally:
        close_db(conn, cur)


# CSS, JAVASCRIPT AND IMAGES
@app.get("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(
        os.path.join(BASE_DIR, "assets"),
        filename
    )


# HOSPITALS AND DOCTORS PAGE
@app.get("/doctors")
def doctors_page():
    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT id, hospital_name, address, area, city, state,
                   pincode, phone, email, website, hospital_image,
                   departments, description, latitude, longitude
            FROM hospitals
            WHERE is_active = 1
            ORDER BY hospital_name ASC
        """)

        hospitals = cur.fetchall()

        for hospital in hospitals:
            image = (hospital.get("hospital_image") or "").strip()
            image = image.replace("\\", "/").lstrip("/")

            if image and os.path.isfile(os.path.join(BASE_DIR, image)):
                hospital["hospital_image_url"] = "/" + image
            else:
                hospital["hospital_image_url"] = ""

            parts = [
                hospital.get("address") or "",
                hospital.get("area") or "",
                hospital.get("city") or "",
                hospital.get("state") or "",
                hospital.get("pincode") or ""
            ]

            hospital["full_address"] = ", ".join(
                str(part).strip()
                for part in parts
                if str(part).strip()
            )

        hospital_id = request.args.get("hospital_id", type=int)

        selected_hospital = None
        doctors = []
        address = ""
        map_url = ""
        map_embed = ""

        if hospital_id:
            selected_hospital = next(
                (h for h in hospitals if h["id"] == hospital_id),
                None
            )

        if selected_hospital:
            address = selected_hospital["full_address"]
            map_query = address or selected_hospital["hospital_name"]
            encoded = quote(map_query)

            map_url = (
                "https://www.google.com/maps/search/?api=1&query="
                + encoded
            )
            map_embed = (
                "https://www.google.com/maps?q="
                + encoded
                + "&output=embed"
            )

            cur.execute("""
                SELECT d.id, d.full_name, d.specialization,
                       d.qualification, d.experience_years, d.photo,
                       d.city, dh.consultation_fee
                FROM doctor_hospitals dh
                INNER JOIN doctors d ON dh.doctor_id = d.id
                WHERE dh.hospital_id = %s
                  AND dh.is_active = 1
                  AND d.is_active = 1
                ORDER BY d.full_name
            """, (hospital_id,))

            doctors = cur.fetchall()

            for doctor in doctors:
                photo = (
                    doctor.get("photo") or ""
                ).strip().replace("\\", "/")

                doctor["photo_url"] = ""

                if photo:
                    filename = os.path.basename(photo)

                    paths = [
                        photo.lstrip("/"),
                        "assets/images/doctors/" + filename
                    ]

                    for path in paths:
                        if os.path.isfile(os.path.join(BASE_DIR, path)):
                            doctor["photo_url"] = "/" + path
                            break

        return render_template(
            "doctors.html",
            hospitals=hospitals,
            selected_hospital=selected_hospital,
            doctors=doctors,
            address=address,
            map_url=map_url,
            map_embed=map_embed,
            logged_in=bool(session.get("user_id"))
        )

    except Error as e:
        app.logger.exception("Doctors page error: %s", e)
        return "Database error. Please check XAMPP MySQL.", 500

    finally:
        close_db(conn, cur)


# APPOINTMENT BOOKING PAGE
@app.get("/book-appointment")
def book_appointment_page():
    if not session.get("user_id") or session.get("user_role") != "patient":
        return redirect("/login")
    doctor_id = request.args.get("doctor_id", type=int)
    hospital_id = request.args.get("hospital_id", type=int)

    if not doctor_id or not hospital_id:
        return "Doctor ID or Hospital ID is missing.", 400

    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT
                d.id AS doctor_id,
                d.full_name,
                d.specialization,
                d.qualification,
                d.experience_years,
                d.photo,
                dh.hospital_id,
                dh.consultation_fee,
                h.hospital_name
            FROM doctor_hospitals dh
            INNER JOIN doctors d ON d.id = dh.doctor_id
            INNER JOIN hospitals h ON h.id = dh.hospital_id
            WHERE d.id = %s
              AND h.id = %s
              AND d.is_active = 1
              AND dh.is_active = 1
              AND h.is_active = 1
            LIMIT 1
        """, (doctor_id, hospital_id))

        doctor = cur.fetchone()

        if not doctor:
            return "Selected doctor is not available at this hospital.", 404

        photo = (
            doctor.get("photo") or ""
        ).strip().replace("\\", "/")

        doctor["photo_url"] = ""

        if photo:
            filename = os.path.basename(photo)

            paths = [
                photo.lstrip("/"),
                "assets/images/doctors/" + filename
            ]

            for path in paths:
                if os.path.isfile(os.path.join(BASE_DIR, path)):
                    doctor["photo_url"] = "/" + path
                    break

        return render_template(
            "book_appointment.html",
            doctor=doctor,
            logged_in=bool(session.get("user_id"))
        )

    except Error as e:
        app.logger.exception("Appointment page error: %s", e)
        return "Database error. Please check XAMPP MySQL.", 500

    finally:
        close_db(conn, cur)


# DATABASE STATUS
@app.get("/api/status")
def status():
    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT DATABASE()")
        db_name = cur.fetchone()[0]

        return jsonify({
            "success": True,
            "backend": "Python Flask",
            "database": db_name,
            "status": "connected"
        })

    except Error as e:
        return db_error(e)

    finally:
        close_db(conn, cur)


# ALL HOSPITALS API
@app.get("/api/hospitals")
def hospitals():
    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT id, hospital_name, address, area, city, state,
                   phone, hospital_image
            FROM hospitals
            WHERE is_active = 1
            ORDER BY hospital_name
        """)

        rows = convert_dates(cur.fetchall())

        return jsonify({
            "success": True,
            "count": len(rows),
            "hospitals": rows
        })

    except Error as e:
        return db_error(e)

    finally:
        close_db(conn, cur)


# DOCTORS OF SELECTED HOSPITAL API
@app.get("/api/hospitals/<int:hospital_id>/doctors")
def hospital_doctors(hospital_id):
    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT d.id, d.full_name, d.specialization,
                   d.qualification, d.experience_years,
                   d.photo, dh.consultation_fee
            FROM doctor_hospitals dh
            INNER JOIN doctors d ON d.id = dh.doctor_id
            INNER JOIN hospitals h ON h.id = dh.hospital_id
            WHERE dh.hospital_id = %s
              AND dh.is_active = 1
              AND d.is_active = 1
              AND h.is_active = 1
            ORDER BY d.full_name
        """, (hospital_id,))

        rows = convert_dates(cur.fetchall())

        return jsonify({
            "success": True,
            "hospital_id": hospital_id,
            "count": len(rows),
            "doctors": rows
        })

    except Error as e:
        return db_error(e)

    finally:
        close_db(conn, cur)


# AVAILABLE DOCTOR SLOTS API
@app.get("/api/doctors/<int:doctor_id>/slots")
def doctor_slots(doctor_id):
    hospital_id = request.args.get("hospital_id", type=int)
    selected_date = request.args.get("date", type=str)

    if not hospital_id or not selected_date:
        return jsonify({
            "success": False,
            "message": "hospital_id and date are required"
        }), 400

    try:
        requested_date = date.fromisoformat(selected_date)

        if requested_date < date.today():
            return jsonify({
                "success": False,
                "message": "Past dates cannot be selected"
            }), 400

    except ValueError:
        return jsonify({
            "success": False,
            "message": "Invalid date format"
        }), 400

    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT id, start_time, end_time, available_date
            FROM doctor_slots
            WHERE doctor_id = %s
              AND hospital_id = %s
              AND available_date = %s
              AND status = 'available'
            ORDER BY start_time
        """, (doctor_id, hospital_id, selected_date))

        rows = convert_dates(cur.fetchall())

        return jsonify({
            "success": True,
            "count": len(rows),
            "slots": rows
        })

    except Error as e:
        return db_error(e)

    finally:
        close_db(conn, cur)


# BOOK APPOINTMENT API - FIXED
@app.post("/api/appointments")
def create_appointment():

    # Patient must be logged in
    if not session.get("user_id") or session.get("user_role") != "patient":
        return jsonify({
            "success": False,
            "message": "Please login before booking an appointment."
        }), 401

    data = request.get_json(silent=True) or {}

    # Patient ID comes from the secure login session
    patient_id = session["user_id"]

    required = ["doctor_id", "slot_id", "hospital_id"]
    missing = [
        key for key in required
        if data.get(key) in (None, "")
    ]

    if missing:
        return jsonify({
            "success": False,
            "message": "Missing required fields",
            "missing": missing
        }), 400

    try:
        doctor_id = int(data["doctor_id"])
        slot_id = int(data["slot_id"])
        hospital_id = int(data["hospital_id"])
        reason = str(data.get("reason", "")).strip()

        if doctor_id <= 0 or slot_id <= 0 or hospital_id <= 0:
            raise ValueError("IDs must be positive numbers")

    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Please provide valid doctor, hospital and slot IDs."
        }), 400

    conn = None
    cur = None

    try:
        conn = get_db()
        conn.start_transaction()
        cur = conn.cursor(dictionary=True)

        # Verify logged-in patient
        cur.execute("""
            SELECT id, full_name, email
            FROM users
            WHERE id = %s
              AND role = 'patient'
              AND status = 'active'
            LIMIT 1
        """, (patient_id,))

        patient = cur.fetchone()

        if not patient:
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "Patient not found or inactive. Please login again."
            }), 404

        # Verify slot and lock it to prevent double booking
        cur.execute("""
            SELECT id, doctor_id, hospital_id, available_date,
                   start_time, end_time, status
            FROM doctor_slots
            WHERE id = %s
            FOR UPDATE
        """, (slot_id,))

        slot = cur.fetchone()

        if (
            not slot
            or slot["doctor_id"] != doctor_id
            or slot["hospital_id"] != hospital_id
            or slot["status"] != "available"
            or slot["available_date"] < date.today()
        ):
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "This appointment slot is not available. Please select another slot."
            }), 409

        # Verify doctor is linked to selected hospital
        cur.execute("""
            SELECT d.id
            FROM doctor_hospitals dh
            INNER JOIN doctors d ON d.id = dh.doctor_id
            INNER JOIN hospitals h ON h.id = dh.hospital_id
            WHERE d.id = %s
              AND h.id = %s
              AND dh.is_active = 1
              AND d.is_active = 1
              AND h.is_active = 1
            LIMIT 1
        """, (doctor_id, hospital_id))

        if not cur.fetchone():
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "Selected doctor is not available at this hospital."
            }), 404

        # Create appointment
        cur.execute("""
            INSERT INTO appointments
                (patient_id, doctor_id, slot_id, reason, status)
            VALUES (%s, %s, %s, %s, 'pending')
        """, (patient_id, doctor_id, slot_id, reason))

        appointment_id = cur.lastrowid

        # Mark slot as booked
        cur.execute("""
            UPDATE doctor_slots
            SET status = 'booked'
            WHERE id = %s
              AND status = 'available'
        """, (slot_id,))

        if cur.rowcount != 1:
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "Slot could not be booked. Please select another slot."
            }), 409

        # Get email details
        cur.execute("""
            SELECT
                u.email AS patient_email,
                u.full_name AS patient_name,
                d.full_name AS doctor_name,
                h.hospital_name,
                s.available_date,
                s.start_time
            FROM appointments a
            INNER JOIN users u ON u.id = a.patient_id
            INNER JOIN doctors d ON d.id = a.doctor_id
            INNER JOIN doctor_slots s ON s.id = a.slot_id
            INNER JOIN hospitals h ON h.id = s.hospital_id
            WHERE a.id = %s
        """, (appointment_id,))

        email_details = cur.fetchone()

        conn.commit()

        # Send email after successful database commit
        email_sent = False

        if email_details and email_details.get("patient_email"):
            try:
                email_sent = bool(send_appointment_email(
                    patient_email=email_details["patient_email"],
                    patient_name=email_details["patient_name"],
                    hospital_name=email_details["hospital_name"],
                    doctor_name=email_details["doctor_name"],
                    appointment_date=str(email_details["available_date"]),
                    appointment_time=str(email_details["start_time"]),
                    appointment_id=appointment_id,
                    status="Pending"
                ))
            except Exception:
                app.logger.exception(
                    "Appointment email could not be sent"
                )

        return jsonify({
            "success": True,
            "message": "Appointment booked successfully",
            "appointment_id": appointment_id,
            "email_sent": email_sent,
            "email_message": (
                "Confirmation email sent successfully"
                if email_sent
                else "Appointment saved, but email could not be sent"
            )
        }), 201

    except Error as e:
        if conn and conn.is_connected():
            conn.rollback()
        return db_error(e)

    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()

        app.logger.exception(
            "Appointment processing error: %s", e
        )

        return jsonify({
            "success": False,
            "message": "Appointment processing failed. Check server logs."
        }), 500

    finally:
        close_db(conn, cur)


# PATIENT APPOINTMENT HISTORY API - SECURED
@app.get("/api/patients/<int:patient_id>/appointments")
def patient_appointments(patient_id):

    if not session.get("user_id"):
        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    if int(session["user_id"]) != patient_id:
        return jsonify({
            "success": False,
            "message": "You are not allowed to view this patient's appointments."
        }), 403

    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT
                a.id AS appointment_id,
                a.patient_id,
                a.doctor_id,
                a.slot_id,
                a.reason,
                a.status,
                d.full_name AS doctor_name,
                d.specialization,
                h.hospital_name,
                s.available_date,
                s.start_time,
                s.end_time
            FROM appointments a
            INNER JOIN doctors d ON a.doctor_id = d.id
            INNER JOIN doctor_slots s ON a.slot_id = s.id
            LEFT JOIN hospitals h ON s.hospital_id = h.id
            WHERE a.patient_id = %s
            ORDER BY a.created_at DESC
        """, (patient_id,))

        rows = convert_dates(cur.fetchall())

        return jsonify({
            "success": True,
            "count": len(rows),
            "appointments": rows
        })

    except Error as e:
        return db_error(e)

    finally:
        close_db(conn, cur)


# SAVE ANONYMOUS USABILITY TEST DATA
@app.post("/api/usability-tests")
def save_usability_test():
    data = request.get_json(silent=True) or {}

    required = [
        "participant_code",
        "method",
        "task_time_seconds",
        "task_completed"
    ]

    missing = [
        key for key in required
        if key not in data
    ]

    if missing:
        return jsonify({
            "success": False,
            "message": "Missing required fields",
            "missing": missing
        }), 400

    try:
        participant_code = str(
            data["participant_code"]
        ).strip()

        method = str(data["method"]).strip()
        task_time = float(data["task_time_seconds"])
        clicks = int(data.get("clicks", 0))
        errors = int(data.get("errors", 0))
        completed = int(data["task_completed"])

        satisfaction = data.get("satisfaction_score")
        sus = data.get("sus_score")

        if not participant_code or len(participant_code) > 20:
            raise ValueError("Invalid participant code")

        if method not in ("current", "prototype"):
            raise ValueError("Method must be current or prototype")

        if task_time < 0 or clicks < 0 or errors < 0:
            raise ValueError("Values cannot be negative")

        if completed not in (0, 1):
            raise ValueError("task_completed must be 0 or 1")

        if satisfaction is not None:
            satisfaction = int(satisfaction)
            if not 1 <= satisfaction <= 5:
                raise ValueError("Satisfaction must be 1 to 5")

        if sus is not None:
            sus = float(sus)
            if not 0 <= sus <= 100:
                raise ValueError("SUS score must be 0 to 100")

    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Invalid testing data"
        }), 400

    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO careplus_usability_tests
            (participant_code, method, task_time_seconds,
             clicks, errors, task_completed,
             satisfaction_score, sus_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            participant_code, method, task_time,
            clicks, errors, completed,
            satisfaction, sus
        ))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Usability test data saved",
            "test_id": cur.lastrowid
        }), 201

    except Error as e:
        if conn and conn.is_connected():
            conn.rollback()
        return db_error(e)

    finally:
        close_db(conn, cur)


# CANCEL APPOINTMENT API
@app.post("/api/appointments/<int:appointment_id>/cancel")
def cancel_appointment(appointment_id):

    # Only logged-in patients can cancel appointments
    if (
        not session.get("user_id")
        or session.get("user_role") != "patient"
    ):
        return jsonify({
            "success": False,
            "message": "Please login as a patient first."
        }), 401

    patient_id = session["user_id"]
    conn = None
    cur = None

    try:
        conn = get_db()
        conn.start_transaction()
        cur = conn.cursor(dictionary=True)

        # Lock and verify this appointment belongs to this patient
        cur.execute("""
            SELECT id, patient_id, slot_id, status
            FROM appointments
            WHERE id = %s
              AND patient_id = %s
            FOR UPDATE
        """, (appointment_id, patient_id))

        appointment = cur.fetchone()

        if not appointment:
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "Appointment not found."
            }), 404

        current_status = (appointment["status"] or "").lower()

        if current_status not in ("pending", "confirmed"):
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "This appointment cannot be cancelled."
            }), 409

        # Lock the appointment slot
        cur.execute("""
            SELECT id, status
            FROM doctor_slots
            WHERE id = %s
            FOR UPDATE
        """, (appointment["slot_id"],))

        slot = cur.fetchone()

        if not slot:
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "Appointment slot was not found."
            }), 404

        # Mark appointment as cancelled
        cur.execute("""
            UPDATE appointments
            SET status = 'cancelled'
            WHERE id = %s
              AND patient_id = %s
              AND status IN ('pending', 'confirmed')
        """, (appointment_id, patient_id))

        if cur.rowcount != 1:
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "Appointment could not be cancelled. Please refresh and try again."
            }), 409

        # Make the slot available again
        cur.execute("""
            UPDATE doctor_slots
            SET status = 'available'
            WHERE id = %s
              AND status = 'booked'
        """, (appointment["slot_id"],))

        if cur.rowcount != 1:
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "Slot status could not be updated. Please contact support."
            }), 409

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Appointment cancelled successfully. The time slot is available again."
        }), 200

    except Error as e:
        if conn and conn.is_connected():
            conn.rollback()
        return db_error(e)

    finally:
        close_db(conn, cur)

# RUN FLASK SERVER
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )