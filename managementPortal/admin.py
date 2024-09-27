from django.contrib import admin
from .models import Equipment, RentalOrder, Inspection

# Register your models here.
admin.site.register(Equipment)
admin.site.register(RentalOrder)
admin.site.register(Inspection)