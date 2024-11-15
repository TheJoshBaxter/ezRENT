from twilio.rest import Client
from django.conf import settings
from managementPortal.models import ManagementAlertNumber
import re

def initialize_twilio_client():
    account_sid = settings.ACCOUNT_SID
    auth_token = settings.AUTH_TOKEN
    client = Client(account_sid, auth_token)
    return client

def clean_phone_number(number):
    cleaned_number = re.sub(r'\D', '', number)
    return cleaned_number


def grabEmployeeNumbers():
    employeeNumbersList = ManagementAlertNumber.objects.all().values_list('phone_number', flat=True)
    return employeeNumbersList

def send_text_alert(): # FOR EMPLOYEES
    # Initialize Twilio client
    client = initialize_twilio_client()

    # Grab list of phone numbers to send the SMS to
    alertList = grabEmployeeNumbers()

    if alertList:
        for number in alertList:
            phone_number = clean_phone_number(number)
            message = client.messages.create(
                messaging_service_sid='MGeecebc9ca2a1e65f53a6219196729ce9',
                body='Ahoy 👋, you have a new rental order that needs to be reviewed.',
                to=f"+1{phone_number}"
            )
            print("Message sent to " + phone_number)
            print(message.sid)
    else:
        print("Alert text not sent; no numbers found in alert list. Please add numbers to Management Alert Numbers in settings")

def send_customer_text(number, messageBody):
    # Initialize Twilio client
    client = initialize_twilio_client()

    phone_number = clean_phone_number(number)

    try:
        message = client.messages.create(
            messaging_service_sid='MGeecebc9ca2a1e65f53a6219196729ce9',
            body=messageBody,
            to=f"+1{phone_number}"
        )
        print("Message sent to the customer @ " + phone_number)
        print(message.sid)
    except:
        print("Text not sent, there was an issue. Check the number and message being passed")