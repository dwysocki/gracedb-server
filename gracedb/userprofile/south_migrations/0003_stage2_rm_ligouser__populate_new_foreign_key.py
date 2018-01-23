# -*- coding: utf-8 -*-
#import datetime
#from south.db import db
from south.v2 import DataMigration
#from django.db import models
import sys
import re

def get_auth_user_for_ligo_user_id(orm, userid):

    LigoUser = orm['gracedb.User']
    DjangoUser = orm['auth.User']

    service_cert_pattern = re.compile(r'.*CN=([^/]+)/[^/]+')

    try:
        ligo_user = LigoUser.objects.get(id=userid)
    except LigoUser.DoesNotExist:
        print("Can't find Ligo User {0}. (this should not happen)".format(userid))
        sys.exit(1)

    try:
        return DjangoUser.objects.get(username=ligo_user.unixid).id
    except DjangoUser.DoesNotExist:
        pass
    try:
        return DjangoUser.objects.get(username=ligo_user.principal)
        return DjangoUser.objects.get(username="{0}@LIGO.ORG".format(ligo_user.unixid))
    except DjangoUser.DoesNotExist:
        pass

    if ligo_user.unixid.lower() == 'none' or ligo_user.principal.lower() == 'none':
        # Some service user, likely.
        name = service_cert_pattern.match(ligo_user.dn).group(1)
        return DjangoUser.objects.get(username=name)

    print("Can't find Django user named '{0}'\nUnixid: {1}\nPrincipal: ({2})\nDN:({3})".
            format(ligo_user.name, ligo_user.unixid, ligo_user.principal, ligo_user.dn))
    sys.exit(1)

#def get_auth_user_for_ligo_user_id(orm, userid):
    #ligo_user = orm['gracedb.User'].objects.get(id=userid)
    #return orm['auth.User'].objects.get(username=ligo_user.unixid).id

def get_ligo_user_for_django_user_id(orm, django_id):
    django_user = orm['auth.User'].objects.get(id=django_id)
    return orm['gracedb.User'].objects.get(unixid=django_user.username)
    return 1

class Migration(DataMigration):

    def forwards(self, orm):
        ids = set()
        ids.update(orm['userprofile.Contact'].objects.values_list('user_id', flat=True).distinct())
        ids.update(orm['userprofile.Trigger'].objects.values_list('user_id', flat=True).distinct())

        for ligo_id in ids:
            django_id = get_auth_user_for_ligo_user_id(orm, ligo_id)
            orm['userprofile.Contact'].objects.filter(user=ligo_id).update(new_user=django_id)
            orm['userprofile.Trigger'].objects.filter(user=ligo_id).update(new_user=django_id)

    def backwards(self, orm):
        ids = set()

        ids.update(orm['userprofile.Contact'].objects.values_list('new_user_id', flat=True).distinct())
        ids.update(orm['userprofile.Trigger'].objects.values_list('new_user_id', flat=True).distinct())
        for django_id in ids:
            ligo_id = get_ligo_user_for_django_user_id(orm, django_id)
            orm['userprofile.Contact'].objects.filter(new_user=django_id).update(user=ligo_id)
            orm['userprofile.Trigger'].objects.filter(new_user=django_id).update(user=ligo_id)

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
            'new_user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.User']"})
        },
        'userprofile.trigger': {
            'Meta': {'object_name': 'Trigger'},
            'atypes': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.AnalysisType']", 'symmetrical': 'False', 'blank': 'True'}),
            'contacts': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.Contact']", 'symmetrical': 'False', 'blank': 'True'}),
            'farThresh': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'labels': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['gracedb.Label']", 'symmetrical': 'False', 'blank': 'True'}),
            'new_user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'}),
            'triggerType': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gracedb.User']"})
        }
    }

    complete_apps = ['userprofile']
    symmetrical = True
