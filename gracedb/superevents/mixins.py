# mixins for class-based views
import pytz

from django import forms
from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.views.generic.base import ContextMixin
from django.views.generic.detail import SingleObjectMixin

from guardian.shortcuts import get_objects_for_user

from core.time_utils import gpsToUtc
from .forms import SignoffForm
from .models import Signoff

import logging
logger = logging.getLogger(__name__)


class PermissionsFilterMixin(SingleObjectMixin):
    """
    Filters queryset to include only objects for which the user has
    the required permissions.  The view should return a 404 if the
    requested object is not found within the filtered queryset.

    Set accept_global_perms to False if you don't want global (table-level)
    permissions to be accepted in place of object permissions.
    """
    filter_permissions = []
    accept_global_perms = True

    def filter_queryset(self, queryset):
        """
        Filters queryset to include only objects for which the user has
        the required permissions.
        """
        qs = get_objects_for_user(self.request.user, self.filter_permissions,
            queryset, **{'accept_global_perms': self.accept_global_perms})

        return qs

    def get_queryset(self):
        qs = super(PermissionsFilterMixin, self).get_queryset()

        # Filter the queryset for user and return
        return self.filter_queryset(qs)


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
            signoff_type=Signoff.SIGNOFF_TYPE_OPERATOR).first()

        # Check if label requesting signoff exists
        signoff_request_label_name = signoff_instrument + 'OPS'
        signoff_request_label_exists = self.object.labelling_set.filter(
            label__name=signoff_request_label_name).exists()

        # Should form object be shown to authorized users?
        signoff_active = signoff_request_label_exists or signoff is not None
        context['operator_signoff_active'] = signoff_active
        if not signoff_active:
            return context

        # Get object time in operator timezone
        obj_time_for_operator = gpsToUtc(self.object.gpstime).astimezone(
            pytz.timezone(Signoff.instrument_time_zones[signoff_instrument]))

        # Add more to context
        context['object_gpstime_in_operator_tz'] = \
            obj_time_for_operator.strftime(settings.GRACE_STRFTIME_FORMAT)
        context['operator_signoff_instrument'] = signoff_instrument
        context['operator_signoff_type'] = Signoff.SIGNOFF_TYPE_OPERATOR
        if signoff:
            # Populate form with instance
            form = SignoffForm(instance=signoff)
            context['operator_signoff_exists'] = True
        else:
            # Default create form
            form = SignoffForm(initial={
                'signoff_type': Signoff.SIGNOFF_TYPE_OPERATOR,
                'instrument': signoff_instrument,
            })
            context['operator_signoff_exists'] = False

        context['operator_signoff_form'] = form

        return context


class AdvocateSignoffMixin(ContextMixin):

    def get_context_data(self, **kwargs):
        context = super(AdvocateSignoffMixin, self).get_context_data(**kwargs)

        # Check if user is in auth group for which signoff is authorized
        signoff_group = self.request.user.groups.filter(
            name=settings.EM_ADVOCATE_GROUP).first()

        # Update context with signoff_authorized bool
        context['advocate_signoff_authorized'] = signoff_group is not None

        # If not, just return
        if not signoff_group:
            return context

        # Get signoff instrument
        signoff_instrument = ""

        # Determine if a signoff object already exists
        signoff = self.object.signoff_set.filter(instrument=signoff_instrument,
            signoff_type=Signoff.SIGNOFF_TYPE_ADVOCATE).first()

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
        context['advocate_signoff_type'] = Signoff.SIGNOFF_TYPE_ADVOCATE
        if signoff:
            # Populate form with instance
            form = SignoffForm(instance=signoff)
            context['advocate_signoff_exists'] = True
        else:
            # Default create form
            form = SignoffForm(initial={
                'signoff_type': Signoff.SIGNOFF_TYPE_ADVOCATE,
                'instrument': signoff_instrument,
            })
            context['advocate_signoff_exists'] = False

        context['advocate_signoff_form'] = form

        return context


class ExposeHideMixin(ContextMixin):
    expose_perm_name = 'superevents.expose_superevent'
    hide_perm_name = 'superevents.hide_superevent'
    form_url_view_name = 'api:default:superevents:superevent-permissions'

    def get_context_data(self, **kwargs):

        # Get base context
        context = super(ExposeHideMixin, self).get_context_data(**kwargs)

        # Determine if user can modify permissions to expose or hide
        can_modify_permissions = False
        if (self.request.user.has_perm(self.expose_perm_name) and
            not self.object.is_exposed):
            # Object is hidden and user can expose
            can_modify_permissions = True
            button_text = 'Make this superevent publicly visible'
            action = 'expose'
        elif (self.request.user.has_perm(self.hide_perm_name) and
              self.object.is_exposed):
            # Object is visible and user can hide
            can_modify_permissions = True
            button_text = 'Make this superevent internal-only'
            action = 'hide'

        # Update context
        context['can_modify_permissions'] = can_modify_permissions
        if can_modify_permissions:
            context['permissions_form_button_text'] = button_text
            context['permissions_action'] = action

        return context


class ConfirmGwFormMixin(ContextMixin):
    """
    Mixin which determines whether the button (form) for "upgrading" a
    superevent to GW status should be shown in the web display.
    """

    def get_context_data(self, **kwargs):

        # Get base context
        context = super(ConfirmGwFormMixin, self).get_context_data(**kwargs)

        # Default setting is False
        context['show_gw_status_form'] = False

        # If superevent is already marked as a GW, just return
        if self.object.is_gw:
            return context

        # Otherwise, we need to check the superevent category and the
        # user's permissions to see if we should show the form.
        method_perm_pairs = {
            'is_production': 'superevents.confirm_gw_superevent',
            'is_test': 'superevents.confirm_gw_test_superevent',
            'is_mdc': 'superevents.confirm_gw_mdc_superevent',
        }
        for method_name, perm_name in method_perm_pairs.iteritems():
            is_category = getattr(self.object, method_name)
            if (is_category() and self.request.user.has_perm(perm_name)):
                context['show_gw_status_form'] = True
                break

        return context
