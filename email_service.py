
import os
import smtplib
from pathlib import Path
from email.message import EmailMessage
from dotenv import load_dotenv

# Read Gmail settings from the main project folder's .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def send_appointment_email(
    patient_email,
    patient_name,
    hospital_name,
    doctor_name,
    appointment_date,
    appointment_time,
    appointment_id,
    status="Pending"
):
    sender_email = os.getenv("MAIL_USERNAME")
    sender_password = os.getenv("MAIL_PASSWORD")

    if not sender_email or not sender_password:
        print("Email settings missing. Check the .env file.")
        return False

    message = EmailMessage()
    message["Subject"] = "CarePlus - Appointment Booking Confirmation"
    message["From"] = f"CarePlus Hospital App <{sender_email}>"
    message["To"] = patient_email

    message.set_content(f"""
Hello {patient_name},

Your appointment booking request has been received by CarePlus.

Appointment Details
-------------------
Booking ID: {appointment_id}
Patient Name: {patient_name}
Hospital: {hospital_name}
Doctor: {doctor_name}
Date: {appointment_date}
Time: {appointment_time}
Status: {status}

Thank you for choosing CarePlus.

This is an automated demo confirmation email.
Please contact the hospital to verify your appointment.

Regards,
CarePlus Team
""")

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)

        print(f"Appointment email sent to {patient_email}")
        return True

    except Exception as error:
        print("Email sending failed:", error)
        return False
