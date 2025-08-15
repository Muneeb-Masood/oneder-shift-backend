import requests
import stripe
import logging
from flask import Flask, jsonify, redirect, request, url_for

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

stripeAPIKey = 'sk_test_51R48bmR0HkrpNQRbvqL3xnBi67yvT1lLuai7c58DWTnnyBi0KteOaSJQ86fN7n2lA579HvL9eF3d2oOby78iSc6t00FmvB1qTX'

stripe.api_key = stripeAPIKey

app = Flask(__name__)

@app.route('/connect-stripe')
def connect_stripe():
    try:
        logger.info("Redirecting user to Stripe OAuth URL for account connection.")
        oauth_url = f"https://connect.stripe.com/oauth/authorize?response_type=code&client_id=ca_SpZoR8SvTHpmjox6os1OWQiERSqLScBb&scope=read_write"
        
        logger.info(f"OAuth URL: {oauth_url}")
        return jsonify({'url': oauth_url}), 200
    except Exception as e:
        logger.error(f"Error occurred while generating Stripe OAuth URL: {str(e)}")
        return jsonify({'error': 'Failed to initiate Stripe connection'}), 500

@app.route('/stripe/callback')
def stripe_callback():
    code = request.args.get('code')
    
    try:
        logger.info("Processing the Stripe OAuth callback with code: %s", code)
        token_url = "https://connect.stripe.com/oauth/token"

        data = {
            "client_secret": stripeAPIKey,  # Replace with your Stripe secret key
            "code": code,
            "grant_type": "authorization_code",
        }

        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            access_token = response.json().get("access_token")
            print("Access Token:", access_token)
            
            # Corrected line to extract stripe_user_id
            connected_account_id = response.json().get('stripe_user_id')
            
            deep_link_url = f"onderShift://callback?connected_account_id={connected_account_id}"

            logger.info("Successfully connected Stripe account: %s", connected_account_id)
            
            print(deep_link_url)
            # Redirect to the deep link (Flutter app will handle this)
            return redirect(deep_link_url)

        else:
            print("Error:", response.json())
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
