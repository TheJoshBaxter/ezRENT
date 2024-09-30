from django.db import models
from customerPortal.models import Customer

# Create your models here.

class Equipment(models.Model):
    name = models.CharField(max_length=100)
    specs = models.TextField()
    cost_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    available_quantity = models.IntegerField()
    image = models.ImageField(upload_to='equipment_images/', null=True, blank=True)

    def __str__(self):
        return self.name

class RentalOrder(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    rental_start_date = models.DateField()
    rental_end_date = models.DateField()
    pickup_time = models.TimeField(null=True, blank=True) # not necessary
    dropoff_time = models.TimeField(null=True, blank=True) # not necessary
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.BooleanField(default=False)
    contract_signed = models.BooleanField(default=False)
    location = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.customer.user.username} - {self.equipment.name}"

class Inspection(models.Model):
    rental_order = models.ForeignKey(RentalOrder, on_delete=models.CASCADE)
    inspection_date = models.DateField(auto_now_add=True)
    fuel_return_level = models.CharField(max_length=3)
    cleaned = models.BooleanField(default=True)
    extras_rented = models.BooleanField(default=False)
    extras_returned = models.BooleanField(blank=True, null=True)
    notes = models.TextField(blank=True)
    photos = models.ImageField(upload_to='inspection_photos/', blank=True, null=True)

    def __str__(self):
        return f"Inspection for {self.rental_order.equipment.name} on {self.inspection_date}"
