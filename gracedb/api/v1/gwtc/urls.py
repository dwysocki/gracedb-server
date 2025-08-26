from django.urls import re_path, include, path, register_converter
from rest_framework import routers

from core.utils import DotSlugConverter
from .viewsets import *


register_converter(DotSlugConverter, 'dotslug')

urlpatterns = [
    # Listing of all gwtc's:
    re_path(r'^$', gwtc_viewset.as_view({'get': 'list', 'post': 'create'}), name='gwtc-list'),

    # Listing of all versions of a gwtc number:
    path('<str:number>/', gwtc_viewset.as_view({'get': 'list',}), name='gwtc-number-list'),

    # show a single version of a gwtc number:
    path('<dotslug:number>/<slug:version>/', gwtc_viewset.as_view({'get': 'retrieve',}), name='gwtc-version-detail'),

]
