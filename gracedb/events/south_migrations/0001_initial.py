# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'User'
        db.create_table('gracedb_user', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('principal', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('dn', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('unixid', self.gf('django.db.models.fields.CharField')(max_length=25)),
        ))
        db.send_create_signal('gracedb', ['User'])

        # Adding model 'Group'
        db.create_table('gracedb_group', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal('gracedb', ['Group'])

        # Adding M2M table for field managers on 'Group'
        db.create_table('gracedb_group_managers', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('group', models.ForeignKey(orm['gracedb.group'], null=False)),
            ('user', models.ForeignKey(orm['gracedb.user'], null=False))
        ))
        db.create_unique('gracedb_group_managers', ['group_id', 'user_id'])

        # Adding model 'Label'
        db.create_table('gracedb_label', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
            ('defaultColor', self.gf('django.db.models.fields.CharField')(default='black', max_length=20)),
        ))
        db.send_create_signal('gracedb', ['Label'])

        # Adding model 'Event'
        db.create_table('gracedb_event', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submitter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.Group'])),
            ('uid', self.gf('django.db.models.fields.CharField')(default='', max_length=20)),
            ('analysisType', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('instruments', self.gf('django.db.models.fields.CharField')(default='', max_length=20)),
            ('nevents', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('far', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('likelihood', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('gpstime', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
        ))
        db.send_create_signal('gracedb', ['Event'])

        # Adding model 'EventLog'
        db.create_table('gracedb_eventlog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.Event'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('issuer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.User'])),
            ('filename', self.gf('django.db.models.fields.CharField')(default='', max_length=100)),
            ('comment', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('gracedb', ['EventLog'])

        # Adding model 'Labelling'
        db.create_table('gracedb_labelling', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.Event'])),
            ('label', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.Label'])),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('gracedb', ['Labelling'])

        # Adding model 'Approval'
        db.create_table('gracedb_approval', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('approver', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('approvedEvent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.Event'])),
            ('approvingCollaboration', self.gf('django.db.models.fields.CharField')(max_length=1)),
        ))
        db.send_create_signal('gracedb', ['Approval'])

        # Adding model 'CoincInspiralEvent'
        db.create_table('gracedb_coincinspiralevent', (
            ('event_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['gracedb.Event'], unique=True, primary_key=True)),
            ('ifos', self.gf('django.db.models.fields.CharField')(default='', max_length=20)),
            ('end_time', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('end_time_ns', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('mass', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('mchirp', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('minimum_duration', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('snr', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('false_alarm_rate', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('combined_far', self.gf('django.db.models.fields.FloatField')(null=True)),
        ))
        db.send_create_signal('gracedb', ['CoincInspiralEvent'])

        # Adding model 'MultiBurstEvent'
        db.create_table('gracedb_multiburstevent', (
            ('event_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['gracedb.Event'], unique=True, primary_key=True)),
            ('ifos', self.gf('django.db.models.fields.CharField')(default='', max_length=20)),
            ('start_time', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('start_time_ns', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('duration', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('peak_time', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('peak_time_ns', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('central_freq', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('bandwidth', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('amplitude', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('snr', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('confidence', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('false_alarm_rate', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('ligo_axis_ra', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('ligo_axis_dec', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('ligo_angle', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('ligo_angle_sig', self.gf('django.db.models.fields.FloatField')(null=True)),
        ))
        db.send_create_signal('gracedb', ['MultiBurstEvent'])

        # Adding model 'Slot'
        db.create_table('gracedb_slot', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.Event'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('gracedb', ['Slot'])

        # Adding unique constraint on 'Slot', fields ['event', 'name']
        db.create_unique('gracedb_slot', ['event_id', 'name'])


    def backwards(self, orm):
        # Removing unique constraint on 'Slot', fields ['event', 'name']
        db.delete_unique('gracedb_slot', ['event_id', 'name'])

        # Deleting model 'User'
        db.delete_table('gracedb_user')

        # Deleting model 'Group'
        db.delete_table('gracedb_group')

        # Removing M2M table for field managers on 'Group'
        db.delete_table('gracedb_group_managers')

        # Deleting model 'Label'
        db.delete_table('gracedb_label')

        # Deleting model 'Event'
        db.delete_table('gracedb_event')

        # Deleting model 'EventLog'
        db.delete_table('gracedb_eventlog')

        # Deleting model 'Labelling'
        db.delete_table('gracedb_labelling')

        # Deleting model 'Approval'
        db.delete_table('gracedb_approval')

        # Deleting model 'CoincInspiralEvent'
        db.delete_table('gracedb_coincinspiralevent')

        # Deleting model 'MultiBurstEvent'
        db.delete_table('gracedb_multiburstevent')

        # Deleting model 'Slot'
        db.delete_table('gracedb_slot')


    models = {
        'gracedb.approval': {
            'Meta': {'object_name': 'Approval'},
            'approvedEvent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.Event']"}),
            'approver': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.User']"}),
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
            'submitter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.User']"}),
            'uid': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '20'})
        },
        'gracedb.eventlog': {
            'Meta': {'ordering': "['-created']", 'object_name': 'EventLog'},
            'comment': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.Event']"}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issuer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.User']"})
        },
        'gracedb.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'managers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['gracedb.User']", 'symmetrical': 'False'}),
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
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.User']"}),
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
        'gracedb.slot': {
            'Meta': {'unique_together': "(('event', 'name'),)", 'object_name': 'Slot'},
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '100'})
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