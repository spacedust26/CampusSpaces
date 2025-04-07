"""
URL configuration for CampusSpaces project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from home import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication routes
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    
    # Dashboard routes
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Booking routes
    path('spaces/', views.view_space, name='view_space'),
    path('spaces/<int:room_id>/', views.room_detail, name='room_detail'),
    path('equipment/', views.view_equipment, name='view_equipment'),
    path('equipment/<int:equipment_id>/', views.equipment_detail, name='equipment_detail'),
    path('history/', views.history, name='history'),
    path('booking-cart/', views.booking_cart, name='booking_cart'),
    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    
    # Approval routes
    path('approve-booking/<int:booking_id>/', views.approve_booking, name='approve_booking'),
    path('booking-approval/<int:booking_id>/', views.booking_approval_detail, name='booking_approval_detail'),
    
    # Notification routes
    path('notifications/', views.notifications, name='notifications'),
    path('mark-notification-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
]

# Add static file serving in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
