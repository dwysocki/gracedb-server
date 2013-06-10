# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):
    needed_by = (("gracedb","0008_auto__del_user"),)

    def forwards(self, orm):
        db.delete_column('userprofile_contact', 'user_id')
        db.delete_column('userprofile_trigger', 'user_id')

        db.rename_column('userprofile_contact', 'new_user_id', 'user_id')
        db.rename_column('userprofile_trigger', 'new_user_id', 'user_id')

    def backwards(self, orm):
        db.rename_column('userprofile_contact', 'user_id', 'new_user_id')
        db.rename_column('userprofile_trigger', 'user_id', 'new_user_id')

        db.add_column('userprofile_contact', 'trigger',
            self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.User'], null=False, default=1),
            keep_default=False)
        db.add_column('userprofile_trigger', 'trigger',
            self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gracedb.User'], null=False, default=1),
            keep_default=False)

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
