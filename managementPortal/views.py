from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Equipment, RentalOrder, Inspection
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import UserRegisterForm
import json
from django.http import JsonResponse

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

# Backend dashboard for business to manage orders and equipment
@login_required
def employee_dashboard(request):
    today = date.today()  # Get the current date

    # print(date.today())                            THESE ARE THE SAME FOR THE RECORD
    # print(timezone.now().date())

    filter_option = request.GET.get('filter', 'current')  # Get the filter option from query parameters, default to 'current'

    # Filter the RentalOrder queryset based on the selected filter option
    if filter_option == 'current':
        orders = RentalOrder.objects.filter(rental_end_date__gte=today, rental_start_date__lte=today).order_by('rental_end_date')
    elif filter_option == 'upcoming':
        orders = RentalOrder.objects.filter(rental_start_date__gt=today).order_by('rental_end_date')
    elif filter_option == 'past':
        orders = RentalOrder.objects.filter(rental_end_date__lt=today).order_by('rental_end_date')
    else:
        orders = RentalOrder.objects.all()  # 'all' or no filter

    # Add days remaining information to each order
    for order in orders:
        days_remaining = (order.rental_end_date - today).days
        order.days_remaining = days_remaining

    return render(request, 'employee_dashboard.html', {'orders': orders, 'filter_option': filter_option})

@login_required
def todays_pickups_dropoffs(request):
    # Get the date from the query parameters, defaulting to today if not provided
    selected_date_str = request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d')) # data from the user comes in string format 
    selected_date = timezone.datetime.strptime(selected_date_str, '%Y-%m-%d').date() # convert to datetime object and format

    # filter data according to user-selected date
    outgoing_orders = RentalOrder.objects.filter(rental_start_date=selected_date).order_by('pickup_time') 
    returning_orders = RentalOrder.objects.filter(rental_end_date=selected_date).order_by('dropoff_time')

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
        return redirect('todays_pickups_dropoffs')
    return render(request, 'perform_inspection.html', {'order': order})

def view_inspection(request, order_id):
    inspection = Inspection.objects.filter(rental_order_id=order_id).get()

    return render(request, 'view_inspection.html', {'inspection': inspection})

def extend_rental(request, order_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            days_to_extend = int(data.get('days_to_extend', 0))
            rental_order = RentalOrder.objects.get(id=order_id)
            rental_order.rental_end_date += timedelta(days=days_to_extend)
            rental_order.save()
            return JsonResponse({'success': True})
        except (RentalOrder.DoesNotExist, ValueError):
            return JsonResponse({'success': False}, status=400)
    return JsonResponse({'success': False}, status=405)

def end_rental(request, order_id):
    if request.method == 'POST':
        try:
            rental_order = RentalOrder.objects.get(id=order_id)
            rental_order.rental_end_date = date.today()
            rental_order.save()
            return JsonResponse({'success': True})
        except (RentalOrder.DoesNotExist, ValueError):
            return JsonResponse({'success': False}, status=400)
    return JsonResponse({'success': False}, status=405)

# Inspections view
def inspections(request):

    today = date.today()

    orders_without_inspections = RentalOrder.objects.filter(inspection__isnull=True, rental_end_date__lte=today).order_by('rental_end_date')
    orders_with_inspections = RentalOrder.objects.filter(inspection__isnull=False).order_by('rental_end_date')

    return render(request, 'inspections.html', {
        'orders_with_inspections': orders_with_inspections,
        'orders_without_inspections': orders_without_inspections
    })