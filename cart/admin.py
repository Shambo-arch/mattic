from django.contrib import admin

from core.admin import ReadOnlyAdmin

from .models import Cart, CartItem

admin.site.register([Cart, CartItem], ReadOnlyAdmin)
