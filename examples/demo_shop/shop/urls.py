from django.urls import include, path

from shop import views

app_name = 'shop'

urlpatterns = [
    path('cart/summary/', views.cart_summary, name='cart_summary'),
    path('webhook/yookassa/', views.webhook_view, name='yookassa_webhook'),
    path('base/', include('market_base.django_app.urls')),
]
