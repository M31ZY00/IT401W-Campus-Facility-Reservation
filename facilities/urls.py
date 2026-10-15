from django.urls import path
from . import views

urlpatterns = [
    path('', views.facility_list, name='facility_list'),
    path('<int:facility_id>/', views.facility_detail, name='facility_detail'),
]