from django.conf import settings
from square.client import Client

# Square API Configuration
def get_square_client():
    client = Client(
        access_token=settings.SQUARE_ACCESS_TOKEN,
        environment=settings.SQUARE_ENV  # 'sandbox' for testing or 'production' for live transactions
    )
    return client

def create_order(orderType, order, cost_in_cents, idempotency_key, extension=None):

    # Access the client service (orders)
    orders_api = get_square_client().orders

    # Depending on type of order, adjust the line item descriptions to be used in "name" below
    if orderType =='extension':
        # order_details = f"Extension for Order #{order.id}, {order.equipment.equipment_type.name} Forklift, extended to {extension.new_end_date}."
        order_details = f"Extension: {order.equipment.equipment_type.name} Forklift"
        note = f"Order #{order.id}, {order.equipment.equipment_type.name} Forklift Rental, extended by {extension.days_extended} days to end on {extension.new_end_date}."
    else:
        order_details = f"{order.equipment.equipment_type.name} Forklift Rental"
        note = f"{order.equipment.equipment_type.name} Forklift Rental: {order.rental_term_agreement}-day Rental from {order.rental_start_date} to {order.rental_end_date}."

    orderResult = orders_api.create_order(
        body = {
            "order": {
            "location_id": settings.SQUARE_LOCATION_ID,
            "line_items": [
                {
                "name": order_details,
                "quantity": "1",
                "base_price_money": {
                    "amount": cost_in_cents,
                    "currency": "USD"
                }
                }
            ]
            },
            "idempotency_key": idempotency_key
        }
    )

    if orderResult.is_error():
        print("Order Creation resulted in an error")
        return {"success": False, "result_errors_info": orderResult.errors}
    elif orderResult.is_success():
        print("Order Creation SUCCESSFUL!!!")

        order_id = orderResult.body['order']['id']
        
        return {"success": True, "order_id": order_id, "note": note} #Return a dictionary containing the order_id and the note to be used in create_payment.

def create_payment(token, cost_in_cents, order_data, idempotency_key):

    client = get_square_client()

    result = client.payments.create_payment(
        body = {
            "source_id": token,
            "idempotency_key": idempotency_key,
            "amount_money": {
            "amount": cost_in_cents,
            "currency": "USD"
            },

            "app_fee_money": { #The amount of money that the developer is taking as a fee for facilitating the payment on behalf of the seller.
            "amount": 0,
            "currency": "USD"
            },
            "autocomplete": True,
            "order_id": order_data["order_id"],
            "note": order_data["note"]
        }
    )

    if result.is_success():
        payment_response = result.body
        receipt_url = payment_response.get("payment", {}).get("receipt_url")
        print("Payment Successful!")
        return {"success": True, "receipt_url": receipt_url, "order_id": order_data["order_id"], "note": order_data["note"]} #Return a dictionary containing success indicator and receipt URL
    elif result.is_error():
        print("PAYMENT ERROR:")
        return {"success": False, "result_errors_info": result.errors} #Return a dictionary containing success indicator and payment error details