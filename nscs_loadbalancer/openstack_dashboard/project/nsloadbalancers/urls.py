# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Freescale Semiconductor, Inc.
# All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from django.conf.urls import patterns, url, include

from .views import IndexView, CreateView, UpdateView, MapLoadbalancerView, ListLoadbalancerView, UnMapLoadbalancerView

VIEWS_MOD = 'openstack_dashboard.dashboards.project.nsloadbalancers.views'
CONFIGS = r'^(?P<config_id>[^/]+)/%s$'

urlpatterns = patterns(VIEWS_MOD,
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^create$', CreateView.as_view(), name='create'),
    url(CONFIGS % 'update', UpdateView.as_view(), name='update'),
    url(CONFIGS % 'maplb', MapLoadbalancerView.as_view(), name='maplb'),
    url(CONFIGS % 'listlbs', ListLoadbalancerView.as_view(), name='listlbs'),
    url(r'^(?P<config_id>[^/]+)/loadbalancers/(?P<lb_id>[^/]+)/unmaplb$', UnMapLoadbalancerView.as_view(), name='unmaplb'),)
    