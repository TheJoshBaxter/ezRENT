from django.core.management.base import BaseCommand
from django.utils.timezone import now, timedelta
from managementPortal.models import RentalOrder, ManagementAlertNumber
from customerPortal.twilioClient import send_customer_text
from customerPortal.emailClient import send_customer_email
from django.conf import settings

class Command(BaseCommand):
    help = 'Check for rentals starting or ending tomorrow'

    def handle(self, *args, **kwargs):
        print("Rental alert cron job started")
        today = now().date()
        tomorrow = today + timedelta(days=1)
        rentals_starting_tomorrow = RentalOrder.objects.filter(rental_start_date=tomorrow)
        rentals_ending_tomorrow = RentalOrder.objects.filter(rental_end_date=tomorrow)
        overdue_rentals = RentalOrder.objects.filter(rental_end_date__lt=today, rental_returned=False)

        # These print messages to the terminal or Render’s cron log output:
        self.stdout.write(f"{rentals_starting_tomorrow.count()} rentals start tomorrow.")
        self.stdout.write(f"{rentals_ending_tomorrow.count()} rentals end tomorrow.")
        self.stdout.write(f"You have {overdue_rentals.count()} rentals overdue for return. (No alerts sent for this alone.)")

        # Send management alert texts if there are rentals due to go out or come in tomorrow
        if rentals_starting_tomorrow.exists() or rentals_ending_tomorrow.exists(): # if there are EITHER rentals ending or starting tomorrow, check which, and send alerts

            messageBody = "G'day, mate! Check ezRENT, you've got " # initializing the variable outside the if so that it persists outside
            subject = "Heads Up! "

            if rentals_starting_tomorrow.exists() and rentals_ending_tomorrow.exists():
                messageBody += f"{rentals_starting_tomorrow.count()} rentals going out and {rentals_ending_tomorrow.count()} coming in TOMORROW ({tomorrow})! Head to the magic portal: {settings.BASE_SITE_URL}/managementPortal/pickups_dropoffs/?date={tomorrow}"
                subject += "Outgoing & Incoming Rentals Tomorrow"
            elif rentals_starting_tomorrow.exists():
                messageBody += f"{rentals_starting_tomorrow.count()} rentals going out TOMORROW ({tomorrow})! Head to the magic portal: {settings.BASE_SITE_URL}/managementPortal/pickups_dropoffs/?date={tomorrow}"
                subject += "Outgoing Rentals Tomorrow"
            else:
                messageBody += f"{rentals_ending_tomorrow.count()} rentals coming in TOMORROW ({tomorrow})! Head to the magic portal: {settings.BASE_SITE_URL}/managementPortal/pickups_dropoffs/?date={tomorrow}"
                subject += "Incoming Rentals Tomorrow"

            # Overdue rental notice tacked on the end
            if overdue_rentals.exists():
                messageBody += " ...Oh and also, looks like you have an overdue rental. That means you either need to end the rental in ezRENT (if it's back in the yard) or you need to schedule a transport to bring it home!"

            managers = ManagementAlertNumber.objects.all()
            for manager in managers:
                try:
                    if manager.employee_notification_preference == 'text':
                        # send an alert text using the send_customer_text method (since it's customizable using arguments)
                        phone = manager.phone_number
                        send_customer_text(phone, messageBody)
                    else:
                        # send an email alert
                        receiver = manager.email
                        send_customer_email(receiver, subject, messageBody)
                except Exception as e:
                    print(f"Failed to send alert to {manager}: {e}")
        print("Rental alert cron job ended")