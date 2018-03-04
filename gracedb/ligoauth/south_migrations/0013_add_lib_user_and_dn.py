# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

users = [
        {
            'username' : 'LIB',
            'first_name' : '',
            'last_name' : 'LIB at CIT',
            'email' : 'salvatore.vitale@ligo.mit.edu',
            'dns' : [
                "/DC=org/DC=ligo/O=LIGO/OU=Services/CN=LIB/ldas-pcdev1.ligo-la.caltech.edu",
            ]
        },
]

class Migration(DataMigration):

    def forwards(self, orm):
        LocalUser = orm['ligoauth.LocalUser']
        X509Cert = orm['ligoauth.X509Cert']

        # Local Users
        for entry in users:
            user, created = LocalUser.objects.get_or_create(username=entry['username'])
            if created:
                user.first_name = entry['first_name']
                user.last_name = entry['last_name']
                user.email = entry['email']
                user.is_active = True
                user.is_staff = False
                user.is_superuser = False
                user.save()
            current_dns = set([cert.subject for cert in user.x509cert_set.all()])
            new_dns = set(entry['dns'])

            missing_dns = new_dns - current_dns
            redundant_dns = current_dns - new_dns

            for dn in missing_dns:
                cert, created = X509Cert.objects.get_or_create(subject=dn)
                if created:
                    cert.save()
                cert.users.add(user)

            for dn in redundant_dns:
                cert = X509Cert.objects.get(subject=dn)
                cert.users.remove(user)

    def backwards(self, orm):
        LocalUser = orm['ligoauth.LocalUser']
        X509Cert = orm['ligoauth.X509Cert']
        for entry in users:
            for dn in entry['dns']:
                cert = X509Cert.objects.get(subject=dn)
                cert.delete()

            user = LocalUser.objects.get(username=entry['username'])
            user.delete()

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
        u'ligoauth.alternateemail': {
            'Meta': {'object_name': 'AlternateEmail'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '254'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'ligoauth.ligoldapuser': {
            'Meta': {'object_name': 'LigoLdapUser', '_ormbases': [u'auth.User']},
            'ldap_dn': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            u'user_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'ligoauth.localuser': {
            'Meta': {'object_name': 'LocalUser', '_ormbases': [u'auth.User']},
            u'user_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'ligoauth.x509cert': {
            'Meta': {'object_name': 'X509Cert'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False'})
        }
    }

    complete_apps = ['ligoauth']
    symmetrical = True
