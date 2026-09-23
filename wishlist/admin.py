from django.contrib import admin

from core.admin import ReadOnlyAdmin

from .models import Wishlist, WishlistItem

admin.site.register([Wishlist, WishlistItem], ReadOnlyAdmin)
