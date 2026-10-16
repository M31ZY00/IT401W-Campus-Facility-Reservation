
from django.contrib import admin
from django.urls import path, include
from authentication.views import HomeLoginView

urlpatterns = [
    path('', HomeLoginView.as_view(), name='login'),
    path('auth/', include('authentication.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('facilities/', include('facilities.urls')),
    path('reservations/', include('reservations.urls')),
    path('manage/', include('management.urls')),
    path('admin/', admin.site.urls),
]
