from django.urls import path
from django.contrib.auth.views import LogoutView

from . import views


urlpatterns = [
    path(
        'register/',
        views.register,
        name='register'
    ),

    path(
        'login/',
        views.StudentLoginView.as_view(),
        name='login'
    ),

    path(
        'admin-login/',
        views.AdminLoginView.as_view(),
        name='admin_login'
    ),

    path(
        'logout/',
        LogoutView.as_view(),
        name='logout'
    ),
]