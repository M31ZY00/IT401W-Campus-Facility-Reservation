from django.urls import path
from django.contrib.auth.views import LogoutView

from . import views

urlpatterns = [

    path(
        '',
        views.HomeLoginView.as_view(),
        name='auth_login'
    ),

    path(
        'register/',
        views.register,
        name='register'
    ),

    path(
        'profile/',
        views.profile,
        name='profile'
    ),

    path(
        'logout/',
        LogoutView.as_view(),
        name='logout'
    ),

]