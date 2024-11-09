from django.urls import path
from . import views

urlpatterns = [
    path('', views.equipment_types, name='equipment_types'),
    path('equipment_list/<int:equipmentTypeID>/', views.equipment_list, name='equipment_list'),
    path('equipment/<int:equipmentType_id>/', views.equipment_detail, name='equipment_detail'),
    path('order_summary/', views.order_summary, name='order_summary'),
    path('confirmation/<int:orderID>', views.confirmation, name='confirmation'),
    path('get_unavailable_dates/<int:equipmentType_id>/', views.get_unavailable_dates, name='get_unavailable_dates'),
    path('search_customers/', views.search_customers, name='search_customers'),
    path('update_payment_status/', views.update_payment_status, name='update_payment_status'),
    
]