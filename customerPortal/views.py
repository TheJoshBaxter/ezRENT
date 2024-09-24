from django.shortcuts import render, redirect
from .models import Customer
from managementPortal.models import Equipment, RentalOrder
from datetime import datetime, date, timedelta
from django.core.mail import send_mail
from django.conf import settings

# Create your views here.

# Equipment list view for customerPortal
def equipment_list(request):
    equipment = Equipment.objects.all()

    # Determine availability for each equipment item
    for item in equipment:
        today = date.today()
        next_reservation = RentalOrder.objects.filter(equipment=item, rental_start_date__gte=today).order_by('rental_start_date').first()

        if next_reservation and next_reservation.rental_start_date == today:
            item.availability_message = f"Available until {next_reservation.rental_start_date - timedelta(days=1)}"
        elif next_reservation:
            item.availability_message = f"Available starting on {next_reservation.rental_start_date}"
        else:
            item.availability_message = "Available now"

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
        pickup_time = request.POST['pickup_time']
        dropoff_time = request.POST['dropoff_time']
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
            pickup_time=pickup_time,
            dropoff_time=dropoff_time,
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