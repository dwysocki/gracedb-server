# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

ANALYSIS_TYPE_TO_PIPELINE = {
    'RD' : 'Ringdown',
    'OM' : 'Omega',
    'Q'  : 'Q',
    'X'  : 'X',
    'MBTA' : 'MBTAOnline',
    'HWINJ' : 'HardwareInjection',
}

class Migration(DataMigration):

    def forwards(self, orm):
        # fetch some pipelines
        gstlal = orm['gracedb.Pipeline'].objects.get(name='gstlal')
        Fermi  = orm['gracedb.Pipeline'].objects.get(name='Fermi')
        Swift  = orm['gracedb.Pipeline'].objects.get(name='Swift')
        CWB    = orm['gracedb.Pipeline'].objects.get(name='CWB')
        CWB2G  = orm['gracedb.Pipeline'].objects.get(name='CWB2G')

        for trigger in orm.Trigger.objects.all():
            for atype in trigger.atypes.all():
                if atype.code in ['LM','HM']:
                    trigger.pipelines.add(gstlal)
                elif atype.code=='GRB':
                    trigger.pipelines.add(Fermi)
                    trigger.pipelines.add(Swift)
                elif atype.code=='CWB':
                    trigger.pipelines.add(CWB)
                    trigger.pipelines.add(CWB2G)
                elif atype.code in ANALYSIS_TYPE_TO_PIPELINE.keys():
                    p = orm['gracedb.Pipeline'].objects.get(name=ANALYSIS_TYPE_TO_PIPELINE[atype.code])
                    trigger.pipelines.add(p)
                else:
                    pass

    def backwards(self, orm):
        for trigger in orm.Trigger.objects.all():
            trigger.pipelines.clear()


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'gracedb.label': {
            'Meta': {'object_name': 'Label'},
            'defaultColor': ('django.db.models.fields.CharField', [], {'default': "'black'", 'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'})
        },
        u'gracedb.pipeline': {
            'Meta': {'object_name': 'Pipeline'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'userprofile.analysistype': {
            'Meta': {'object_name': 'AnalysisType'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'display': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'userprofile.contact': {
            'Meta': {'object_name': 'Contact'},
            'desc': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'userprofile.trigger': {
            'Meta': {'object_name': 'Trigger'},
            'atypes': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['userprofile.AnalysisType']", 'symmetrical': 'False', 'blank': 'True'}),
            'contacts': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['userprofile.Contact']", 'symmetrical': 'False', 'blank': 'True'}),
            'farThresh': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'labels': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['gracedb.Label']", 'symmetrical': 'False', 'blank': 'True'}),
            'pipelines': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['gracedb.Pipeline']", 'symmetrical': 'False', 'blank': 'True'}),
            'triggerType': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['userprofile']
    symmetrical = True
