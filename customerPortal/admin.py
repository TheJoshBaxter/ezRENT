# from django.contrib import admin
from managementPortal.admin import custom_admin_site
from .models import Customer

# Register your models here.
custom_admin_site.register(Customer)