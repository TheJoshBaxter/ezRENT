from django.conf import settings
from square.client import Client
import uuid

# Square API Configuration
def get_square_client():
    client = Client(
        access_token=settings.SQUARE_ACCESS_TOKEN,
        environment="sandbox"  # 'sandbox' for testing or 'production' for live transactions
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
            "note": "Brief description"
        }
    )

    if result.is_success():
        print(result.body)
    elif result.is_error():
        print("ERROR:")
        print(result.errors)