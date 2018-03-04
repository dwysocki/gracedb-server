# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'AnalysisType'
        db.create_table('userprofile_analysistype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
            ('display', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
        ))
        db.send_create_signal('userprofile', ['AnalysisType'])

        # Adding model 'Contact'
        db.create_table('userprofile_contact', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.User'])),
            ('desc', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
        ))
        db.send_create_signal('userprofile', ['Contact'])

        # Adding model 'Trigger'
        db.create_table('userprofile_trigger', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.User'])),
            ('triggerType', self.gf('django.db.models.fields.CharField')(max_length=20, blank=True)),
            ('farThresh', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
        ))
        db.send_create_signal('userprofile', ['Trigger'])

        # Adding M2M table for field labels on 'Trigger'
        db.create_table('userprofile_trigger_labels', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('trigger', models.ForeignKey(orm['userprofile.trigger'], null=False)),
            ('label', models.ForeignKey(orm['gracedb.label'], null=False))
        ))
        db.create_unique('userprofile_trigger_labels', ['trigger_id', 'label_id'])

        # Adding M2M table for field atypes on 'Trigger'
        db.create_table('userprofile_trigger_atypes', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('trigger', models.ForeignKey(orm['userprofile.trigger'], null=False)),
            ('analysistype', models.ForeignKey(orm['userprofile.analysistype'], null=False))
        ))
        db.create_unique('userprofile_trigger_atypes', ['trigger_id', 'analysistype_id'])

        # Adding M2M table for field contacts on 'Trigger'
        db.create_table('userprofile_trigger_contacts', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('trigger', models.ForeignKey(orm['userprofile.trigger'], null=False)),
            ('contact', models.ForeignKey(orm['userprofile.contact'], null=False))
        ))
        db.create_unique('userprofile_trigger_contacts', ['trigger_id', 'contact_id'])


    def backwards(self, orm):
        # Deleting model 'AnalysisType'
        db.delete_table('userprofile_analysistype')

        # Deleting model 'Contact'
        db.delete_table('userprofile_contact')

        # Deleting model 'Trigger'
        db.delete_table('userprofile_trigger')

        # Removing M2M table for field labels on 'Trigger'
        db.delete_table('userprofile_trigger_labels')

        # Removing M2M table for field atypes on 'Trigger'
        db.delete_table('userprofile_trigger_atypes')

        # Removing M2M table for field contacts on 'Trigger'
        db.delete_table('userprofile_trigger_contacts')


    models = {
        'gracedb.label': {
            'Meta': {'object_name': 'Label'},
            'defaultColor': ('django.db.models.fields.CharField', [], {'default': "'black'", 'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'})
        },
        'gracedb.user': {
            'Meta': {'ordering': "['name']", 'object_name': 'User'},
            'dn': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'principal': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'unixid': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'userprofile.analysistype': {
            'Meta': {'object_name': 'AnalysisType'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'display': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'userprofile.contact': {
            'Meta': {'object_name': 'Contact'},
            'desc': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.User']"})
        },
        'userprofile.trigger': {
            'Meta': {'object_name': 'Trigger'},
            'atypes': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.AnalysisType']", 'symmetrical': 'False', 'blank': 'True'}),
            'contacts': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.Contact']", 'symmetrical': 'False', 'blank': 'True'}),
            'farThresh': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'labels': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['gracedb.Label']", 'symmetrical': 'False', 'blank': 'True'}),
            'triggerType': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.User']"})
        }
    }

    complete_apps = ['userprofile']