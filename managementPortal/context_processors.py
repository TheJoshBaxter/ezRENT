from .models import RentalOrder

def global_notifications(request):
    unapprovedOrders = RentalOrder.objects.filter(rental_approved=False).order_by('rental_start_date')

    context = {}
    context['unapprovedOrders'] = unapprovedOrders

    return context