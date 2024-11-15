import pyotp
from flask import Flask, request, render_template, redirect, url_for
import hashlib
import smtplib
from email.mime.text import MIMEText
from user_agents import parse
import time
import requests

app = Flask(__name__)

# In-memory storage for sessions and OTP
sessions = {}
otp_storage = {}
TIMEOUT = 5 * 60  # 5 minutes timeout for OTP
HIGH_RISK_TIMEOUT = 2 * 60  # 2 minutes for high-risk devices

# Function to fetch location from IP address
def get_location_from_ip(ip_address):
    try:
        # Call IP Geolocation API
        response = requests.get(f"https://ipapi.co/{ip_address}/json/")
        data = response.json()
        # Retrieve location details
        location = f"{data.get('city')}, {data.get('region')}, {data.get('country_name')}"
        return location
    except Exception as e:
        print(f"Error fetching location: {e}")
        return "Location Unavailable"

# Function to generate and send OTP via Gmail
def send_otp(email, otp):
    sender_email = "gstmass2@gmail.com"  # Your Gmail address
    sender_password = "zpiv curo yqfv yeys"  # Your App Password
    receiver_email = email
    msg = MIMEText(f"Your OTP is: {otp}")
    msg["Subject"] = "Your OTP Code"
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
            print("OTP sent successfully!")
    except Exception as e:
        print(f"Error: {e}")

# Function to generate device fingerprint
def generate_fingerprint(request):
    ua = parse(request.headers.get('User-Agent'))
    fingerprint = hashlib.sha256(f"{request.remote_addr}{ua.device}{ua.os}".encode()).hexdigest()
    return fingerprint

# Function to fetch the real client IP address, considering proxy headers
def get_client_ip(request):
    """Fetches the real client IP address."""
    # If the request is behind a proxy (like Render), use the X-Forwarded-For header
    ip_address = request.headers.get('X-Forwarded-For')
    if ip_address:
        # X-Forwarded-For can contain a comma-separated list of IPs, we need the first one
        ip_address = ip_address.split(',')[0]
    else:
        # Fallback to request.remote_addr for direct requests
        ip_address = request.remote_addr
    return ip_address

# Function to send login attempt notification
def send_login_attempt_notification(username, email, request):
    ip_address = get_client_ip(request)  # Fetch real IP address
    location = get_location_from_ip(ip_address)  # Fetch location from real IP
    device_id = generate_fingerprint(request)
    
    message_content = f"""
    New Login Attempt:
    
    Username: {username}
    Email: {email}
    Device ID: {device_id}
    Origin (IP): {ip_address}
    Location: {location}
    """

    # Set up email content
    sender_email = "gstmass2@gmail.com"
    sender_password = "zpiv curo yqfv yeys"
    receiver_email = "harinath8124@gmail.com"
    msg = MIMEText(message_content)
    msg["Subject"] = "New Login Attempt Notification"
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
            print("Login attempt notification sent successfully!")
    except Exception as e:
        print(f"Error sending notification: {e}")

# Home route (login simulation)
@app.route('/')
def home():
    return render_template('login.html')

# Route to handle login attempts
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    email = request.form['email']
    fingerprint = generate_fingerprint(request)

    # Trigger OTP for unrecognized devices and send login notification
    if fingerprint not in sessions:
        otp = pyotp.random_base32()
        otp_storage[username] = {"otp": otp, "timestamp": time.time()}
        send_otp(email, otp)
        send_login_attempt_notification(username, email, request)
        return render_template('otp.html', email=email, username=username)

    send_login_attempt_notification(username, email, request)
    return "Login successful!"

# Route to handle OTP verification
@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    username = request.form['username']
    otp = request.form['otp']
    if username not in otp_storage:
        return "Invalid OTP session!"

    stored_otp_data = otp_storage[username]
    if time.time() - stored_otp_data['timestamp'] > TIMEOUT:
        return "OTP expired!"

    if otp == stored_otp_data['otp']:
        sessions[generate_fingerprint(request)] = username
        return "Login successful!"
    else:
        return "Invalid OTP!"

if __name__ == "__main__":
    app.run(debug=True)
