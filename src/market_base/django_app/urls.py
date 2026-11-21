"""Ready-to-use API URL patterns for marketplace delivery, webhooks and messengers."""

from django.urls import path

from market_base.django_app import views

app_name = 'market_base'

urlpatterns = [
    path('api/delivery/quote/', views.quote_delivery, name='quote_delivery'),
    path('api/delivery/autocomplete/', views.autocomplete_delivery_city, name='autocomplete_delivery_city'),
    path('api/delivery/pickup-points/', views.delivery_pickup_points, name='delivery_pickup_points'),
    path('api/messenger/bind/', views.bind_messenger, name='bind_messenger'),
]
