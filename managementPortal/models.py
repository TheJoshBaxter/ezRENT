from django.db import models
from customerPortal.models import Customer

# Create your models here.

class EquipmentType(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    specs = models.TextField()
    available_quantity = models.IntegerField()
    manufacturer = models.CharField(max_length=100, blank=True, null=True)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_daily_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Discounted Daily Rate (leave blank for no discount)")
    weekly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    discounted_weekly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Discounted Weekly Rate (leave blank for no discount)")
    monthly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    discounted_monthly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Discounted Monthly Rate (leave blank for no discount)")
    imgURL = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name
class Equipment(models.Model):
    name = models.CharField(max_length=100)
    equipment_type = models.ForeignKey(EquipmentType, on_delete=models.CASCADE)
    out_for_repairs = models.BooleanField(default=False, null=True)
    imgURL = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name
class RentalOrder(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    rental_start_date = models.DateField()
    rental_end_date = models.DateField()
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    paid = models.BooleanField(default=False)
    contract_signed = models.BooleanField(default=False)
    location = models.CharField(max_length=255)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    rental_approved = models.BooleanField(default=False, null=True)
    rental_returned = models.BooleanField(default=False, null=True)
    payment_receipt_url = models.CharField(max_length=100, default="noURL")

    @property
    def rental_term_agreement(self): # (number of days until renewal or return)
        return (self.rental_end_date - self.rental_start_date).days
    
    @property
    def is_fully_paid(self):
        # Check the rental order's paid status and any unpaid extensions
        return self.paid and not self.extensions.filter(paid=False).exists()

    def __str__(self):
        return f"Order #{self.id} - {self.customer.first_name} {self.customer.last_name} - {self.equipment.name} - Ending on {self.rental_end_date}"
    
class RentalExtensions(models.Model):
    rental_order = models.ForeignKey(RentalOrder, on_delete=models.CASCADE, related_name='extensions') # "related_name='extensions'" allows me to
    original_end_date = models.DateField()
    days_extended = models.IntegerField()
    new_end_date = models.DateField()
    timestamp = models.DateTimeField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    paid = models.BooleanField(default=False, null=True)
    payment_receipt_url = models.CharField(max_length=100, default="noURL")

    def __str__(self):
        return f"Extension for {self.rental_order} originally, now {self.new_end_date}"

class Inspection(models.Model):
    rental_order = models.ForeignKey(RentalOrder, on_delete=models.CASCADE)
    inspection_date = models.DateField(auto_now_add=True)
    fuel_return_level = models.CharField(max_length=5)
    cleaned = models.BooleanField(default=True)
    extras_rented = models.BooleanField(default=False)
    extras_returned = models.BooleanField(blank=True, null=True)
    notes = models.TextField(blank=True)
    photos = models.ImageField(upload_to='inspection_photos/', blank=True, null=True)

    def __str__(self):
        return f"Inspection for {self.rental_order.equipment.name} on {self.inspection_date}"

class ManagementAlertNumber(models.Model):

    ALERTS_PREFERENCE_CHOICES = [
        ('text', 'Text'),
        ('email', 'Email'),
    ]

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=15, unique=True) # Enforce uniqueness (phone number is unique id)
    email = models.EmailField(blank=True, null=True)
    employee_notification_preference = models.CharField(max_length=10, choices=ALERTS_PREFERENCE_CHOICES, default='email')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
class TransportRate(models.Model):
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return "Hourly Rate"
    
class TransportOrder(models.Model):
    rental_order = models.OneToOneField(RentalOrder, on_delete=models.CASCADE)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Transport Request for {self.rental_order}"
    
class CompanySetting(models.Model):
    company_name = models.CharField(max_length=100, blank=False, default="DemoRentals")
    company_phone = models.CharField(max_length=15, blank=False, default="8011231234")
    owner_name = models.CharField(max_length=100, blank=False, default="Demo Owner Signature")

    def __str__(self):
        return f"Company Settings for {self.company_name}"
    
class SignedContract(models.Model):
    date_signed = models.DateField()
    customer_signature = models.CharField(blank=False, max_length=50)
    business_signature = models.CharField(blank=False, max_length=50)
    agreement_box_checked = models.BooleanField(blank=False, default=True)
    associated_order = models.OneToOneField(RentalOrder, on_delete=models.CASCADE)

    def __str__(self):
        return f"SignedContract for {self.associated_order}"