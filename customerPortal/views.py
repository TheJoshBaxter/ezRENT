from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from .models import Customer
from managementPortal.models import Equipment, EquipmentType, RentalOrder, RentalExtensions, TransportOrder, ManagementAlertNumber, CompanySetting, SignedContract
from datetime import datetime, date, timedelta
from django.http import JsonResponse, HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import io
from customerPortal.square_client import create_payment, create_order
# from customerPortal.twilioClient import send_text_alert
from customerPortal.twilioClient import send_customer_text
from customerPortal.emailClient import send_customer_email
from customerPortal.googleMapsClient import calculate_delivery_fee
from django.db.models import Q

# Create your views here.

def equipment_types(request, template_name):
    allEquipmentTypes = EquipmentType.objects.all().order_by('id')

    return render(request, template_name, {'allEquipmentTypes': allEquipmentTypes})


def equipment_list(request, equipmentTypeID):
    equipment = calc_availability_by_item(equipmentTypeID)
    # this function returns the equipment objects associated with equipmentTypeID WITH an item-unique availability message

    return render(request, 'equipment_list.html', {'equipment': equipment})

def calc_availability_by_item(equipmentTypeID):
    equipment = Equipment.objects.filter(equipment_type_id=equipmentTypeID, out_for_repairs=False) # grab all equipment of the requested equipment type EXCEPT those items marked as "out for repairs."

    today = date.today()
    print("Today isssssssssssss " + str(today))

    for item in equipment:

        # Fetch all reservations for each item starting from today
        unavailable_orders = RentalOrder.objects.filter(
            equipment_id=item.id,
            rental_end_date__gte=today
        ).values('rental_start_date', 'rental_end_date')

        # Create a list of all dates that fall between the start and end of each reservation for each item
        unavailable_dates = []
        for order in unavailable_orders:
            start_date = order['rental_start_date']
            end_date = order['rental_end_date'] + timedelta(days=1) # add an extra day of unavailability to account for the list comprehension stopping one day before end date. Could add one more for equipment transportation.
            date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days)]
            unavailable_dates.extend(date_range) # .extend() differs from .append(), which would add the entire date_range list as a single element. This way, each individual date from date_range gets added to unavailable_dates 

        # Sort the list to ensure chronological order
        unavailable_dates.sort()

        # Increment day by day and check if the date is unavailable
        next_available_date = today # Start checking from today
        while next_available_date in unavailable_dates:
            # print("checked " + str(next_available_date) + " and no good")

            # Check if the day is Saturday (5) or Sunday (6)
            if next_available_date.weekday() == 5:  # Saturday
                # Add 2 days to move to Monday
                # print("This is a saturday, adding two days to make it Monday (0)")
                next_available_date += timedelta(days=2)
                # print("now its " + str(next_available_date.weekday()))

            elif next_available_date.weekday() == 6:  # Sunday
                # Add 1 day to move to Monday
                # print("This is a sunday, adding 1 days to make it Monday (0)")
                next_available_date += timedelta(days=1)
                # print("now its " + str(next_available_date.weekday()))

            else:
                # if it's not a saturday or a sunday, increment by one day run the loop again
                next_available_date += timedelta(days=1)
        
        # print("supposedly " + str(next_available_date) + " is good...its a " + str(next_available_date.weekday()))

        print("Item " + str(item.id) + " is available on " + str(next_available_date))

        if next_available_date == today:
            item.availability_message = "Available now"
            item.nextAvailableDate = today
        else:
            item.availability_message = f"Not available until {next_available_date}"
            item.nextAvailableDate = next_available_date

    return equipment

def calc_aggregate_availability(equipmentTypeID):
    # for each equipment (item), get the availability message and compile availability:
    equipment_with_availability = calc_availability_by_item(equipmentTypeID)
    today = date.today()

    # get the earliest available date
    earliest_available_item = min(
        (item for item in equipment_with_availability if item.nextAvailableDate is not None),
        key=lambda x: x.nextAvailableDate, # The min() function takes an optional parameter called key, which expects a function that tells min() which part of each object it should use for comparison.
        default=None
    )

    if earliest_available_item:
        earliest_date = earliest_available_item.nextAvailableDate
        equipment_id = earliest_available_item.id # determine which item has the first available date
    else:
        earliest_date = None
        equipment_id = None
    
    # count any other items with the same availability date
    earliest_available_itemS = [item for item in equipment_with_availability if item.nextAvailableDate == earliest_date]
    num_available = len(earliest_available_itemS)
    
    # create one singular message for the type of equipment:
    if earliest_date == today:
        theAvailabilityMessage = f"{num_available} forklift(s) available starting today."
    else:
        theAvailabilityMessage = f"{num_available} forklift(s) available starting on {earliest_date}"

    print("AGGREGATE AVAILABILITY: earliest_available_itemS")
    print(earliest_available_itemS)
    
    context = {}
    context['aggregateEarliestDate'] = earliest_date
    context['theAvailabilityMessage'] = theAvailabilityMessage

    return context

# Equipment detail view for customerPortal
def equipment_detail(request, equipmentType_id, template_name):
    equipmentType = EquipmentType.objects.get(id=equipmentType_id)
    aggregateAvailabilityContext = calc_aggregate_availability(equipmentType_id)

    if request.method == 'POST':
        # grab the selected rentalEquipment ID that was identified as available for rental
        equipment_id = request.POST['equipmentIdField']

        # Check if an existing customer was selected or a new one is being created
        if request.POST['first_name'].strip():  # If first_name from the DOM has contents and isn't an empty string, this is a New customer
            print("this is a BRAND spanking new customer")
            first_name = request.POST['first_name']
            last_name = request.POST['last_name']
            company_name = request.POST.get('company_name', '')
            phone_number = request.POST['phone_number']
            email = request.POST['email']
            custNotificationPreference = request.POST['custNotificationPreference']

            start_date = request.POST['start_date']
            rental_period = int(request.POST['rental_period'])
            address = request.POST['address-line-1']
            apt_unit = request.POST['address-line-2']
            city = request.POST['city']
            state = request.POST['state']
            zip = request.POST['zip']

            dropoffLocation = f"{address} {apt_unit}, {city}, {state} {zip}"

            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = start_date + timedelta(days=rental_period)

            # revert back to str format
            end_date = str(end_date)
            start_date = str(start_date)

            # Calculate total rental cost
            total_cost = calculate_total_cost(equipmentType, rental_period)
            print("data grab completed!!!!!")

            # Prevent Duplicates
            print("ALWAYS should double check user to make sure they're not duplicating an existing customer record")
            exists = Customer.objects.filter(phone_number=phone_number, first_name__icontains=first_name, last_name__icontains=last_name).exists()

            if exists: # create an order with the matching customer data
                print("CUSTOMER CHECK: customer already exists!")

                customer = Customer.objects.get(phone_number=phone_number, first_name__icontains=first_name, last_name__icontains=last_name)

                order_data = {
                    'customer': customer.id,
                    'customer_fName': customer.first_name,
                    'customer_lName': customer.last_name,
                    'company': customer.company_name,
                    'phone_number': phone_number,
                    'email': email,
                    'equipmentType': equipmentType.name + " " + equipmentType.category,
                    'equipment': equipment_id,
                    'rental_start_date': start_date,
                    'rental_period': rental_period,
                    'rental_end_date': end_date,
                    'location': dropoffLocation,
                    'total_cost': float(total_cost),
                    'new_cust': False,
                    'cust_notification_preference': customer.cust_notification_preference
                }

            else:
                print("CUSTOMER CHECK: customer doesn't exist yet!")

                try:
                    customer = Customer.objects.create(
                        first_name=first_name,
                        last_name=last_name,
                        company_name=company_name,
                        phone_number=phone_number,
                        email=email,
                        cust_notification_preference=custNotificationPreference
                    )

                    order_data = { # then create a new order for the new customer
                        'customer': customer.id,
                        'customer_fName': customer.first_name,
                        'customer_lName': customer.last_name,
                        'company': customer.company_name,
                        'phone_number': phone_number,
                        'email': email,
                        'equipmentType': equipmentType.name + " " + equipmentType.category,
                        'equipment': equipment_id,
                        'rental_start_date': start_date,
                        'rental_period': rental_period,
                        'rental_end_date': end_date,
                        'location': dropoffLocation,
                        'total_cost': float(total_cost),
                        'new_cust': True,
                        'cust_notification_preference': custNotificationPreference
                    }
                except: 
                    order_data = {
                        'customer': "ERROR",
                        'phone_number': "ERROR: something went wrong (most likely you have entered the same phone number used in the past, but with a different name). Please EDIT INFO to make sure information is correct.",
                        'email': email,
                        'equipmentType': equipmentType.name + " " + equipmentType.category,
                        'equipment': equipment_id,
                        'rental_start_date': start_date,
                        'rental_period': rental_period,
                        'rental_end_date': end_date,
                        'location': dropoffLocation,
                        'total_cost': float(total_cost),
                    }

        else:  # Existing customer!
            print("You are using your fancy new customer dropdown functionality!")
            customer_name = request.POST['customerSearch']  # Assuming it's in the format "First Last"
            first_name, last_name = customer_name.split(' ')
            customer = Customer.objects.get(first_name=first_name, last_name=last_name)
            phone_number = request.POST['phone_number']
            email = request.POST['email']
            custNotificationPreference = request.POST['custNotificationPreference']

            start_date = request.POST['start_date']
            rental_period = int(request.POST['rental_period'])
            address = request.POST['address-line-1']
            apt_unit = request.POST['address-line-2']
            city = request.POST['city']
            state = request.POST['state']
            zip = request.POST['zip']

            dropoffLocation = f"{address} {apt_unit}, {city}, {state} {zip}"

            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = start_date + timedelta(days=rental_period)

            # revert back to str format
            end_date = str(end_date)
            start_date = str(start_date)

            # Calculate total rental cost
            total_cost = calculate_total_cost(equipmentType, rental_period)
            print(template_name)

            order_data = {
                'customer': customer.id,
                'customer_fName': customer.first_name,
                'customer_lName': customer.last_name,
                'company': customer.company_name,
                'phone_number': phone_number,
                'email': email,
                'equipmentType': equipmentType.name + " " + equipmentType.category,
                'equipment': equipment_id,
                'rental_start_date': start_date,
                'rental_period': rental_period,
                'rental_end_date': end_date,
                'location': dropoffLocation,
                'total_cost': float(total_cost),
                'new_cust': False,
                'cust_notification_preference': custNotificationPreference
            }

            # Store order_data in the session
            request.session['order_data'] = order_data

            # check whether the equipment_detail template is the customer version or the management version, and redirect to the corresponding orders_summary template
            if "customer" in template_name.lower():
                print("issa CUSTOMER")
                return redirect('customer_order_summary', )
            else:
                print(template_name)
                print(template_name.lower())
                print("ISS NOT A CUSTOMER")
                return redirect('order_summary', )
        
        # Store order_data in the session
        request.session['order_data'] = order_data

        # check whether the equipment_detail template is the customer version or the management version, and redirect to the corresponding orders_summary template
        if "customer" in template_name.lower():
            return redirect('customer_order_summary', )
        else:
            return redirect('order_summary', )

    return render(request, template_name, {'equipmentType': equipmentType, 'aggregateAvailabilityContext': aggregateAvailabilityContext})

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
                'cust_notification_preference': customer.cust_notification_preference
            } for customer in customers
        ]
        return JsonResponse({'results': results})

def get_unavailable_dates(request, equipmentType_id):
    today = date.today()
    unavailable_dates_by_item = {}

    # Retrieve all equipment items of the specified type
    equipment_items = Equipment.objects.filter(equipment_type_id=equipmentType_id)

    # Loop through each equipment item
    for equipment in equipment_items:
        # Fetch all active or upcoming rental orders for this equipment item
        unavailable_orders = RentalOrder.objects.filter(
            equipment_id=equipment.id,
            rental_end_date__gte=today
        ).values('rental_start_date', 'rental_end_date')

        # Create a list to store unavailable dates for the current equipment item
        item_unavailable_dates = []
        for order in unavailable_orders:
            start_date = order['rental_start_date']
            end_date = order['rental_end_date'] + timedelta(days=1)  # Adjust for turnaround time
            date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days)]
            item_unavailable_dates.extend(date_range)

        # Remove duplicates and sort dates for the current equipment item
        item_unavailable_dates = sorted(set(item_unavailable_dates))
        
        # Store the unavailable dates for this item in the dictionary
        unavailable_dates_by_item[equipment.id] = [date.strftime('%Y-%m-%d') for date in item_unavailable_dates]

    # Return JSON response with unavailable dates organized by equipment ID
    return JsonResponse({
        'unavailable_dates_by_item': unavailable_dates_by_item,
        'equipment': list(equipment_items.values('id'))
    })

# Helper function to calculate total cost
def calculate_total_cost(equipmentType, rental_period, request_type="new"): # if request_type is not provided when calling this function, default value "new" will be used, and it means that it is a new request, not an extension, and the function will check for discounts.
    # create some logic to check the app settings (a future settings page needs to be created) to determine the desired pricing system (daily only, or daily, weekly, monthly rates)

    if rental_period < 7:
        if request_type != "extension": # if request_type is not extension, check for discounts
            if equipmentType.discounted_daily_rate is not None and equipmentType.discounted_daily_rate > 0: # check for active discount
                rate = equipmentType.discounted_daily_rate
            else: # no active discount
                rate = equipmentType.daily_rate
        else: # this block executes if the request_type = extension. It does not check for discounts
            rate = equipmentType.daily_rate
        numPeriods = rental_period
    elif rental_period >= 7 and rental_period < 28:
        if request_type != "extension":
            if equipmentType.discounted_weekly_rate is not None and equipmentType.discounted_weekly_rate > 0:  # check for active discount
                rate = equipmentType.discounted_weekly_rate
            else:
                rate = equipmentType.weekly_rate
        else:
            rate = equipmentType.weekly_rate
        numPeriods = rental_period//7
    else:
        if request_type != "extension":
            if equipmentType.discounted_monthly_rate is not None and equipmentType.discounted_monthly_rate > 0: # check for active discount
                rate = equipmentType.discounted_monthly_rate
            else:
                rate = equipmentType.monthly_rate
        else:
            rate = equipmentType.monthly_rate
        numPeriods = 1 # hard coded 1 because 1 month is the max time period option available to users
        
    # Calculate the total cost

    # total_cost = rental_days * equipment.daily_rate # THIS LINE TO BE USED IF "DAILY ONLY RATES" SETTINGS IS CHECKED
    total_cost = numPeriods * rate
    
    return total_cost

def order_summary(request, template_name):

    context = {}

    # Retrieve order_data from session
    order_data = request.session.get('order_data', None)
    context['order_data'] = order_data

    # Calculate transport fee and add to context:
    delivery_fee = calculate_delivery_fee(order_data['location'], order_data['rental_period'])
    context['delivery_fee'] = delivery_fee

    # Calculate total cost by adding transport fee and rental cost
    context['grandTotal'] = float(order_data['total_cost']) + float(delivery_fee)

    if request.method == 'POST': # this is triggered when the user hits confirm and pay on the order summary page

        # Ensure no accidental duplicate order submissions
        existing_order = RentalOrder.objects.filter(
            Q(customer_id=order_data['customer']) &
            Q(equipment_id=order_data['equipment']) &
            Q(rental_start_date=order_data['rental_start_date']) &
            Q(rental_end_date=order_data['rental_end_date']) &
            Q(location=order_data['location']) &
            Q(total_cost=order_data['total_cost'])
        )#.exists()

        if existing_order.exists():
            print("This Rental Order has already been submitted. Duplication avoided successfully")
            existing_order_queryset = existing_order.values_list('id', flat=True)
            existing_order_id = existing_order_queryset[0]

            # Redirect to the confirmation view and pass the original order ID (WITHOUT SAVING DUPLICATE TO THE DB OR SENDING TEXT ALERTS)
            # check whether the equipment_detail template is the customer version or the management version, and redirect to the corresponding orders_summary template
            if "customer" in template_name.lower():
                return redirect('customer_confirmation', orderID=existing_order_id)
            else:
                return redirect('confirmation', orderID=existing_order_id)
        else:
            # Save the new order to the DB
            new_order = RentalOrder.objects.create(
                customer_id=order_data['customer'],
                equipment_id=order_data['equipment'],
                rental_start_date=order_data['rental_start_date'],
                rental_end_date=order_data['rental_end_date'],
                location=order_data['location'],
                total_cost=order_data['total_cost'],
            )
            print("Rental Order created in ezRENT successfully")

            new_transport_order = TransportOrder.objects.create(
                rental_order=new_order,
                cost=delivery_fee,
                paid=False,
            )

            print("Transport Order created in ezRENT successfully")

            # grab company name from DB to populate automated texts/emails
            company = CompanySetting.objects.first()

            # Send email or text (depending on preference) notification to each manager
            managers = ManagementAlertNumber.objects.all()
            for manager in managers:
                if manager.employee_notification_preference == 'text':
                    # send an alert text using the send_customer_text method (since it's customizable using arguments)
                    phone = manager.phone_number
                    messageBody = f"Ahoy there, you have a new rental order that needs to be reviewed. Check it out at {settings.BASE_SITE_URL}/managementPortal/pending_rentals/"
                    send_customer_text(phone, messageBody)
                else:
                    # send an email alert
                    receiver = manager.email
                    subject = "New Pending Rental Request"
                    body = f"Ahoy there, you have a new rental order that needs to be reviewed. Check it out at {settings.BASE_SITE_URL}/managementPortal/pending_rentals/.\n\nThanks!\n-ezRENT"
                    send_customer_email(receiver, subject, body)

            # Send email or text notification to customer depending on preference
            customerPreference = new_order.customer.cust_notification_preference
            
            if customerPreference == 'text':
                # send an alert text
                phone = new_order.customer.phone_number
                messageBody = f"Hello, {new_order.customer.first_name}, your rental request for an {new_order.equipment.equipment_type.name} {new_order.equipment.equipment_type.category} has been submitted! Your request is now being reviewed. If you haven't paid and signed the rental agreement, please visit {settings.BASE_SITE_URL}/customer_confirmation/{new_order.id}"
                send_customer_text(phone, messageBody)
            else:
                # send an email alert
                receiver = new_order.customer.email
                subject = "Rental Order Submitted"
                body = f"Hello, {new_order.customer.first_name},\n\nYour rental request for an {new_order.equipment.equipment_type.name} {new_order.equipment.equipment_type.category}, to be rented from {new_order.rental_start_date} to {new_order.rental_end_date}, has been submitted and is now being reviewed.\n\nPlease make sure you have signed the rental contract and paid for your rental by visiting the following link:\n{settings.BASE_SITE_URL}/customer_confirmation/{new_order.id}.\n\nYou can return to this link at any time. A second notification will be sent upon approval of your request.\n\nThanks for your business!\n-The {company.company_name} Team"
                send_customer_email(receiver, subject, body)
    
            # Redirect to the confirmation view and pass the order ID
            # check whether the equipment_detail template is the customer version or the management version, and redirect to the corresponding orders_summary template
            if "customer" in template_name.lower():
                return redirect('customer_confirmation', orderID=new_order.id)
            else:
                return redirect('confirmation', orderID=new_order.id)

    # this return is called on the inital load of the page, since the inital load is a GET not a POST
    return render(request, template_name, context)

def confirmation(request, orderID, template_name):

    newOrder = RentalOrder.objects.get(id=orderID)
    companyInfo = CompanySetting.objects.first()
    today = date.today()

    if settings.SQUARE_ENV == 'sandbox':
        sandboxed = True
    else:
        sandboxed = False

    # If the request method is POST, this means that the user has submitted their signed rental contract
    if request.method == 'POST':
        newOrder.contract_signed = True # mark contract signed as true in DB
        newOrder.save()

        # create a new instance of SignedContract
        signed_contract = SignedContract.objects.create(
            date_signed=today,
            customer_signature=request.POST['cust_signature'],
            business_signature=request.POST['biz_signature'],
            agreement_box_checked=True,
            associated_order=newOrder
        )

    try: # if there is a transport order, grab it, and calculate total cost by adding rental order cost and transport cost
        transportOrder = TransportOrder.objects.get(rental_order_id=orderID)
        initialTotalCost = newOrder.total_cost + transportOrder.cost
    
    except: # if there is no transport order, total cost will just be the initial order's total cost
        initialTotalCost = newOrder.total_cost

    orderExtensions = newOrder.extensions.all() # this grabs all RentalExtensions instances related to the Rental Order newOrder


    # add any existing extension orders to the initialTotalCost to find the grandTotalCost
    grandTotalCost = initialTotalCost

    if orderExtensions:
        for extension in orderExtensions:
            grandTotalCost += extension.cost

    context = {}
    context['today'] = date.today()
    context['order'] = newOrder
    context['sandboxed'] = sandboxed # used for showing/hiding square sandbox fake card info
    context['contract_signed'] = newOrder.contract_signed # if contract is signed, this will contain true
    context['paid'] = newOrder.paid # if order has been paid for, this will contain true
    context['initial_total_cost'] = initialTotalCost
    context['grand_total_cost'] = grandTotalCost
    context['order_id'] = orderID
    context['extensions'] = orderExtensions
    context['squareAppId'] = settings.SQUARE_APP_ID
    context['squareLocationId'] = settings.SQUARE_LOCATION_ID
    context['companyInfo'] = companyInfo

    return render(request, template_name, context)

# def generate_pdf_from_template(signed_contract): # generate a PDF from the contract_fragment HTML template
#     # Step 0: Grab necessary variables to populate the pdf
#     today = date.today()
#     companyInfo = CompanySetting.objects.first()

#     # Step 1: Render the HTML template as a string
#     html_string = render_to_string("contract_fragment.html", {"today": today}, {"companyInfo": companyInfo}, {"order": signed_contract.associated_order}, {"companyInfo": companyInfo})
    
#     # Step 2: Convert the HTML string into a PDF
#     pdf_file = BytesIO()
#     HTML(string=html_string).write_pdf(pdf_file)
    
#     # Step 3: Prepare the HTTP response with the PDF content
#     pdf_file.seek(0) # Move to the beginning of the file buffer
#     response = HttpResponse(pdf_file, content_type="application/pdf") # Sends the generated PDF file as an HTTP response
#     response["Content-Disposition"] = 'attachment; filename="document.pdf"' # Makes the PDF downloadable instead of displaying it in the browser
#     return response

def generate_pdf_from_template(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)

    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)

    if pdf.err:
        return None  # Handle the error appropriately in your view

    return result.getvalue()  # Returns the PDF file as bytes

def download_pdf(request, order_id):

    # Step 1: Grab necessary variables to populate the pdf
    today = date.today()
    companyInfo = CompanySetting.objects.first()
    signed_contract = SignedContract.objects.get(associated_order=order_id)  # Fetch the signed_contract instance
    context = { # Context to pass to the template
        "today": signed_contract.date_signed,
        "companyInfo": companyInfo,
        "order": signed_contract.associated_order,
        "companyInfo": companyInfo
        }  

    pdf_content = generate_pdf_from_template("contract_fragment.html", context)

    if not pdf_content:
        return HttpResponse("Error generating PDF", status=500)

    response = HttpResponse(pdf_content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Rental_contract_order_{signed_contract.associated_order.id}.pdf"'
    return response

def update_payment_status(request):
    if request.method == 'GET':
        extensionId = request.GET.get('extensionId', '')
        token = request.GET.get('token', '') # to be used for payment API
        orderId = request.GET.get('orderId', '')
        orderType = request.GET.get('orderType', '')

        order = RentalOrder.objects.get(id=orderId)
        transportOrder = TransportOrder.objects.get(rental_order=orderId)

        if orderType == 'extension': # if orderType contains 'extension' (set in the call in js), this is a rental extension payment, not an intial order payment.
            extension = RentalExtensions.objects.get(id=extensionId)
            cost_in_cents = int(extension.cost * 100)

            # create an order for receipting purposes
            order_data = create_order(orderType, order, cost_in_cents, extension)

            # if order creation was successful, use create_payment to take the payment
            if order_data.get("success"):

                result = create_payment(token, cost_in_cents, order_data) # execute create_payment, save the results to "result"
                if result.get("success"): #if the success key in the returned dict contains True (for successful payment), mark the extension as paid and save it.
                    extension.paid = True
                    extension.payment_receipt_url = result.get("receipt_url")
                    extension.save()
                else:
                    messages.error(request, "Payment failed. Please try again or contact support at the number above.", extra_tags=f"extensionPayment {extensionId}")

        else:
            try: # if there is a transport order, grab it, and calculate total cost by adding rental order cost and transport cost
                initialTotalCost = order.total_cost + transportOrder.cost
            
            except: # if there is no transport order, total cost will just be the initial order's total cost
                initialTotalCost = order.total_cost

            cost_in_cents = int(initialTotalCost * 100)

            # create an order for receipting purposes
            order_data = create_order(orderType, order, cost_in_cents)

            # if order creation was successful, use create_payment to take the payment
            if order_data.get("success"):

                result = create_payment(token, cost_in_cents, order_data) # execute create_payment, save the results to "result"
                if result.get("success"): #if the success key in the returned dict contains True (for successful payment), mark the order and transport as paid and save them.
                    order.paid = True
                    order.payment_receipt_url = result.get("receipt_url")
                    transportOrder.paid = True
                    order.save()
                    transportOrder.save()
                else:
                    messages.error(request, "Payment failed. Please try again or contact support at the number above.", extra_tags="initialPayment")

        return redirect('confirmation', orderID=orderId)
    
def privacy_policy(request):
    return render(request, 'privacy_policy.html')

def terms_conditions(request):
    return render(request, 'terms_conditions.html')