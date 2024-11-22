from django.contrib import admin
from .models import EquipmentType, Equipment, RentalOrder, Inspection, RentalExtensions, ManagementAlertNumber

# Register your models here.
admin.site.register(Equipment)
admin.site.register(RentalOrder)
admin.site.register(Inspection)
admin.site.register(EquipmentType)
admin.site.register(RentalExtensions)
admin.site.register(ManagementAlertNumber)

admin.site.site_header = "ezRENT Configuration Portal"
admin.site.site_title = "ezRENT Config Portal"
admin.site.index_title = "🏗⚙️🛠"