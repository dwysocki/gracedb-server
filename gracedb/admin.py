
from models import Event, EventLog, EMBBEventLog, Group
from models import Label, Labelling, Tag
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

class LabelAdmin(admin.ModelAdmin):
    list_display = [ 'name', 'defaultColor' ]

class EventLogAdmin(admin.ModelAdmin):
    list_display = [ 'event', 'issuer', 'filename', 'comment' ]
    search_fields = [ 'event__id', 'issuer__name', 'filename', 'comment']

#class EMBBEventLogAdmin(admin.ModelAdmin):
#    list_display = [ 'event' ]
#    search_fields = [ 'event__id']

class LabellingAdmin(admin.ModelAdmin):
    list_display = [ 'event', 'label', 'creator' ]
    search_fields = [ 'event__id', 'label__name', 'creator__name' ]

class TagAdmin(admin.ModelAdmin):
    list_display = [ 'name', 'displayName' ]
    exclude = [ 'eventlogs' ]

admin.site.register(Event, EventAdmin)
admin.site.register(EventLog, EventLogAdmin)
#admin.site.register(EMBBEventLog, EMBBEventLogAdmin)
admin.site.register(Group)
admin.site.register(Label, LabelAdmin)
admin.site.register(Labelling, LabellingAdmin)
admin.site.register(Tag, TagAdmin)
