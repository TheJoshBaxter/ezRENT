from django.shortcuts import render, redirect
from .models import Customer
from managementPortal.models import Equipment, EquipmentType, RentalOrder
from datetime import datetime, date, timedelta
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timezone import localtime
from decimal import Decimal

from customerPortal.square_client import get_square_client

# Create your views here.

def equipment_types(request):
    allEquipmentTypes = EquipmentType.objects.all().order_by('id')

    return render(request, 'equipment_types.html', {'allEquipmentTypes': allEquipmentTypes})


def equipment_list(request, equipmentTypeID):
    equipment = Equipment.objects.filter(equipment_type_id=equipmentTypeID)


    ### NEW AVAILABILITY CALCULATOR ###

    today = date.today()

    for item in equipment:
        # Fetch all reservations for each item starting from today
        unavailable_orders = RentalOrder.objects.filter(
            equipment_id=item.id,
            rental_end_date__gte=today
        ).values('rental_start_date', 'rental_end_date')

        # Create a list of all dates that fall between the start and end of each reservation for each item
        unavailable_dates = []
        for order in unavailable_orders:
            start_date = order['rental_start_date'] + timedelta(days=1) # this is incorrect--adjusting one day forward--to adjust for my bad timezone practices. TZ ISSUES
            end_date = order['rental_end_date'] + timedelta(days=1) # this is incorrect--adjusting one day forward--to adjust for my bad timezone practices TZ ISSUES
            date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days)]
            unavailable_dates.extend(date_range) # .extend() differs from .append(), which would add the entire date_range list as a single element. This way, each individual date from date_range gets added to unavailable_dates 

        # Sort the list to ensure chronological order
        unavailable_dates.sort()

        # Increment day by day and check if the date is unavailable
        next_available_date = today # Start checking from today
        while next_available_date in unavailable_dates:
            next_available_date += timedelta(days=1)

        if next_available_date == today:
            item.availability_message = "Available now"
        else:
            item.availability_message = f"Not available until {next_available_date}"

    return render(request, 'equipment_list.html', {'equipment': equipment})

# Equipment detail view for customerPortal
def equipment_detail(request, equipment_id):
    equipment = Equipment.objects.get(id=equipment_id)

    if request.method == 'POST':

        # Check if an existing customer was selected or a new one is being created
        if request.POST['first_name'].strip():  # If first_name from the DOM has contents and isn't an empty string, this is a New customer
            print("this is a BRAND spanking new customer")
            first_name = request.POST['first_name']
            last_name = request.POST['last_name']
            company_name = request.POST.get('company_name', '')
            phone_number = request.POST['phone_number']
            email = request.POST['email']

            start_date = request.POST['start_date']
            rental_period = int(request.POST['rental_period'])
            location = request.POST['location']

            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = start_date + timedelta(days=rental_period)

            # revert back to str format
            end_date = str(end_date)
            start_date = str(start_date)

            # Calculate total rental cost
            total_cost = calculate_total_cost(equipment, start_date, end_date, rental_period)
            print("data grab completed!!!!!")

            # Check if the user is an employee (authenticated)
            if request.user.is_authenticated:  # Employee - create new customer
                print("this user is authenticated...we should trust them to create the new customer if needed due to our awesome front end validations")
                customer = Customer.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    company_name=company_name,
                    phone_number=phone_number,
                    email=email
                )

                order_data = { # create an order for the newly created customer
                        'customer': customer.id,
                        'phone_number': phone_number,
                        'email': email,
                        'equipment': equipment.id,
                        'rental_start_date': start_date,
                        'rental_period': rental_period,
                        'rental_end_date': end_date,
                        'location': location,
                        'total_cost': float(total_cost),
                    }


            else: # Non-employee - see if customer already exists in the DB
                print("user is not authenticated...they're a customer theoretically...we should double check them to make sure they're not duplicating an existing customer record")
                exists = Customer.objects.filter(phone_number=phone_number, first_name__icontains=first_name, last_name__icontains=last_name).exists()

                if exists: # create an order with the matching customer data
                    print("CUSTOMER CHECK: customer already exists!")

                    customer = Customer.objects.get(phone_number=phone_number, first_name__icontains=first_name, last_name__icontains=last_name)

                    order_data = {
                        'customer': customer.id,
                        'phone_number': phone_number,
                        'email': email,
                        'equipment': equipment.id,
                        'rental_start_date': start_date,
                        'rental_period': rental_period,
                        'rental_end_date': end_date,
                        'location': location,
                        'total_cost': float(total_cost),
                    }

                else:
                    print("CUSTOMER CHECK: customer doesn't exist yet!")

                    try:
                        customer = Customer.objects.create(
                            first_name=first_name,
                            last_name=last_name,
                            company_name=company_name,
                            phone_number=phone_number,
                            email=email
                        )

                        order_data = { # then create a new order for the new customer
                            'customer': customer.id,
                            'phone_number': phone_number,
                            'email': email,
                            'equipment': equipment.id,
                            'rental_start_date': start_date,
                            'rental_period': rental_period,
                            'rental_end_date': end_date,
                            'location': location,
                            'total_cost': float(total_cost),
                        }
                    except: # this isn't great error catching as the user can still procede...edit in the future
                        order_data = {
                            'customer': "ERROR",
                            'phone_number': "ERROR: this phone number is already registered. Please EDIT INFO",
                            'email': email,
                            'equipment': equipment,
                            'rental_start_date': start_date,
                            'rental_period': rental_period,
                            'rental_end_date': end_date,
                            'location': location,
                            'total_cost': float(total_cost),
                        }

        else:  # Existing customer!
            print("You are using your fancy new customer dropdown functionality!")
            customer_name = request.POST['customerSearch']  # Assuming it's in the format "First Last"
            first_name, last_name = customer_name.split(' ')
            customer = Customer.objects.get(first_name=first_name, last_name=last_name)
            phone_number = request.POST['phone_number']
            email = request.POST['email']

            start_date = request.POST['start_date']
            rental_period = int(request.POST['rental_period'])
            location = request.POST['location']

            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = start_date + timedelta(days=rental_period)

            # revert back to str format
            end_date = str(end_date)
            start_date = str(start_date)

            # Calculate total rental cost
            total_cost = calculate_total_cost(equipment, start_date, end_date, rental_period)

            print("HELLO")
            print(customer.id)
            order_data = {
                'customer': customer.id,
                'phone_number': phone_number,
                'email': email,
                'equipment': equipment.id,
                'rental_start_date': start_date,
                'rental_period': rental_period,
                'rental_end_date': end_date,
                'location': location,
                'total_cost': float(total_cost),
            }

            # Store order_data in the session
            request.session['order_data'] = order_data


            return render(request, 'order_summary.html', {'order_data': order_data})
        
        # Store order_data in the session
        request.session['order_data'] = order_data
        return render(request, 'order_summary.html', {'order_data': order_data})

    return render(request, 'equipment_detail.html', {'equipment': equipment})

def search_customers(request):
    if request.method == 'GET':
        query = request.GET.get('query', '')
        customers = Customer.objects.filter(first_name__icontains=query) | Customer.objects.filter(last_name__icontains=query)
        results = [
            {
                'id': customer.id,
                'first_name': customer.first_name,
                'last_name': customer.last_name,
                'company_name': customer.company_name,
                'phone_number': customer.phone_number,
                'email_address': customer.email,
            } for customer in customers
        ]
        return JsonResponse({'results': results})

# Helper function to fetch unavailable dates for equipment
def get_unavailable_dates(request, equipment_id):
    today = date.today()

    ### TZ ISSUES ###
    # print("HEYO")
    # print(today)

    # current_time = timezone.localtime()
    # current_timezone = current_time.tzinfo
    # print(f"Current Time: {current_time}")
    # print(f"Timezone: {current_timezone}")
    ### TZ ISSUES ###

    # Fetch all reservations for this equipment starting from today
    unavailable_orders = RentalOrder.objects.filter(
        equipment_id=equipment_id,
        rental_end_date__gte=today
    ).values('rental_start_date', 'rental_end_date')

    # print(equipment_id)
    # print("unavailable orders")
    # print(unavailable_orders)

    # Create a list of all dates that fall between the start and end of each reservation
    unavailable_dates = []
    for order in unavailable_orders:
        start_date = order['rental_start_date'] + timedelta(days=0)
        end_date = order['rental_end_date'] + timedelta(days=1) # need at least 1 day after the reservation for inspection/turnaround
        date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
        unavailable_dates.extend(date_range) # .extend() differs from .append(), which would add the entire date_range list as a single element. This way, each individual date from date_range gets added to unavailable_dates

    # print("unavailable dates")
    # print(unavailable_dates) 

    # Return the unavailable dates as JSON for use in front-end manipulation of the date selectors on the equipment_detail template
    return JsonResponse({'unavailable_dates': unavailable_dates})

# Helper function to calculate total cost
def calculate_total_cost(equipment, start_date, end_date, rental_period):
    # create some logic to check the app settings (a future settings page needs to be created) to determine the desired pricing system (daily only, or daily, weekly, monthly rates)

    # Convert the date strings to date objects
    rental_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    rental_end = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    # Calculate the number of rental days
    rental_days = (rental_end - rental_start).days + 1  # Inclusive of the last day

    if rental_days < 7:
        rate = equipment.equipment_type.daily_rate
        numPeriods = rental_days
    elif rental_days >= 7 and rental_days < 28:
        rate = equipment.equipment_type.daily_rate
        numPeriods = rental_days//7
    else:
        rate = equipment.monthly_rate
        numPeriods = 1 # hard coded 1 because 1 month is the max time period option available to users
        
    # Calculate the total cost

    # total_cost = rental_days * equipment.daily_rate # THIS LINE TO BE USED IF "DAILY ONLY RATES" SETTINGS IS CHECKED
    total_cost = numPeriods * rate
    
    return total_cost

def order_summary(request):
    return render(request, 'order_summary.html')

def confirmation(request):

    # Retrieve order_data from session
    order_data = request.session.get('order_data', None)

    RentalOrder.objects.create(
        customer_id=order_data['customer'],
        equipment_id=order_data['equipment'],
        rental_start_date=order_data['rental_start_date'],
        rental_end_date=order_data['rental_end_date'],
        location=order_data['location'],
        total_cost=order_data['total_cost'],
    )
                                     
    # Store order_data in the session
    request.session['order_data'] = order_data

    # Get the Square client from the utility module
    square_client = get_square_client()

    # Access the client services, e.g., customers, payments
    customers_api = square_client.customers
    response = customers_api.create_customer(
        body={
            "given_name": "JohnnyBoy",
            "family_name": "Dough",
            "email_address": "john.doe@example.com"
        }
    )

    if response.is_success():
        customer_id = response.body['customer']['id']
        message = customer_id
        print("WE ARE TALKING TO SQUARE:")
        print(message)
        # Proceed with your logic, such as displaying a success message or redirecting
    else:
        # Handle errors appropriately
        print(response.errors)
        message = response.errors

    #   EMAIL? #
    # send_mail(
    #         'Proceed to Payment',
    #         f'Please proceed to sign contracts and make payment. Equipment: {equipment.name}. URL: /confirm/{equipment_id}/',
    #         settings.DEFAULT_FROM_EMAIL,
    #         [email],
    #         fail_silently=False,
    #     )
    
    return render(request, 'confirmation.html', {'message': message})