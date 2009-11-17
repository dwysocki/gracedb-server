#from gracedb.gracedb.models import Analysis, Group, User
from models import Event, EventLog, User, Group
from models import Label, Labelling
from django.contrib import admin

#class AnalysisAdmin(admin.ModelAdmin):
#    list_display = ['uid', 'group', 'analysisType', 'description', 'owner']

#admin.site.register(Analysis, AnalysisAdmin)
admin.site.register(Event)
admin.site.register(EventLog)
admin.site.register(User)
admin.site.register(Group)
admin.site.register(Label)
admin.site.register(Labelling)

