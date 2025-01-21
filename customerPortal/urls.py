from django.urls import path
from . import views

urlpatterns = [
    path('equipment_types/', views.equipment_types, {'template_name': 'equipment_types.html'}, name='equipment_types'),
    path('', views.equipment_types, {'template_name': 'customer_equipment_types.html'}, name='customer_equipment_types'), # HOME PAGE

    path('equipment_list/<int:equipmentTypeID>/', views.equipment_list, name='equipment_list'),

    path('equipment/<int:equipmentType_id>/', views.equipment_detail, {'template_name': 'equipment_detail.html'}, name='equipment_detail'),
    path('detailPage/<int:equipmentType_id>/', views.equipment_detail, {'template_name': 'customer_equipment_detail.html'}, name='customer_equipment_detail'),

    path('order_summary/', views.order_summary, {'template_name': 'order_summary.html'},  name='order_summary'),
    path('customer_summary/', views.order_summary, {'template_name': 'customer_order_summary.html'}, name='customer_order_summary'),

    path('confirmation/<int:orderID>', views.confirmation, {'template_name': 'confirmation.html'}, name='confirmation'),
    path('customer_confirmation/<int:orderID>', views.confirmation, {'template_name': 'customer_confirmation.html'}, name='customer_confirmation'),

    path('get_unavailable_dates/<int:equipmentType_id>/', views.get_unavailable_dates, name='get_unavailable_dates'),
    path('search_customers/', views.search_customers, name='search_customers'),
    path('update_payment_status/', views.update_payment_status, name='update_payment_status'),

    path('privacy_policy/', views.privacy_policy, name='privacy_policy'),
    path('terms_conditions/', views.terms_conditions,  name='terms_conditions'),
]