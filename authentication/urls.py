from django.urls import path
from django.contrib.auth.views import LogoutView

from . import views


urlpatterns = [
    path('', views.HomeLoginView.as_view(), name='login'),   # first page: sign in

    path('register/', views.register, name='register'),

    path('home/', views.home, name='home'),                  # welcome page after login
    path('logout/', LogoutView.as_view(), name='logout'),
]