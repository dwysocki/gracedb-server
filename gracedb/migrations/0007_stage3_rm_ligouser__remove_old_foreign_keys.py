# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Remove old fields
        db.delete_column('gracedb_event', 'submitter_id')
        db.delete_column('gracedb_labelling', 'creator_id')
        db.delete_column('gracedb_approval', 'approver_id')
        db.delete_column('gracedb_eventlog', 'issuer_id')

        #
        # Move new_* to *  (and make them non-nullable)
        #
        db.rename_column('gracedb_event', 'new_submitter_id', 'submitter_id')
        db.rename_column('gracedb_labelling', 'new_creator_id', 'creator_id')
        db.rename_column('gracedb_approval', 'new_approver_id', 'approver_id')
        db.rename_column('gracedb_eventlog', 'new_issuer_id', 'issuer_id')

        db.alter_column('gracedb_event', 'submitter_id',
            self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'],null=False))
        db.alter_column('gracedb_labelling', 'creator_id',
            self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'],null=False))
        db.alter_column('gracedb_approval', 'approver_id',
            self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'],null=False))
        db.alter_column('gracedb_eventlog', 'issuer_id',
            self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'],null=False))

    def backwards(self, orm):
        # Move * to new_*
        db.rename_column('gracedb_event', 'submitter_id', 'new_submitter_id')
        db.rename_column('gracedb_labelling', 'creator_id', 'new_creator_id')
        db.rename_column('gracedb_approval', 'approver_id', 'new_approver_id')
        db.rename_column('gracedb_eventlog', 'issuer_id', 'new_issuer_id')

        # Replace old fields
        db.add_column('gracedb_event', 'submitter',
            self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.User'], null=False, default=1),
            keep_default=False)
        db.add_column('gracedb_labelling', 'creator',
            self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.User'], null=False, default=1),
            keep_default=False)
        db.add_column('gracedb_approval', 'approver',
            self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.User'], null=False, default=1),
            keep_default=False)
        db.add_column('gracedb_eventlog', 'issuer',
            self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.User'], null=False, default=1),
            keep_default=False)

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
            'Meta': {'ordering': "['-created']", 'object_name': 'EventLog'},
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
        'gracedb.tag': {
            'Meta': {'object_name': 'Tag'},
            'displayName': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'eventlogs': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['gracedb.EventLog']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'gracedb.user': {
            'Meta': {'ordering': "['name']", 'object_name': 'User'},
            'dn': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'principal': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'unixid': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        }
    }

    complete_apps = ['gracedb']
