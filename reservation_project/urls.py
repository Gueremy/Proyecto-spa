from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('booking.urls')),  # O el nombre de tu app, por ejemplo 'spa_reservas.urls'
]