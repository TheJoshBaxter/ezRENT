# from django.contrib import admin  ### not registering models with the default admin any more, registering them ith my custom admin.
from django.contrib.admin import AdminSite
from django.conf import settings
from .models import EquipmentType, Equipment, RentalOrder, Inspection, RentalExtensions, ManagementAlertNumber

# Re-add the User and Group models that would've been included in default admin.
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin

class CustomAdminSite(AdminSite):
    site_header = "ezRENT Configuration Portal"
    site_title = "ezRENT Config Portal"
    index_title = "🏗⚙️🛠"
    site_url = f'{settings.BASE_SITE_URL}/managementPortal/'

# Create an instance of your custom admin site
custom_admin_site = CustomAdminSite()

# Register your models with the custom admin site
custom_admin_site.register(RentalOrder)
custom_admin_site.register(Equipment)
custom_admin_site.register(Inspection)
custom_admin_site.register(EquipmentType)
custom_admin_site.register(RentalExtensions)
custom_admin_site.register(ManagementAlertNumber)

# Re-register the User and Group models that would've been included in default admin.
custom_admin_site.register(User, UserAdmin)
custom_admin_site.register(Group, GroupAdmin)