from django.contrib import admin
from django.urls import path
from . import views as main_views

urlpatterns = [
    path('', main_views.home),
    path('chart/<str:pool_id>/', main_views.price_chart, name='price_chart'),

    # API
    path('api-price/<str:pool_id>/', main_views.get_price, name='api-price'),
]
