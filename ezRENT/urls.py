"""
URL configuration for ezRENT project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
from managementPortal.admin import custom_admin_site # use the custom Admin
from django.urls import path, include

urlpatterns = [
    path('admin/', custom_admin_site.urls),
    path('customerPortal/', include('customerPortal.urls')),
    path('managementPortal/', include('managementPortal.urls')),
    path('', include('customerPortal.urls')),  # Default route redirects to customers
]
