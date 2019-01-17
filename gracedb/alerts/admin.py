from django.contrib import admin

from .models import Contact, Notification


class ContactManager(admin.ModelAdmin):
    pass

class NotificationManager(admin.ModelAdmin):
    pass

admin.site.register(Contact, ContactManager)
admin.site.register(Notification, NotificationManager)

