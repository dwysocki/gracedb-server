
from .models import Contact, Trigger

from django.contrib import admin

class ContactManager(admin.ModelAdmin):
    pass
#   list_display = [ 'user', 'desc' ]

class TriggerManager(admin.ModelAdmin):
    pass
#   exclude = [ 'labels' ]
#   list_display = [ 'user', ]

admin.site.register(Contact, ContactManager)
admin.site.register(Trigger, TriggerManager)

