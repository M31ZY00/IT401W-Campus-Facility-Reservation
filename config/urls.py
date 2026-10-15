from django.urls import path, include

urlpatterns = [
    path('', include('dashboard.urls')),
    path('facilities/', include('facilities.urls')),
    path('accounts/', include('accounts.urls')),
    path('reservations/', include('reservations.urls')),
    path('manage/', include('management.urls')),
]