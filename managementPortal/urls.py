from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('pickups_dropoffs/', views.todays_pickups_dropoffs, name='todays_pickups_dropoffs'),
    path('perform_inspection/<int:order_id>/', views.perform_inspection, name='perform_inspection'),
]
