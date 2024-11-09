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
    weekly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    monthly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
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

    @property
    def rental_term_agreement(self): # (number of days until renewal or return)
        return (self.rental_end_date - self.rental_start_date).days

    def __str__(self):
        return f"Order #{self.id} - {self.customer.first_name} {self.customer.last_name} - {self.equipment.name} - Ending on {self.rental_end_date}"
    
class RentalExtensions(models.Model):
    rental_order = models.ForeignKey(RentalOrder, on_delete=models.CASCADE)
    original_end_date = models.DateField()
    days_extended = models.IntegerField()
    new_end_date = models.DateField()
    timestamp = models.DateTimeField()

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
