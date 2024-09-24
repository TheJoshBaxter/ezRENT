from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Equipment, RentalOrder, Inspection
from datetime import date
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import UserRegisterForm


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
    orders = RentalOrder.objects.all()
    return render(request, 'employee_dashboard.html', {'orders': orders})

@login_required
def todays_pickups_dropoffs(request):
    today = date.today()
    outgoing_orders = RentalOrder.objects.filter(rental_start_date=today).order_by('pickup_time')
    returning_orders = RentalOrder.objects.filter(rental_end_date=today).order_by('dropoff_time')

    return render(request, 'pickups_dropoffs.html', {
        'outgoing_orders': outgoing_orders,
        'returning_orders': returning_orders,
    })

def perform_inspection(request, order_id):
    order = RentalOrder.objects.get(id=order_id)
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        photos = request.FILES.get('photos', None)
        inspection = Inspection.objects.create(
            rental_order=order,
            notes=notes,
            photos=photos
        )
        return redirect('employee_dashboard')
    return render(request, 'perform_inspection.html', {'order': order})
