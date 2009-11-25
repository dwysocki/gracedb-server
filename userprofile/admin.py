
from models import AnalysisType, Contact, Trigger

from django.contrib import admin

class AnalysisTypeManager(admin.ModelAdmin):
    list_display = [ 'display' ]

class ContactManager(admin.ModelAdmin):
    pass
#   list_display = [ 'user', 'desc' ]

class TriggerManager(admin.ModelAdmin):
    pass
#   exclude = [ 'labels' ]
#   list_display = [ 'user', ]

admin.site.register(AnalysisType, AnalysisTypeManager)
admin.site.register(Contact, ContactManager)
admin.site.register(Trigger, TriggerManager)

