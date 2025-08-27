from flask import Flask, request, jsonify
from twilio.rest import Client
import random

app = Flask(__name__)

# Twilio credentials
ACCOUNT_SID = "YOUR_TWILIO_ACCOUNT_SID"
AUTH_TOKEN = "YOUR_TWILIO_AUTH_TOKEN"
TWILIO_PHONE = "+1XXXXXXXXXX"  # your Twilio number

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Store OTPs in memory (dict: phone -> otp)
otp_storage = {}

def generate_otp():
    return str(random.randint(100000, 999999))

@app.route("/send_otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    phone = data.get("phone")

    otp = generate_otp()
    otp_storage[phone] = otp  # save in memory

    # Send SMS via Twilio
    message = client.messages.create(
        body=f"Your verification code is: {otp}",
        from_=TWILIO_PHONE,
        to=phone
    )

    return jsonify({"success": True, "sid": message.sid})

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    phone = data.get("phone")
    entered_otp = data.get("otp")

    if otp_storage.get(phone) == entered_otp:
        return jsonify({"verified": True})
    else:
        return jsonify({"verified": False})

if __name__ == "__main__":
    app.run(debug=True)
