from .models import RentalOrder
from datetime import date

def global_notifications(request):
    today = date.today()

    unapprovedOrders = RentalOrder.objects.filter(rental_approved=False).order_by('-created_at')
    numUnapprovedOrders = len(unapprovedOrders)

    returnedOrdersPendingInspection = RentalOrder.objects.filter(inspection__isnull=True, rental_end_date__lte=today, rental_returned=True).order_by('rental_end_date')
    numPendingInspection = len(returnedOrdersPendingInspection)

    numAlerts = numUnapprovedOrders + numPendingInspection

    context = {}
    context['unapprovedOrders'] = unapprovedOrders
    context['returnedOrdersPendingInspection'] = returnedOrdersPendingInspection
    context['numAlerts'] = numAlerts
    context['numUnapprovedOrders'] = numUnapprovedOrders

    return context