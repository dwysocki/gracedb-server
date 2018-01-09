# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

import ldap


def update_from_ldap(LigoLdapUser, X509Cert):
    # Copied here from ligoauth/management/commands/refresh_from_ldap
    # because it might not be there or be crazy different in the future.
    # Of course, it might still be broken in the future anyway, but hey.
    baseDN = "ou=people,dc=ligo,dc=org"
    searchScope = ldap.SCOPE_SUBTREE
    searchFilter = "(employeeNumber=*)"
    retrieveAttributes = ["krbPrincipalName",
                          "gridX509subject",
                          "givenName",
                          "sn",
                          "mail",
                          "isMemberOf"]

    l = ldap.open("ldap.ligo.org")
    l.protocol_version = ldap.VERSION3
    ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
    while 1:
        result_type, result_data = l.result(ldap_result_id, 0)
        if (result_data == []):
            break
        else:
            if result_type == ldap.RES_SEARCH_ENTRY:
                for (ldap_dn, ldap_result) in result_data:

                    first_name = unicode(ldap_result['givenName'][0], 'utf-8')
                    last_name = unicode(ldap_result['sn'][0], 'utf-8')
                    email = ldap_result['mail'][0]
                    new_dns = set(ldap_result.get('gridX509subject',[]))
                    is_active = "Communities:LVC:LVCGroupMembers" \
                                in ldap_result.get('isMemberOf',[])
                    principal = ldap_result['krbPrincipalName'][0]

                    # Update/Create LigoLdapUser entry
                    user, created = LigoLdapUser.objects.get_or_create(ldap_dn=ldap_dn)

                    changed = created \
                            or (user.first_name != first_name) \
                            or (user.last_name != last_name) \
                            or (user.email != email) \
                            or (user.username != principal) \
                            or (user.is_active != is_active)

                    if changed:
                        user.first_name = first_name
                        user.last_name = last_name
                        user.email = email
                        user.username = principal
                        user.is_active = is_active
                        # revoke staff/superuser if not active.
                        user.is_staff = user.is_staff and is_active
                        user.is_superuser = user.is_superuser and is_active
                        user.save()

                    # update X509 certs for user
                    current_dns = set([ cert.subject for cert in user.x509cert_set.all() ])

                    if current_dns != new_dns:
                        for dn in current_dns - new_dns:
                            X509Cert.objects.get(subject=dn).delete()
                        for dn in new_dns - current_dns:
                            cert, created = X509Cert.objects.get_or_create(subject=dn)
                            if created:
                                cert.save()
                            cert.users.add(user)

class Migration(DataMigration):

    needed_by = (
                ("gracedb", "0005_stage1_rm_ligouser__add_new_foreign_keys"),
                ("userprofile", "0002_stage1_rm_ligouser__add_new_foreign_key"),
            )

    def forwards(self, orm):
        LigoLdapUser = orm['ligoauth.LigoLdapUser']
        X509Cert = orm['ligoauth.X509Cert']
        update_from_ldap(LigoLdapUser, X509Cert)

    def backwards(self, orm):
        LigoLdapUser = orm['ligoauth.LigoLdapUser']
        for user in LigoLdapUser.objects.all():
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
