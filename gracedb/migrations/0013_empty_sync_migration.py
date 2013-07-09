# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


# Empty Migration.
#
# Synch up models that are messed up from previous, merged migrations.

class Migration(SchemaMigration):

    def forwards(self, orm):
        pass

    def backwards(self, orm):
        pass

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'gracedb.approval': {
            'Meta': {'object_name': 'Approval'},
            'approvedEvent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.Event']"}),
            'approver': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'approvingCollaboration': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'gracedb.coincinspiralevent': {
            'Meta': {'ordering': "['-id']", 'object_name': 'CoincInspiralEvent', '_ormbases': ['gracedb.Event']},
            'combined_far': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'end_time': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'end_time_ns': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['gracedb.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'false_alarm_rate': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'ifos': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '20'}),
            'mass': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'mchirp': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'minimum_duration': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'snr': ('django.db.models.fields.FloatField', [], {'null': 'True'})
        },
        'gracedb.event': {
            'Meta': {'ordering': "['-id']", 'object_name': 'Event'},
            'analysisType': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'far': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'gpstime': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instruments': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '20'}),
            'labels': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['gracedb.Label']", 'through': "orm['gracedb.Labelling']", 'symmetrical': 'False'}),
            'likelihood': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'nevents': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'submitter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'uid': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '20'})
        },
        'gracedb.eventlog': {
            'Meta': {'ordering': "['-created', '-N']", 'unique_together': "(('event', 'N'),)", 'object_name': 'EventLog'},
            'N': ('django.db.models.fields.IntegerField', [], {}),
            'comment': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.Event']"}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issuer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'gracedb.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'gracedb.label': {
            'Meta': {'object_name': 'Label'},
            'defaultColor': ('django.db.models.fields.CharField', [], {'default': "'black'", 'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'})
        },
        'gracedb.labelling': {
            'Meta': {'object_name': 'Labelling'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.Label']"})
        },
        'gracedb.multiburstevent': {
            'Meta': {'ordering': "['-id']", 'object_name': 'MultiBurstEvent', '_ormbases': ['gracedb.Event']},
            'amplitude': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'bandwidth': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'central_freq': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'confidence': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'duration': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['gracedb.Event']", 'unique': 'True', 'primary_key': 'True'}),
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
        'gracedb.singleinspiral': {
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
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.Event']"}),
            'event_duration': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'f_final': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
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
        'gracedb.tag': {
            'Meta': {'object_name': 'Tag'},
            'displayName': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'eventlogs': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['gracedb.EventLog']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['gracedb']
