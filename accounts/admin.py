from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone", "is_active_worker", "created_at")
    list_filter = ("role", "is_active_worker")
    search_fields = ("user__username", "user__email", "phone")

# Register your models here.
