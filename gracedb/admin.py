
from models import Event, EventLog, User, Group
from models import Label, Labelling, Slot
from django.contrib import admin

class EventAdmin(admin.ModelAdmin):
    def analysis_type(obj):
        return obj.get_analysisType_display()
    analysis_type.admin_order_field = 'analysisType'

    def graceid(obj):
        return obj.graceid()
    graceid.admin_order_field = 'id'

    list_display = [ graceid, 'group', analysis_type, 'submitter'  ]
    search_fields = [ 'group__name', 'submitter__name' ]

class UserAdmin(admin.ModelAdmin):
    list_display = [ 'name', 'dn' ]
    search_fields = [ 'name' ]

class LabelAdmin(admin.ModelAdmin):
    list_display = [ 'name', 'defaultColor' ]

class EventLogAdmin(admin.ModelAdmin):
    list_display = [ 'event', 'issuer', 'filename', 'comment' ]
    search_fields = [ 'event__id', 'issuer__name', 'filename', 'comment']

class LabellingAdmin(admin.ModelAdmin):
    list_display = [ 'event', 'label', 'creator' ]
    search_fields = [ 'event__id', 'label__name', 'creator__name' ]

class SlotAdmin(admin.ModelAdmin):
    list_display = [ 'event', 'name', 'value' ]

admin.site.register(Event, EventAdmin)
admin.site.register(EventLog, EventLogAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Group)
admin.site.register(Label, LabelAdmin)
admin.site.register(Labelling, LabellingAdmin)
admin.site.register(Slot, SlotAdmin)
