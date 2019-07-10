import pytest

from django.urls import reverse

from events.models import Pipeline
from events.views import PipelineManageView


@pytest.mark.django_db
def test_pipeline_manage_view(standard_user, client):
    """Test pipeline manage view as various classes of non-advocate user"""
    if not standard_user.is_anonymous:
        client.force_login(standard_user)
    response = client.get(reverse('manage-pipelines'))

    # Expected response code by user
    response_dict = {
        'internal.user': 200,
        '': 403,
    }
    assert response.status_code == response_dict[standard_user.username]

    # Check context
    if response.status_code == 200:
        assert response.context['user_can_manage'] == False


def test_pipeline_manage_view_as_advocate(em_advocate_user, client):
    """Test pipeline manage view as EM advocate"""
    client.force_login(em_advocate_user)
    response = client.get(reverse('manage-pipelines'))

    # Expected response code
    assert response.status_code == 200

    # Check context
    assert response.context['user_can_manage'] == True


@pytest.mark.parametrize("view", ['enable-pipeline', 'disable-pipeline'])
@pytest.mark.django_db
def test_pipeline_change_views(view, standard_user, client):
    """
    Test pipeline enable/disable views as various classes of non-advocate user
    """
    if not standard_user.is_anonymous:
        client.force_login(standard_user)

    # Create a pipeline
    p, _ = Pipeline.objects.get_or_create(name='fake_pipeline')
    p.pipeline_type = Pipeline.PIPELINE_TYPE_SEARCH_PRODUCTION
    p.save(update_fields=['pipeline_type'])

    # NOTE: get() is wired to post() in the view
    response = client.get(reverse(view, args=[p.pk]))

    assert response.status_code == 403


@pytest.mark.parametrize("view", ['enable-pipeline', 'disable-pipeline'])
@pytest.mark.django_db
def test_pipeline_change_views_as_advocate(view, em_advocate_user, client):
    """
    Test pipeline enable/disable views as various classes of non-advocate user
    """
    client.force_login(em_advocate_user)

    # Create a pipeline
    p, _ = Pipeline.objects.get_or_create(name='fake_pipeline')
    p.pipeline_type = Pipeline.PIPELINE_TYPE_SEARCH_PRODUCTION
    p.save(update_fields=['pipeline_type'])

    # NOTE: get() is wired to post() in the view
    response = client.get(reverse(view, args=[p.pk]))

    assert response.status_code == 302
