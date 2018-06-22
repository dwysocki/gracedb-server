# mixins for class-based views
from django import forms
from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.views.generic.base import ContextMixin
from guardian.models import GroupObjectPermission

from .forms import SignoffForm

import logging
logger = logging.getLogger(__name__)


class OperatorSignoffMixin(ContextMixin):

    def get_context_data(self, **kwargs):
        context = super(OperatorSignoffMixin, self).get_context_data(**kwargs)

        # Check if user is in auth group for which signoff is authorized
        signoff_group = self.request.user.groups.filter(
            name__icontains='control_room').first()

        # Update context with signoff_authorized bool
        context['operator_signoff_authorized'] = signoff_group is not None

        # If not, just return
        if not signoff_group:
            return context

        # Get signoff instrument
        signoff_instrument = signoff_group.name[:2].upper()

        # Determine if a signoff object already exists
        signoff = self.object.signoff_set.filter(instrument=signoff_instrument,
            signoff_type='OP').first()

        # Check if label requesting signoff exists
        signoff_request_label_name = signoff_instrument + 'OPS'
        signoff_request_label_exists = self.object.labelling_set.filter(
            label__name=signoff_request_label_name).exists()

        # Should form object be shown to authorized users?
        signoff_active = signoff_request_label_exists or signoff is not None
        context['operator_signoff_active'] = signoff_active
        if not signoff_active:
            return context

        # Add more to context
        context['operator_signoff_instrument'] = signoff_instrument
        if signoff:
            # Populate form with instance
            form = SignoffForm(initial={'action': 'UP'}, instance=signoff)
            context['operator_signoff_exists'] = True
        else:
            # Default create form
            form = SignoffForm(initial={'signoff_type': 'OP',
                'instrument': signoff_instrument, 'action': 'CR'})
            context['operator_signoff_exists'] = False

            # Hide delete checkbox - doesn't apply to creation
            form.fields['delete'].widget=forms.HiddenInput()
        context['operator_signoff_form'] = form

        return context


class AdvocateSignoffMixin(ContextMixin):

    def get_context_data(self, **kwargs):
        context = super(AdvocateSignoffMixin, self).get_context_data(**kwargs)

        # Check if user is in auth group for which signoff is authorized
        signoff_group = self.request.user.groups.filter(
            name=settings.EM_ADVOCATE_GROUP)

        # Update context with signoff_authorized bool
        context['advocate_signoff_authorized'] = signoff_group is not None

        # If not, just return
        if not signoff_group:
            return context

        # Get signoff instrument
        signoff_instrument = ""

        # Determine if a signoff object already exists
        signoff = self.object.signoff_set.filter(instrument=signoff_instrument,
            signoff_type='ADV').first()

        # Check if label requesting signoff exists
        signoff_request_label_name = 'ADVREQ'
        signoff_request_label_exists = self.object.labelling_set.filter(
            label__name=signoff_request_label_name).exists()

        # Should form object be shown to authorized users?
        signoff_active = signoff_request_label_exists or signoff is not None
        context['advocate_signoff_active'] = signoff_active
        if not signoff_active:
            return context

        # Add more to context
        context['advocate_signoff_instrument'] = signoff_instrument
        if signoff:
            # Populate form with instance
            form = SignoffForm(initial={'action': 'UP'}, instance=signoff)
            context['advocate_signoff_exists'] = True
        else:
            # Default create form
            form = SignoffForm(initial={'signoff_type': 'ADV',
                'instrument': signoff_instrument, 'action': 'CR'})
            context['advocate_signoff_exists'] = False

            # Hide delete checkbox - doesn't apply to creation
            form.fields['delete'].widget=forms.HiddenInput()
        context['advocate_signoff_form'] = form

        return context


class LvemPermissionMixin(ContextMixin):

    def get_context_data(self, **kwargs):

        # Get base context
        context = super(LvemPermissionMixin, self).get_context_data(**kwargs)

        # Get LV-EM observers group
        lvem_obs_group = AuthGroup.objects.get(
            name=settings.LVEM_OBSERVERS_GROUP)

        # Get permission objects
        model_name = self.model.__name__.lower()
        ctype = ContentType.objects.get(app_label=self.model._meta.app_label,
            model=model_name)
        p_view = Permission.objects.get(codename='view_{0}'.format(model_name))
        p_change = Permission.objects.get(codename='change_{0}'.format(
            model_name))

        # Determine
        lvem_obs_can_view = GroupObjectPermission.objects.filter(
            content_type=ctype, object_pk=self.object.pk, group=lvem_obs_group,
            permission=p_view).exists()
        lvem_obs_can_change = GroupObjectPermission.objects.filter(
            content_type=ctype, object_pk=self.object.pk, group=lvem_obs_group,
            permission=p_change).exists()

        # Determine user permissions for exposing to or protecting from
        # the LV-EM observers group
        if (lvem_obs_can_view and lvem_obs_can_change and
            self.request.user.has_perm(
            'guardian.delete_groupobjectpermission')):
            perms = False, True
        elif (not lvem_obs_can_view and not lvem_obs_can_change and
              self.request.user.has_perm(
              'guardian.add_groupobjectpermission')):
            perms = True, False
        else:
            perms = False, False

        # Update context
        context['can_expose_to_lvem'] = perms[0]
        context['can_protect_from_lvem'] = perms[1]
        context['lvem_group_name'] = settings.LVEM_OBSERVERS_GROUP

        return context
