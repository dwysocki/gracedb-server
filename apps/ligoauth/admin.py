
from django.contrib import admin
from .models import LocalUser, LigoLdapUser, X509Cert

class LigoLdapUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'first_name', 'last_name']
    search_fields = ['username']

class X509CertAdmin(admin.ModelAdmin):
    list_display = ['subject']
    search_fields = ['subject']

admin.site.register(LocalUser)
admin.site.register(LigoLdapUser, LigoLdapUserAdmin)
admin.site.register(X509Cert, X509CertAdmin)
