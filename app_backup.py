
import os
from flask import Flask, jsonify, request
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# MySQL Database Configuration
DB_CONFIG = {
    "host": os.getenv("CAREPLUS_DB_HOST", "127.0.0.1"),
    "user": os.getenv("CAREPLUS_DB_USER", "root"),
    "password": os.getenv("CAREPLUS_DB_PASSWORD", ""),
    "database": os.getenv("CAREPLUS_DB_NAME", "careplus_db"),
}


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def db_error(error):
    app.logger.exception("CarePlus database error: %s", error)
    return jsonify({
        "success": False,
        "message": "Database connection/query failed. Check XAMPP MySQL and config."
    }), 500


def close_db(conn, cur):
    if cur:
        cur.close()
    if conn and conn.is_connected():
        conn.close()


def convert_dates(rows):
    for row in rows:
        for key, value in row.items():
            if hasattr(value, "isoformat"):
                row[key] = value.isoformat()
            elif hasattr(value, "total_seconds"):
                row[key] = str(value)
    return rows


# HOME
@app.get("/")
def home():
    return jsonify({
        "project": "CarePlus",
        "backend": "Python Flask",
        "status": "running"
    })


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


# ALL HOSPITALS
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

        rows = cur.fetchall()

        return jsonify({
            "success": True,
            "count": len(rows),
            "hospitals": rows
        })
    except Error as e:
        return db_error(e)
    finally:
        close_db(conn, cur)


# DOCTORS OF SELECTED HOSPITAL
@app.get("/api/hospitals/<int:hospital_id>/doctors")
def hospital_doctors(hospital_id):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT
                d.id,
                d.full_name,
                d.specialization,
                d.qualification,
                d.experience_years,
                d.photo,
                dh.consultation_fee
            FROM doctor_hospitals dh
            INNER JOIN doctors d ON d.id = dh.doctor_id
            INNER JOIN hospitals h ON h.id = dh.hospital_id
            WHERE dh.hospital_id = %s
              AND dh.is_active = 1
              AND d.is_active = 1
              AND h.is_active = 1
            ORDER BY d.full_name
        """, (hospital_id,))

        rows = cur.fetchall()

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


# AVAILABLE DOCTOR SLOTS
@app.get("/api/doctors/<int:doctor_id>/slots")
def doctor_slots(doctor_id):
    hospital_id = request.args.get("hospital_id", type=int)
    date = request.args.get("date", type=str)

    if not hospital_id or not date:
        return jsonify({
            "success": False,
            "message": "hospital_id and date are required"
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
        """, (doctor_id, hospital_id, date))

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


# BOOK APPOINTMENT
@app.post("/api/appointments")
def create_appointment():
    data = request.get_json(silent=True) or {}

    required = ["patient_id", "doctor_id", "slot_id", "hospital_id"]
    missing = [key for key in required if not data.get(key)]

    if missing:
        return jsonify({
            "success": False,
            "message": "Missing required fields",
            "missing": missing
        }), 400

    try:
        patient_id = int(data["patient_id"])
        doctor_id = int(data["doctor_id"])
        slot_id = int(data["slot_id"])
        hospital_id = int(data["hospital_id"])
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "IDs must be valid numbers"
        }), 400

    conn = None
    cur = None

    try:
        conn = get_db()
        conn.start_transaction()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT id
            FROM users
            WHERE id = %s AND role = 'patient' AND status = 'active'
        """, (patient_id,))

        if not cur.fetchone():
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "Patient not found or inactive"
            }), 404

        cur.execute("""
            SELECT id, doctor_id, hospital_id, status
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
        ):
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "This appointment slot is not available"
            }), 409

        cur.execute("""
            INSERT INTO appointments
                (patient_id, doctor_id, slot_id, reason, status)
            VALUES (%s, %s, %s, %s, 'pending')
        """, (
            patient_id,
            doctor_id,
            slot_id,
            data.get("reason", "")
        ))

        appointment_id = cur.lastrowid

        cur.execute("""
            UPDATE doctor_slots
            SET status = 'booked'
            WHERE id = %s AND status = 'available'
        """, (slot_id,))

        if cur.rowcount != 1:
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "Slot could not be booked"
            }), 409

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Appointment booked successfully",
            "appointment_id": appointment_id
        }), 201

    except Error as e:
        if conn and conn.is_connected():
            conn.rollback()
        return db_error(e)
    finally:
        close_db(conn, cur)


# PATIENT APPOINTMENT HISTORY
@app.get("/api/patients/<int:patient_id>/appointments")
def patient_appointments(patient_id):
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
            INNER JOIN doctors d
                ON a.doctor_id = d.id
            INNER JOIN doctor_slots s
                ON a.slot_id = s.id
            LEFT JOIN hospitals h
                ON s.hospital_id = h.id
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

    missing = [key for key in required if key not in data]

    if missing:
        return jsonify({
            "success": False,
            "message": "Missing required fields",
            "missing": missing
        }), 400

    try:
        participant_code = str(data["participant_code"]).strip()
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
            raise ValueError("Time, clicks and errors cannot be negative")

        if completed not in (0, 1):
            raise ValueError("task_completed must be 0 or 1")

        if satisfaction is not None:
            satisfaction = int(satisfaction)
            if not 1 <= satisfaction <= 5:
                raise ValueError("Satisfaction score must be 1 to 5")

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
        test_id = cur.lastrowid

        return jsonify({
            "success": True,
            "message": "Usability test data saved",
            "test_id": test_id
        }), 201

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
