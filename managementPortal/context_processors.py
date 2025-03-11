from .models import RentalOrder
from .models import CompanySetting
from datetime import date

def global_notifications(request):
    today = date.today()

    unapprovedOrders = RentalOrder.objects.filter(rental_approved=False).order_by('-created_at')
    numUnapprovedOrders = len(unapprovedOrders)

    returnedOrdersPendingInspection = RentalOrder.objects.filter(inspection__isnull=True, rental_end_date__lte=today, rental_returned=True).order_by('rental_end_date')
    numPendingInspection = len(returnedOrdersPendingInspection)

    numAlerts = numUnapprovedOrders + numPendingInspection

    companyInfo = CompanySetting.objects.first()

    overdueRentals_exists = RentalOrder.objects.filter(rental_end_date__lt=today, rental_returned=False).exists()

    context = {}
    context['overdueRentals_exists'] = overdueRentals_exists
    context['unapprovedOrders'] = unapprovedOrders
    context['returnedOrdersPendingInspection'] = returnedOrdersPendingInspection
    context['numAlerts'] = numAlerts
    context['numUnapprovedOrders'] = numUnapprovedOrders
    context['companyInfo'] = companyInfo

    return context