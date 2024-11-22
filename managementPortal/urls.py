from django.urls import path
from . import views

urlpatterns = [
    # path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('pending_rentals/', views.pending_rentals, name='pending_rentals'),
    path('pickups_dropoffs/', views.todays_pickups_dropoffs, name='todays_pickups_dropoffs'),
    path('inspections/', views.inspections, name='inspections'),
    path('customers/', views.customers, name='customers'),
    path('edit_customer/<int:customer_id>/', views.edit_customer, name='edit_customer'),
    path('delete_customer/<int:customer_id>/', views.delete_customer, name='delete_customer'),
    path('view_inspection/<int:order_id>/', views.view_inspection, name='view_inspection'),
    path('perform_inspection/<int:order_id>/', views.perform_inspection, name='perform_inspection'),
    path('extend_rental/<int:order_id>/', views.extend_rental, name='extend_rental'),
    path('end_rental/<int:order_id>/', views.end_rental, name='end_rental'),
    path('save_notes/<int:order_id>/', views.save_notes, name='save_notes'),
    path('approve_rental/<int:order_id>/', views.approve_rental, name='approve_rental'),
    path('', views.summary_dash, name='summary_dash'),
]
