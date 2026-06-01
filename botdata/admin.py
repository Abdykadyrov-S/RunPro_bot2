from django.contrib import admin
from django.db import connection

from .models import Chat, Dispatcher, Driver, Load


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "chat_id")
    search_fields = ("name", "chat_id")
    ordering = ("name", "id")


@admin.register(Dispatcher)
class DispatcherAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "telegram_user_id")
    search_fields = ("name", "telegram_user_id")
    ordering = ("name", "id")


@admin.register(Load)
class LoadAdmin(admin.ModelAdmin):
    list_display = (
        "load_number",
        "driver",
        "dispatcher",
        "broker",
        "rate",
        "miles",
        "pu_date",
        "del_date",
    )
    list_filter = ("dispatcher", "driver")
    search_fields = ("load_number", "broker", "driver__name", "dispatcher__name")
    autocomplete_fields = ("driver", "dispatcher")
    ordering = ("-id",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.driver_id and obj.dispatcher_id:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO driver_dispatcher (driver_id, dispatcher_id)
                    VALUES (%s, %s)
                    ON CONFLICT (driver_id, dispatcher_id) DO NOTHING
                    """,
                    [obj.driver_id, obj.dispatcher_id],
                )


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("chat_id", "title")
    search_fields = ("title", "chat_id")
