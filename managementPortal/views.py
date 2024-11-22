from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import RentalOrder, Inspection, Customer, RentalExtensions, EquipmentType
from datetime import date, timedelta, datetime
from django.utils import timezone
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.db.models import Sum
from .forms import UserRegisterForm
import json
from django.http import JsonResponse
# from customerPortal.square_client import get_square_client
from django.conf import settings
from customerPortal.views import calculate_total_cost
from customerPortal.emailClient import send_customer_email
from customerPortal.twilioClient import send_customer_text

# Create your views here.
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()  # Save the user
            messages.success(request, f'Your account has been created! You can now log in.')
            return redirect('login')  # Redirect to login after successful registration
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})

# Login view
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('employee_dashboard')  # Redirect to equipment list after successful login
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

# Logout view
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def summary_dash(request):
    today = date.today()

    # Monthly Revenue
    monthlyOrders = RentalOrder.objects.filter(
        rental_start_date__year=today.year,
        rental_start_date__month=today.month,
        paid=True
    )
    totalMonthOrderRevenue = monthlyOrders.aggregate(Sum('total_cost'))['total_cost__sum'] or 0.00

    totalMonthExtensionRevenue = RentalExtensions.objects.filter(
        rental_order__in=monthlyOrders,
        paid=True
    ).aggregate(Sum('cost'))['cost__sum'] or 0.00

    # Yearly Revenue
    yearlyOrders = RentalOrder.objects.filter(
        rental_start_date__year=today.year,
        paid=True
    )
    totalYearOrderRevenue = yearlyOrders.aggregate(Sum('total_cost'))['total_cost__sum'] or 0.00

    totalYearExtensionRevenue = RentalExtensions.objects.filter(
        rental_order__in=yearlyOrders,
        paid=True
    ).aggregate(Sum('cost'))['cost__sum'] or 0.00

    # Total Revenue
    monthlyRev = totalMonthOrderRevenue + totalMonthExtensionRevenue
    annualRev = totalYearOrderRevenue + totalYearExtensionRevenue

    # Percentage AR Received:
    #something here
    
    context = {}
    context['monthlyRev'] = monthlyRev
    context['anualRev'] = annualRev
    return render(request, 'summary_dash.html', context)


# Backend dashboard for business to manage orders and equipment
@login_required
def employee_dashboard(request):
    today = date.today()  # Get the current date
    # print(date.today())                            THESE ARE THE SAME FOR THE RECORD
    # print(timezone.now().date())

    context = {}

    filter_option = request.GET.get('filter', 'current')  # Get the filter option from query parameters, default to 'current'

    # Filter the RentalOrder queryset based on the selected filter option
    if filter_option == 'current':
        orders = RentalOrder.objects.filter(rental_end_date__gte=today, rental_start_date__lte=today, rental_approved=True, rental_returned=False).order_by('rental_end_date')
    elif filter_option == 'upcoming':
        orders = RentalOrder.objects.filter(rental_start_date__gt=today, rental_approved=True).order_by('rental_end_date')
    elif filter_option == 'past':
        orders = RentalOrder.objects.filter(rental_end_date__lt=today, rental_approved=True).order_by('rental_end_date')
    elif filter_option == 'new':
        orders = RentalOrder.objects.filter(rental_approved=True).order_by('-created_at')
    else:
        orders = RentalOrder.objects.filter(rental_approved=True).order_by('rental_end_date')

    # Add days remaining information to each order
    for order in orders:
        # get inspection data associated with an order (assuming inspection has been performed)
        inspection = Inspection.objects.filter(rental_order_id=order.id)
        order.inspection = inspection

        # get all extensions associated with each order
        extensions = get_extensions(order.id)
        order.extensions = extensions
        order.numExtensions = extensions.count()

        # get days remaining for each order
        days_remaining = (order.rental_end_date - today).days
        order.days_remaining = days_remaining # used to color icons based on proximity of end date

        # grab the potential end date to be populated in the end_rental modal
        if order.rental_end_date <= today:
            order.potential_end_date = order.rental_end_date
        else:
            order.potential_end_date = today

        # get the last inspection data for the equipment id associated with each order
        try:
            lastInspection = get_last_inspection(order.equipment_id)
            order.starting_fuel_status = lastInspection.fuel_return_level
            
            if lastInspection.cleaned:
                order.start_condition_status = "Clean"
            else:
                order.start_condition_status = "Dirty"
        except:
            order.start_condition_status = "Clean"
            order.starting_fuel_status = "Full"

    context['orders'] = orders
    context['filter_option'] = filter_option
    context['today'] = today

    return render(request, 'employee_dashboard.html', context)

def pending_rentals(request):
    pendingOrders = RentalOrder.objects.filter(rental_approved=False).order_by('rental_start_date')

    for order in pendingOrders:
        order.unavailableDates = get_unavailable_dates(order.equipment_id)

    context = {}
    context['pendingOrders'] = pendingOrders
    
    return render(request, 'pending_rentals.html', context)

def approve_rental(request, order_id):
    # Get the RentalOrder instance
    order = get_object_or_404(RentalOrder, id=order_id)
    
    if request.method == 'POST':
        # Mark the rental as approved (you can update any field in your model)
        order.rental_approved = True
        order.save()

        # Send email or text notification to customer depending on preference
        customerPreference = order.customer.cust_notification_preference

        if customerPreference == 'text':
            # send an alert text
            phone = order.customer.phone_number
            messageBody = f"Hello, {order.customer.first_name} 👋, your rental request for a {order.equipment.equipment_type.name} {order.equipment.equipment_type.category} has been approved! For next steps, please visit {settings.BASE_SITE_URL}/confirmation/{order.id}"
            # send_customer_text(phone, messageBody)
        else:
            # send an email alert
            receiver = order.customer.email
            subject = "Rental Order Approval Notification"
            body = f"Hello, {order.customer.first_name} 👋,\n\nYour rental request for a {order.equipment.equipment_type.name} {order.equipment.equipment_type.category}, to be rented from {order.rental_start_date} to {order.rental_end_date}, has been approved!\n\nThe {order.equipment.equipment_type.category} will be delivered to {order.location} on the specified start date of the reservation.\n\nPlease make sure you have signed the rental contract and paid for your rental by visiting {settings.BASE_SITE_URL}/confirmation/{order.id}.\n\nThanks for your business!\n\n-The Jobsite Rents Team"
            # send_customer_email(receiver, subject, body)

        # Redirect to a confirmation page or the updated rental order page
        return redirect('employee_dashboard')

@login_required
def save_notes(request, order_id):
    if request.method == 'POST':

        orderToChange = RentalOrder.objects.filter(id=order_id).get()

        # Update Customer fields
        customer = orderToChange.customer  # Access the related Customer instance
        customer.first_name = request.POST['customerFN']
        customer.last_name = request.POST['customerLN']
        customer.save()  # Save changes to the Customer model

        # Update RentalOrder fields
        stringStartDate = request.POST['startDate']
        orderToChange.rental_start_date = datetime.strptime(stringStartDate, "%Y-%m-%d") # convert to datetime object
        rentalTerm = int(request.POST['rentalTerm'])
        orderToChange.rental_end_date = orderToChange.rental_start_date + timedelta(days=rentalTerm)  # Adjust start date if necessary
        orderToChange.location = request.POST['rentalLocation']
        orderToChange.notes = request.POST['notes']
        orderToChange.save()  # Save changes to the RentalOrder model

        return redirect('employee_dashboard')
    
    return redirect('employee_dashboard')

def get_extensions(rental_order_ID):
    extensions = RentalExtensions.objects.filter(rental_order=rental_order_ID)

    return extensions #returns a query set


def get_last_inspection(equipment_id):
    lastInspection = (
        Inspection.objects
        .filter(rental_order__equipment=equipment_id)  # Filter by equipment ID
        .order_by('-inspection_date')  # Order by inspection date in descending order
        .first()  # Get the first result (most recent inspection)
    )

    return lastInspection

@login_required
def todays_pickups_dropoffs(request):
    # Get the date from the query parameters, defaulting to today if not provided
    selected_date_str = request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d')) # data from the user comes in string format 
    selected_date = timezone.datetime.strptime(selected_date_str, '%Y-%m-%d').date() # convert to datetime object and format

    # filter data according to user-selected date
    outgoing_orders = RentalOrder.objects.filter(rental_start_date=selected_date) 
    returning_orders = RentalOrder.objects.filter(rental_end_date=selected_date)

    # this block determines if each returning item has already been inspected or not
    for item in returning_orders:
        exists = Inspection.objects.filter(rental_order_id=item.id).exists()
        if exists:
            item.inspected = True
        else:
            item.inspected = False


    return render(request, 'pickups_dropoffs.html', {
        'outgoing_orders': outgoing_orders,
        'returning_orders': returning_orders,
        'selected_date': selected_date_str,
    })

# Inspections view
@login_required
def inspections(request):

    today = date.today()

    orders_without_inspections = RentalOrder.objects.filter(inspection__isnull=True, rental_end_date__lte=today, rental_returned=True).order_by('rental_end_date')
    orders_with_inspections = RentalOrder.objects.filter(inspection__isnull=False).order_by('-rental_end_date')

    return render(request, 'inspections.html', {
        'orders_with_inspections': orders_with_inspections,
        'orders_without_inspections': orders_without_inspections
    })

@login_required
def perform_inspection(request, order_id):
    order = RentalOrder.objects.get(id=order_id)
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        photos = request.FILES.get('photos', None)
        cleaned = request.POST.get('cleaned')
        extrasRented = request.POST.get('extrasRented')
        extrasReturned = request.POST.get('extrasReturned')
        fuelReturnLevel = request.POST.get('fuelReturnLevel')
        inspection = Inspection.objects.create(
            rental_order=order,
            notes=notes,
            photos=photos,
            cleaned=cleaned,
            extras_rented=extrasRented,
            extras_returned=extrasReturned,
            fuel_return_level=fuelReturnLevel
        )
        return redirect('inspections')
    return render(request, 'perform_inspection.html', {'order': order})

@login_required
def view_inspection(request, order_id):
    inspection = Inspection.objects.filter(rental_order_id=order_id).get()

    return render(request, 'view_inspection.html', {'inspection': inspection})

@login_required
def extend_rental(request, order_id):
    if request.method == 'POST':
        try:
            #first, update the RentalOrder data
            data = json.loads(request.body)
            days_to_extend = int(data.get('days_to_extend', 0))
            rental_order = RentalOrder.objects.get(id=order_id)
            ogEndDate = rental_order.rental_end_date # saving for exension data creation
            rental_order.rental_end_date += timedelta(days=days_to_extend)
            rental_order.save()

            # grab equipment type, and feed it and rental extension period to the calculate_total_cost method (from other views file)
            equipmentTypeId = rental_order.equipment.equipment_type.id # grab the type id in order to grab the instance
            equipmentType = EquipmentType.objects.get(id=equipmentTypeId) # grab instance (contains the three rates)
            extensionCost = calculate_total_cost(equipmentType, days_to_extend)

            # second, save extension data to the rental extensions table:
            RentalExtensions.objects.create(
                original_end_date = ogEndDate,
                days_extended = days_to_extend,
                new_end_date = rental_order.rental_end_date,
                timestamp = date.today(),
                rental_order_id = order_id,
                extension_cost = extensionCost
            )

            # then mark the order as not fully paid

            # notify customer of outstanding payment
            if rental_order.customer.cust_notification_preference == 'text':
                # send an alert text
                phone = rental_order.customer.phone_number
                messageBody = f"Hello, {rental_order.customer.first_name} 👋, your request for an extension on your rental ({rental_order.equipment.equipment_type.name} {rental_order.equipment.equipment_type.category}) has been approved! Please confirm details and complete payment by visiting {settings.BASE_SITE_URL}/confirmation/{rental_order.id}."
                # send_customer_text(phone, messageBody)
            else:
                # send an email alert
                receiver = rental_order.customer.email
                subject = "Rental Order Approval Notification"
                body = f"Hello, {rental_order.customer.first_name} 👋,\n\nYour request for an extension on your rental of our ({rental_order.equipment.equipment_type.name} {rental_order.equipment.equipment_type.category}), originally rented from {rental_order.rental_start_date} to {rental_order.rental_end_date}, has been approved!\n\n Please confirm extension details and complete payment for your rental extension by visiting {settings.BASE_SITE_URL}/confirmation/{rental_order.id}.\n\nThanks for your business!\n\n-The Jobsite Rents Team"
                # send_customer_email(receiver, subject, body)

            return JsonResponse({'success': True})
        except (RentalOrder.DoesNotExist, ValueError):
            return JsonResponse({'success': False}, status=400)
    return JsonResponse({'success': False}, status=405)

@login_required
def end_rental(request, order_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            end_date_str = data.get('end_date')
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            rental_order = RentalOrder.objects.get(id=order_id)
            rental_order.rental_end_date = end_date
            rental_order.rental_returned = True
            rental_order.save()

            return JsonResponse({'success': True})
        except (RentalOrder.DoesNotExist, ValueError):
            return JsonResponse({'success': False}, status=400)
    return JsonResponse({'success': False}, status=405)

@login_required
def customers(request):
    customers = Customer.objects.all().order_by('first_name')

    return render(request, 'customers.html', {'customers': customers})

@login_required
def edit_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)

    if request.method == 'POST':
        customer.first_name = request.POST['first_name']
        customer.last_name = request.POST['last_name']
        customer.company_name = request.POST.get('company_name', '')
        customer.phone_number = request.POST['phone_number']
        customer.email = request.POST['email']
        customer.save()

        return redirect('customers')  # Redirect to the customer list page after saving

    return render(request, 'customers.html', {'customer': customer})

@login_required
def delete_customer(request, customer_id):
    # Get the customer object or return 404 if it doesn't exist
    customer = get_object_or_404(Customer, id=customer_id)
    customer.delete()  # Delete the customer from the database

    return redirect('customers')  # Redirect back to the customer list page

def get_unavailable_dates(equipment_id):
    today = date.today()

    # Fetch all reservations for this equipment starting from today
    unavailable_orders = RentalOrder.objects.filter(
        equipment_id=equipment_id,
        rental_end_date__gte=today,
        rental_approved=True
    )

    unavailablePeriods = []

    for order in unavailable_orders:
        formattedStart = order.rental_start_date.strftime('%b %d')
        formattedEnd = order.rental_end_date.strftime('%b %d, %Y')
        unavailablePeriods.append(f"{formattedStart} - {formattedEnd}")

    return unavailablePeriods