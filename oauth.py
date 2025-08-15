import time
import uuid
import requests
import stripe
import logging
from flask import Flask, jsonify, redirect, request, url_for

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

stripeAPIKey = 'sk_test_51R48bmR0HkrpNQRbvqL3xnBi67yvT1lLuai7c58DWTnnyBi0KteOaSJQ86fN7n2lA579HvL9eF3d2oOby78iSc6t00FmvB1qTX'

stripe.api_key = stripeAPIKey

temp_account_store = {}

app = Flask(__name__)

@app.route('/connect-stripe')
def connect_stripe():
    try:
        session_id = str(uuid.uuid4())
        temp_account_store[session_id] = {'status': 'pending'}
        redirect_uri = "https://oneder-shift-backend.onrender.com/stripe/callback"
        logger.info("Redirecting user to Stripe OAuth URL for account connection.")
        oauth_url = (
                    f"https://connect.stripe.com/oauth/authorize?"
                    f"response_type=code&"
                    f"client_id=ca_SpZoR8SvTHpmjox6os1OWQiERSqLScBb&"
                    f"scope=read_write&"
                    f"redirect_uri={redirect_uri}"
                )        
        logger.info(f"OAuth URL: {oauth_url}")
        return jsonify({'url': oauth_url, 'session_id': session_id}), 200

    except Exception as e:
        logger.error(f"Error occurred while generating Stripe OAuth URL: {str(e)}")
        return jsonify({'error': 'Failed to initiate Stripe connection'}), 500

@app.route('/stripe/callback')
def stripe_callback():
    code = request.args.get('code')
    session_id = request.args.get('session_id')
    
    # Log the received code for debugging
    logger.info("Received callback with code: %s", code)
    
    if not code:
        logger.error("No 'code' parameter found in the request.")
        return jsonify({'error': 'Missing code parameter'}), 400

    try:
        logger.info("Processing the Stripe OAuth callback with code: %s", code)
        token_url = "https://connect.stripe.com/oauth/token"

        data = {
            "client_secret": stripeAPIKey,  # Replace with your Stripe secret key
            "code": code,
            "grant_type": "authorization_code",
        }

        logger.info("Sending request to Stripe token URL with data: %s", data)

        response = requests.post(token_url, data=data)
        logger.info("Received response from Stripe: %s", response.text)

        if response.status_code == 200:
            access_token = response.json().get("access_token")
            logger.info("Access Token received: %s", access_token)
            
            # Corrected line to extract stripe_user_id
            connected_account_id = response.json().get('stripe_user_id')
            if connected_account_id:
                temp_account_store[session_id] = {
                    'connected_account_id': connected_account_id,
                    'timestamp': time.time()
                }
                logger.info("Successfully connected Stripe account: %s", connected_account_id)
                return "Stripe connection successful! You can now return to your app."

            else:
                logger.error("No 'stripe_user_id' found in the response")
                return "Stripe connection failed, please try again.", 400

        else:
            logger.error("Error response from Stripe: %s", response.json())
            return jsonify({'error': response.json()}), 400

    except stripe.error.StripeError as e:
        logger.error(f"Stripe API error: {str(e)}")
        return jsonify({'error': 'Stripe API error occurred'}), 400
    except Exception as e:
        logger.error(f"General error during Stripe callback processing: {str(e)}")
        return jsonify({'error': str(e)}), 400
@app.route('/stripe/create-payment-intent/<string:connected_account_id>', methods=['POST'])
def create_payment_intent(connected_account_id):
    try:
        logger.info("Creating PaymentIntent for connected account: %s", connected_account_id)
        payment_intent = stripe.PaymentIntent.create(
            amount=1000,
            currency='usd',
            transfer_group='pharmacy-payment',
            # destination=connected_account_id
        )
        logger.info("PaymentIntent created successfully: %s", payment_intent.id)
        # Return the PaymentIntent details as a JSON response
        return jsonify(payment_intent), 200
    except stripe.error.StripeError as e:
        logger.error(f"Stripe API error during PaymentIntent creation: {str(e)}")
        return jsonify({'error': 'Stripe API error occurred'}), 400
    except Exception as e:
        logger.error(f"General error during PaymentIntent creation: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/get-connected-id')
def get_connected_id():
    session_id = request.args.get('session_id')
    
    if not session_id or session_id not in temp_account_store:
        logger.warning(f"Attempt to get connected ID for invalid session: {session_id}")
        return jsonify({'error': 'Invalid or expired session.'}), 404
    
    account_data = temp_account_store[session_id]
    
    if 'connected_account_id' in account_data:
        connected_id = account_data['connected_account_id']
        logger.info(f"Successfully retrieved connected ID for session {session_id}")
        
        del temp_account_store[session_id]
        
        return jsonify({'connected_account_id': connected_id}), 200
    else:
        logger.warning(f"Connected ID not yet available for session {session_id}")
        return jsonify({'error': 'Connected ID not yet available.'}), 404

def capture_payment_and_transfer(payment_intent_id, connected_account_id):
    try:
        logger.info("Retrieving PaymentIntent: %s", payment_intent_id)
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        payment_intent.capture()
        
        total_amount = payment_intent.amount_received
        commission = total_amount * 0.1
        amount_to_pharmacist = total_amount - commission
        
        logger.info("Captured PaymentIntent: %s, Commission: %s, Amount to Pharmacist: %s",
                    payment_intent.id, commission, amount_to_pharmacist)
        
        transfer = stripe.Transfer.create(
            amount=amount_to_pharmacist,
            currency='usd',
            # destination=connected_account_id,
            transfer_group=payment_intent.transfer_group
        )
        logger.info("Transfer created successfully: %s", transfer.id)
        return transfer
    except stripe.error.StripeError as e:
        logger.error(f"Stripe API error during capture or transfer: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"General error during captur or transfer: {str(e)}")
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
