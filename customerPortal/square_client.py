from django.conf import settings
from square.client import Client
import uuid

# Square API Configuration
def get_square_client():
    client = Client(
        access_token=settings.SQUARE_ACCESS_TOKEN,
        environment=settings.SQUARE_ENV  # 'sandbox' for testing or 'production' for live transactions
    )
    return client

def create_payment(token, cost_in_cents):

    client = get_square_client()

    result = client.payments.create_payment(
        body = {
            "source_id": token,
            "idempotency_key": str(uuid.uuid4()),
            "amount_money": {
            "amount": cost_in_cents,
            "currency": "USD"
            },
            "app_fee_money": { #The amount of money that the developer is taking as a fee for facilitating the payment on behalf of the seller.
            "amount": 0,
            "currency": "USD"
            },
            "autocomplete": True,
            "note": "Brief description goes here -JB"
        }
    )

    if result.is_success():
        payment_response = result.body
        receipt_url = payment_response.get("payment", {}).get("receipt_url")
        print("Payment Successful!")
        return {"success": True, "receipt_url": receipt_url} #Return a dictionary containing success indicator and receipt URL
    elif result.is_error():
        print("PAYMENT ERROR:")
        print(result.errors)
        return {"success": False, "result_errors_info": result.errors} #Return a dictionary containing success indicator and payment error details