from django.conf import settings
from square.client import Client

# Square API Configuration
def get_square_client():
    client = Client(
        access_token=settings.SQUARE_ACCESS_TOKEN,
        environment="sandbox"  # 'sandbox' for testing or 'production' for live transactions
    )
    return client
