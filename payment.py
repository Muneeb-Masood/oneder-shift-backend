import stripe
from flask import Flask, request, jsonify
import os

# Initialize Flask app
app = Flask(__name__)

# Set your Stripe secret key
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Endpoint to create a PaymentIntent
@app.route('/create-payment-method', methods=['POST'])
def create_payment_method():
    try:
        # Get data from the frontend (raw card details)
        data = request.json
        card_number = data['card_number']
        exp_month = data['exp_month']
        exp_year = data['exp_year']
        cvc = data['cvc']
        connected_account_id = data['connected_account_id']  # Connected account ID (pharmacist)

        # Create the PaymentMethod using raw card details
        payment_method = stripe.payment_methods.create(
            type='card',
            card={
                'number': card_number,
                'exp_month': exp_month,
                'exp_year': exp_year,
                'cvc': cvc,
            }
        )

        # Now create the PaymentIntent with the created PaymentMethod
        amount = data['amount']  # Amount in cents (e.g., $100 = 10000)

        payment_intent = stripe.payment_intents.create(
            amount=amount,
            currency='usd',
            payment_method=payment_method.id,
            confirm=True,  # Automatically confirm the payment
            stripe_account=connected_account_id  # Specify the connected account (pharmacist)
        )

        return jsonify({
            'client_secret': payment_intent.client_secret
        })

    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Endpoint to transfer funds to the pharmacist (after deducting the platform fee)
@app.route('/transfer-funds', methods=['POST'])
def transfer_funds():
    try:
        # Get data from the request body
        data = request.json
        amount = data['amount']  # Amount in cents (e.g., $100 = 10000)
        connected_account_id = data['connected_account_id']  # Connected account ID (pharmacist)
        
        # Deduct the platform fee (10% in this case)
        platform_fee = int(amount * 0.1)  # 10% fee
        amount_to_transfer = amount - platform_fee  # Remaining amount for pharmacist
        
        # Transfer funds to the pharmacist's connected account
        transfer = stripe.transfers.create(
            amount=amount_to_transfer,  # Amount to transfer (in cents)
            currency='usd',
            destination=connected_account_id,  # Pharmacist's connected account
        )
        
        return jsonify({
            'transfer_id': transfer.id,
            'amount_transferred': amount_to_transfer
        })

    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint to check the balance of the pharmacist's connected account
@app.route('/check-balance/<connected_account_id>', methods=['GET'])
def check_balance(connected_account_id):
    try:
        # Retrieve the balance of the pharmacist's connected account
        balance = stripe.balance.retrieve(stripe_account=connected_account_id)

        return jsonify({
            'balance': balance
        })

    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
