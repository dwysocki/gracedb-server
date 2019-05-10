import pytest

from django.conf import settings
from django.contrib.auth.models import (
    Group, Permission, AnonymousUser,
)

# Groups ----------------------------------------------------------------------
@pytest.mark.django_db
@pytest.fixture
def internal_group():
    group, _ = Group.objects.get_or_create(name=settings.LVC_GROUP)

    # Add permissions
    perm_data = [
        {'app': 'superevents', 'codename': 'add_labelling'},
        {'app': 'superevents', 'codename': 'delete_labelling'},
        {'app': 'superevents', 'codename': 'tag_log'},
        {'app': 'superevents', 'codename': 'untag_log'},
        {'app': 'superevents', 'codename': 'view_log'},
        {'app': 'superevents', 'codename': 'add_test_superevent'},
        {'app': 'superevents', 'codename': 'change_test_superevent'},
        {'app': 'superevents', 'codename': 'confirm_gw_test_superevent'},
        {'app': 'superevents', 'codename': 'annotate_superevent'},
        {'app': 'superevents', 'codename': 'view_superevent'},
        {'app': 'superevents', 'codename': 'add_voevent'},
        {'app': 'superevents', 'codename': 'view_supereventgroupobjectpermission'},
        {'app': 'superevents', 'codename': 'view_signoff'},
    ]
    permission_list = []
    for perm in perm_data:
        p, _  = Permission.objects.get_or_create(
            content_type__app_label=perm['app'],
            codename=perm['codename'])
        permission_list.append(p)
    group.permissions.add(*permission_list)

    return group

@pytest.mark.django_db
@pytest.fixture
def em_advocates_group():
    group, _ = Group.objects.get_or_create(name=settings.EM_ADVOCATE_GROUP)

    # Add permissions
    perm_data = [
        {'app': 'superevents', 'codename': 'add_signoff'},
        {'app': 'superevents', 'codename': 'change_signoff'},
        {'app': 'superevents', 'codename': 'delete_signoff'},
        {'app': 'superevents', 'codename': 'do_adv_signoff'},
        {'app': 'events', 'codename': 'manage_pipeline'},
    ]
    permission_list = []
    for perm in perm_data:
        p, _ = Permission.objects.get_or_create(
            content_type__app_label=perm['app'],
            codename=perm['codename'])
        permission_list.append(p)
    group.permissions.add(*permission_list)

    return group


# Users =======================================================================

## Basic users ------------------------
@pytest.mark.django_db
@pytest.fixture
def internal_user(django_user_model, internal_group):
    user, _ = django_user_model.objects.get_or_create(username='internal.user')
    internal_group.user_set.add(user)
    return user


@pytest.fixture
def public_user():
    return AnonymousUser()


## Special users ----------------------
@pytest.fixture
def em_advocate_user(django_user_model, internal_group, em_advocates_group):
    user, _ = django_user_model.objects.get_or_create(
        username='em_advocate.user')
    em_advocates_group.user_set.add(user)
    # Also add to internal group
    internal_group.user_set.add(user)

    return user


# User lists ------------------------------------------------------------------
@pytest.fixture(params=['internal_user', 'public_user'])
def standard_user(request):
    """
    Parametrized fixture which includes 'standard' user classes:
    internal user, public user (LV-EM user to come?)
    """
    return request.getfixturevalue(request.param)
