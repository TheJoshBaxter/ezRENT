from django.shortcuts import render, redirect
from .models import Customer
from managementPortal.models import Equipment, RentalOrder
from datetime import datetime, date, timedelta
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timezone import localtime

# Create your views here.

# Equipment list view for customerPortal
def equipment_list(request):
    equipment = Equipment.objects.all()

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
        # Step 1: Collect form data
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        company_name = request.POST.get('company_name', '')
        phone_number = request.POST['phone_number']
        email = request.POST['email']
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        # pickup_time = request.POST['pickup_time']
        # dropoff_time = request.POST['dropoff_time']
        location = request.POST['location']
        print('step 1 grabbed data complete')

        # Step 2: Save customer information
        customer = Customer.objects.create(
            first_name=first_name,
            last_name=last_name,
            company_name=company_name,
            phone_number=phone_number,
            email=email

        )
        print('step 2, created new customer')

        # Step 3: Calculate total rental cost
        total_cost = calculate_total_cost(equipment, start_date, end_date)
        print('step 3 calculated total cost')

        # Step 4: Save the rental order
        RentalOrder.objects.create(
            customer=customer,
            equipment=equipment,
            rental_start_date=start_date,
            rental_end_date=end_date,
            # pickup_time=pickup_time,
            # dropoff_time=dropoff_time,
            location=location,
            total_cost=total_cost,
        )
        print('step 4 created rentalOrder object')

        # Step 5: Grab the ID for the order just created:
        lastOrder = RentalOrder.objects.last()
        lastOrder_ID = lastOrder.id
        print('step 5 completed (lastOrderID set) now going to order_summary')
        print(lastOrder_ID)

        return redirect('order_summary', lastOrder_ID)
    return render(request, 'equipment_detail.html', {'equipment': equipment})

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
        start_date = order['rental_start_date'] + timedelta(days=1) # this is incorrect--adjusting one day forward--to adjust for my bad timezone practices. TZ ISSUES
        end_date = order['rental_end_date'] + timedelta(days=1) # this is incorrect--adjusting one day forward--to adjust for my bad timezone practices TZ ISSUES
        date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
        unavailable_dates.extend(date_range) # .extend() differs from .append(), which would add the entire date_range list as a single element. This way, each individual date from date_range gets added to unavailable_dates

    # print("unavailable dates")
    # print(unavailable_dates) 

    # Return the unavailable dates as JSON for use in front-end manipulation of the date selectors on the equipment_detail template
    return JsonResponse({'unavailable_dates': unavailable_dates})

# Helper function to calculate total cost
def calculate_total_cost(equipment, start_date, end_date):
    # Convert the date strings to date objects
    rental_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    rental_end = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    # Calculate the number of rental days
    rental_days = (rental_end - rental_start).days + 1  # Inclusive of the last day
    
    # Calculate the total cost
    total_cost = rental_days * equipment.cost_per_day
    return total_cost

def order_summary(request, lastOrder_ID):
    order = RentalOrder.objects.get(id=lastOrder_ID)
    print('made it to order summary')
    return render(request, 'order_summary.html', {'order': order})

def confirmation(request):
    print('made it to order confirmation!!!')
    # send_mail(
    #         'Proceed to Payment',
    #         f'Please proceed to sign contracts and make payment. Equipment: {equipment.name}. URL: /confirm/{equipment_id}/',
    #         settings.DEFAULT_FROM_EMAIL,
    #         [email],
    #         fail_silently=False,
    #     )
    
    return render(request, 'confirmation.html')