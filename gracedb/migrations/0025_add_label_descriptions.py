# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

# dict of label names and descriptions
# descriptions taken from templates/gracedb/event_detail_script.js
label_dict = {
    "ADVNO": "EM advocate says event is not okay.",
    "ADVOK": "EM advocate says event is okay.",
    "ADVREQ": "EM advocate signoff requested.",
    "cWB_s": "cWB_s",
    "cWB_r": "cWB_r",
    "DQV": "Data quality veto.",
    "EM_COINC": "Signifies that a coincidence was found between gravitational-wave candidates and External triggers.",
    "EM_READY": "Has been processed by GDB Processor. Skymaps have been produced.",
    "EM_Selected": "GraceID automatically chosen as the most promising candidate out of a set of entries thought to correspond to the same physical event.",
    "EM_SENT": "Has been sent to MOU partners.",
    "EM_Superseded": "GraceID automatically passed over because another entry was thought to be more promising and to correspond to the same physical event.",
    "EM_Throttled": "GraceID is ignored by automatic processing because the corresponding pipeline submitted too many events too quickly.",
    "GRB_OFFLINE": "Indicates that offline triggered GRB searches found something coincident with this event.",
    "GRB_ONLINE": "Indicates that online triggered GRB searches found something coincident with this event.",
    "H1NO": "H1 operator says event is not okay.",
    "H1OK": "H1 operator says event is okay.",
    "H1OPS": "H1 operator signoff requested.",
    "INJ": "Injection occured near this time.",
    "L1NO": "L1 operator says event is not okay.",
    "L1OK": "L1 operator says event is okay.",
    "L1OPS": "L1 operator signoff requested.",
    "LUMIN_GO": "LUMIN Go",
    "LUMIN_NO": "LUMIN No",
    "PE_READY": "Parameter estimation results are available",
    "SWIFT_GO": "Send notification to SWIFT telescope.",
    "SWIFT_NO": "Do not send notification to SWIFT telescope.",
    "V1NO": "V1 operator says event is not okay.",
    "V1OK": "V1 operator says event is okay.",
    "V1OPS": "V1 operator signoff requested.",
}

EMPTY_DESC = ""

def add_descriptions(apps, schema_editor):
    Label = apps.get_model('gracedb', 'Label')

    # add description
    for l in Label.objects.all():
        l.description = label_dict[l.name]
        l.save()

def remove_descriptions(apps, schema_editor):
    Label = apps.get_model('gracedb', 'Label')

    for l in Label.objects.all():
        l.description = EMPTY_DESC
        l.save()

class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0024_label_description')
    ]

    operations = [
        migrations.RunPython(add_descriptions, remove_descriptions)
    ]
