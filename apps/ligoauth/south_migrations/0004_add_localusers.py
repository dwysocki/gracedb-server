# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

users = [
        {
            'username' : 'MbtaAlert',
            'first_name' : '',
            'last_name' : 'MBTA Alert',
            'email' : 'mours@lapp.in2p3.fr',
            'dns' : [
                "/C=IT/O=INFN/OU=Service/L=EGO/CN=MbtaAlert/lscgw.virgo.infn.it",
                "/C=IT/O=INFN/OU=Service/L=EGO/CN=MbtaAlert/olnode04.virgo.infn.it",
                "/C=IT/O=INFN/OU=Service/L=EGO/CN=MbtaAlert/olnode33.virgo.infn.it",
            ]
        },
        {
            'username' : 'detchar',
            'first_name' : '',
            'last_name' : 'Detchar',
            'email' : 'pankow@gravity.phys.uwm.edu',
            'dns' : [
                "/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-grid.ligo-la.caltech.edu",
                "/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-grid.ligo-wa.caltech.edu",
                "/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-grid.ligo.caltech.edu",
                "/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev1.ligo-la.caltech.edu",
                "/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev1.ligo-wa.caltech.edu",
                "/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev1.ligo.caltech.edu",
                "/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev2.ligo-la.caltech.edu",
                "/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev2.ligo-wa.caltech.edu",
                "/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev2.ligo.caltech.edu",
                "/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev3.ligo.caltech.edu",
                "/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev4.ligo.caltech.edu",
            ]
        },
        {
            'username' : 'excesspower-processor',
            'first_name' : '',
            'last_name' : 'Excess Power Processor',
            'email' : 'pankow@gravity.phys.uwm.edu',
            'dns' : [
                '/DC=org/DC=doegrids/OU=Services/CN=excesspower-processor/marlin.phys.uwm.edu',
            ]
        },
        {
            'username' : 'gdb-processor',
            'first_name' : '',
            'last_name' : 'GDB Processor',
            'email' : 'gdb_processor@gravity.phys.uwm.edu',
            'dns' : [
                "/DC=org/DC=doegrids/OU=Services/CN=gdb-processor/marlin.phys.uwm.edu",
            ]
        },
        {
            'username' : 'gis',
            'first_name' : '',
            'last_name' : 'GIS',
            'email' : 'xavier.amador@ligo.org',
            'dns' : [
                "/DC=org/DC=doegrids/OU=Services/CN=gis/lscgis.phys.uwm.edu",
            ]
        },
        {
            'username' : 'lumin',
            'first_name' : '',
            'last_name' : 'LUMIN',
            'email' : 'bmoe@gravity.phys.uwm.edu',
            'dns' : [
                "/DC=org/DC=doegrids/OU=Services/CN=luminrobot/ldas-pcdev1.ligo.caltech.edu",
            ]
        },
        {
            'username' : 'omega',
            'first_name' : '',
            'last_name' : 'Omega Analysis',
            'email' : '',
            'dns' : [
                "/DC=org/DC=doegrids/OU=Services/CN=omegarobot/node499.ldas-cit.ligo.caltech.edu",
            ]
        },
        {
            'username' : 'waveburst',
            'first_name' : '',
            'last_name' : 'Cwb Analysis',
            'email' : 'bmoe@gravity.phys.uwm.edu',
            'dns' : [
                "/DC=org/DC=doegrids/OU=Services/CN=waveburst/ldas-pcdev1.ligo.caltech.edu",
            ]
        },
        {
            'username' : 'gstlalcbc',
            'first_name' : '',
            'last_name' : 'GstLal CBC',
            'email' : 'chad.r.hanna@gmail.com',
            'dns' : [
                "/DC=org/DC=ligo/O=LIGO/OU=Services/CN=gstlalcbc/ldas-pcdev1.ligo.caltech.edu",
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
        for user in LocalUser.objects.all():
            user.delete()

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
        'ligoauth.ligoldapuser': {
            'Meta': {'object_name': 'LigoLdapUser', '_ormbases': ['auth.User']},
            'ldap_dn': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'user_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        },
        'ligoauth.localuser': {
            'Meta': {'object_name': 'LocalUser', '_ormbases': ['auth.User']},
            'user_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        },
        'ligoauth.x509cert': {
            'Meta': {'object_name': 'X509Cert'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'})
        }
    }

    complete_apps = ['ligoauth']
    symmetrical = True
