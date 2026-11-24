
from email_service import send_appointment_email

recipient = input("Enter your email address to receive the test email: ").strip()

if not recipient:
    print("Email address is required.")
else:
    result = send_appointment_email(
        patient_email=recipient,
        patient_name="CarePlus Test",
        hospital_name="CarePlus Demo Hospital",
        doctor_name="Dr. Demo",
        appointment_date="2026-11-23",
        appointment_time="10:00 AM",
        appointment_id="TEST-001",
        status="Demo"
    )

    print("Email test successful!" if result else "Email test failed. Check terminal error.")
