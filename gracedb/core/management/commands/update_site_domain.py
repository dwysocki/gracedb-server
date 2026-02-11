# -*- coding: utf-8 -*-
"""
Django management command to update the Site domain to match DJANGO_PRIMARY_FQDN.

This is needed because the sites migration (0002_update_site.py) reads
DJANGO_PRIMARY_FQDN at migration time and stores it in the database.
If the environment variable changes between container starts, the database
will have stale data.

Usage:
    python manage.py update_site_domain
    python manage.py update_site_domain --verbosity 2
"""

import os
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.conf import settings


class Command(BaseCommand):
    help = (
        "Update the Site domain to match DJANGO_PRIMARY_FQDN. "
        "This ensures the database stays in sync with the environment variable."
    )

    def handle(self, *args, **options):
        verbosity = options.get('verbosity', 1)

        # Safety check: only run in local development mode
        if os.environ.get('LOCAL_BUILD') != 'true':
            self.stdout.write(
                self.style.WARNING(
                    '⚠ Skipping site domain update: LOCAL_BUILD is not set to "true"'
                )
            )
            if verbosity >= 2:
                self.stdout.write(
                    '  This command is only intended for local development '
                    'where DJANGO_PRIMARY_FQDN may change between container starts.'
                )
            return

        # Get expected domain from environment (same logic as migration)
        import socket
        default_domain = socket.gethostname() + '.ligo.org'
        expected_domain = os.environ.get('DJANGO_PRIMARY_FQDN', default_domain)

        # Get expected name (same logic as migration)
        expected_name = expected_domain.partition('.')[2] or expected_domain

        try:
            # Get the current site
            site = Site.objects.get(id=settings.SITE_ID)

            # Check if update is needed
            if site.domain == expected_domain and site.name == expected_name:
                if verbosity >= 1:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Site domain is already correct: {site.domain}'
                        )
                    )
                return

            # Update the site
            old_domain = site.domain
            old_name = site.name

            site.domain = expected_domain
            site.name = expected_name
            site.save()

            if verbosity >= 1:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Updated site domain: {old_domain} → {expected_domain}'
                    )
                )
                if verbosity >= 2:
                    self.stdout.write(f'  Site name: {old_name} → {expected_name}')
                    self.stdout.write(f'  Site ID: {site.id}')
                    self.stdout.write(f'  DJANGO_PRIMARY_FQDN: {os.environ.get("DJANGO_PRIMARY_FQDN", "not set")}')

        except Site.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f'✗ Site with ID {settings.SITE_ID} does not exist. '
                    f'Run migrations first.'
                )
            )
            raise
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error updating site: {e}')
            )
            raise
