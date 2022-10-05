from django.contrib import admin

from apps.products.models import Product, PriceInterval

admin.site.register(Product)
admin.site.register(PriceInterval)
