# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from django.core.management import call_command

class Migration(DataMigration):

    def forwards(self, orm):
        call_command("loaddata", "initial_searches.json")

    def backwards(self, orm):
        for search in orm.Search.objects.all():
            search.delete()

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
        u'gracedb.approval': {
            'Meta': {'object_name': 'Approval'},
            'approvedEvent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['gracedb.Event']"}),
            'approver': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'approvingCollaboration': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'gracedb.coincinspiralevent': {
            'Meta': {'ordering': "['-id']", 'object_name': 'CoincInspiralEvent', '_ormbases': [u'gracedb.Event']},
            'combined_far': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'end_time': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'end_time_ns': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            u'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['gracedb.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'false_alarm_rate': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'ifos': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '20'}),
            'mass': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'mchirp': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'minimum_duration': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'snr': ('django.db.models.fields.FloatField', [], {'null': 'True'})
        },
        u'gracedb.event': {
            'Meta': {'ordering': "['-id']", 'object_name': 'Event'},
            'analysisType': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'far': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'gpstime': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['gracedb.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instruments': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '20'}),
            'labels': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['gracedb.Label']", 'through': u"orm['gracedb.Labelling']", 'symmetrical': 'False'}),
            'likelihood': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'nevents': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'submitter': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'uid': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '20'})
        },
        u'gracedb.eventlog': {
            'Meta': {'ordering': "['-created', '-N']", 'unique_together': "(('event', 'N'),)", 'object_name': 'EventLog'},
            'N': ('django.db.models.fields.IntegerField', [], {}),
            'comment': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['gracedb.Event']"}),
            'file_version': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issuer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'gracedb.grbevent': {
            'Meta': {'ordering': "['-id']", 'object_name': 'GrbEvent', '_ormbases': [u'gracedb.Event']},
            'author_ivorn': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'author_shortname': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'coord_system': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'dec': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'error_radius': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            u'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['gracedb.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'how_description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'how_reference_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True'}),
            'ivorn': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'observatory_location_id': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'ra': ('django.db.models.fields.FloatField', [], {'null': 'True'})
        },
        u'gracedb.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        u'gracedb.label': {
            'Meta': {'object_name': 'Label'},
            'defaultColor': ('django.db.models.fields.CharField', [], {'default': "'black'", 'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'})
        },
        u'gracedb.labelling': {
            'Meta': {'object_name': 'Labelling'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['gracedb.Event']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['gracedb.Label']"})
        },
        u'gracedb.multiburstevent': {
            'Meta': {'ordering': "['-id']", 'object_name': 'MultiBurstEvent', '_ormbases': [u'gracedb.Event']},
            'amplitude': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'bandwidth': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'central_freq': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'confidence': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'duration': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            u'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['gracedb.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'false_alarm_rate': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'ifos': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '20'}),
            'ligo_angle': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'ligo_angle_sig': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'ligo_axis_dec': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'ligo_axis_ra': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'peak_time': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'peak_time_ns': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'snr': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'start_time': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'start_time_ns': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'})
        },
        u'gracedb.pipeline': {
            'Meta': {'object_name': 'Pipeline'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'gracedb.search': {
            'Meta': {'object_name': 'Search'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'gracedb.singleinspiral': {
            'Gamma0': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'Gamma1': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'Gamma2': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'Gamma3': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'Gamma4': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'Gamma5': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'Gamma6': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'Gamma7': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'Gamma8': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'Gamma9': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'Meta': {'object_name': 'SingleInspiral'},
            'alpha': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'alpha1': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'alpha2': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'alpha3': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'alpha4': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'alpha5': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'alpha6': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'amplitude': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'bank_chisq': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'bank_chisq_dof': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'beta': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'channel': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'chi': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'chisq': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'chisq_dof': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'coa_phase': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'cont_chisq': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'cont_chisq_dof': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'eff_distance': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'end_time': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'end_time_gmst': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'end_time_ns': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'eta': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['gracedb.Event']"}),
            'event_duration': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'f_final': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ifo': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True'}),
            'impulse_time': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'impulse_time_ns': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'kappa': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'mass1': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'mass2': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'mchirp': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'mtotal': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'psi0': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'psi3': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'rsqveto_duration': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'search': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True'}),
            'sigmasq': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'snr': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'tau0': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'tau2': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'tau3': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'tau4': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'tau5': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'template_duration': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'ttotal': ('django.db.models.fields.FloatField', [], {'null': 'True'})
        },
        u'gracedb.tag': {
            'Meta': {'object_name': 'Tag'},
            'displayName': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'eventlogs': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['gracedb.EventLog']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['gracedb']
    symmetrical = True
