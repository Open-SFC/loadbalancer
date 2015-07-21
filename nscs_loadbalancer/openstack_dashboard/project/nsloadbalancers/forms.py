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

import logging

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from openstack_dashboard import api
from horizon import exceptions
from horizon import forms
from horizon import messages


LOG = logging.getLogger(__name__)

class BaseConfigForm(forms.SelfHandlingForm):
    def __init__(self, request, *args, **kwargs):
        super(BaseConfigForm, self).__init__(request, *args, **kwargs)
        # Populate Loadbalancer choices
        lb_choices = [('', _("Select a Loadbalancer"))]
        loadbalancers = api.crdlbaas.pool_list(request)
        for lb in loadbalancers:
            lb_choices.append((lb.id, lb.name))
        self.fields['lb_id'].choices = lb_choices

class MapLoadbalancer(BaseConfigForm):
    config_handle_id = forms.CharField(label=_("Config ID"),
                                 widget=forms.TextInput(
                                     attrs={'readonly': 'readonly'}))
    lb_id = forms.ChoiceField(label=_("Loadbalancers"),
                                        required=True,
                                        help_text=_("Select one of the"
                                                    "Loadbalancers available"))
    tenant_id = forms.CharField(widget=forms.HiddenInput)
        
    failure_url = 'horizon:project:nsloadbalancers:index'

    def handle(self, request, data):
        try:
            LOG.debug('params = %s' % data)
            config = api.crdlbaas.pool_update(request, data['lb_id'],
                                               config_handle_id=data['config_handle_id'])
            msg = _('Loadbalancer was successfully mapped for the Configuration %s.') % data['config_handle_id']
            LOG.debug(msg)
            messages.success(request, msg)
            return config
        except Exception:
            msg = _('Failed to map Loadbalancer for the COnfiguration %s') % data['config_handle_id']
            LOG.info(msg)
            redirect = reverse(self.failure_url)
            exceptions.handle(request, msg, redirect=redirect)
            
class UpdateConfig(forms.SelfHandlingForm):
    config_id = forms.CharField(label=_("ID"),
                                 widget=forms.TextInput(
                                     attrs={'readonly': 'readonly'}))
    name = forms.CharField(label=_("Configuration Name"),
                                  required=True,
                                  initial="",
                                  help_text=_("Name of the Configuration"))
    tenant_id = forms.CharField(widget=forms.HiddenInput)
        
    failure_url = 'horizon:project:nsloadbalancers:index'

    def handle(self, request, data):
        try:
            LOG.debug('params = %s' % data)
            #params = {'name': data['name']}
            #params['gateway_ip'] = data['gateway_ip']
            config = api.crdlbaas.config_handle_modify(request, data['config_id'],
                                               name=data['name'])
            msg = _('Configuration %s was successfully updated.') % data['config_id']
            LOG.debug(msg)
            messages.success(request, msg)
            return config
        except Exception:
            msg = _('Failed to update Configuration %s') % data['name']
            LOG.info(msg)
            redirect = reverse(self.failure_url)
            exceptions.handle(request, msg, redirect=redirect)
            
class UnMapLoadbalancer(forms.SelfHandlingForm):
    config_handle_id = forms.CharField(label=_("Config ID"),
                                 widget=forms.TextInput(
                                     attrs={'readonly': 'readonly'}))
    lb_id = forms.CharField(label=_("Pool ID"),
                                 widget=forms.TextInput(
                                     attrs={'readonly': 'readonly'}))
    failure_url = 'horizon:project:nsloadbalancers:index'

    def handle(self, request, data):
        try:
            LOG.debug('params = %s' % data)
            config = api.crdlbaas.pool_update(request, data['lb_id'],
                                               config_handle_id='')
            msg = _('Loadbalancer Pool was successfully dettached for the Configuration %s.') % data['config_handle_id']
            LOG.debug(msg)
            messages.success(request, msg)
            return config
        except Exception:
            msg = _('Failed to dettach Loadbalancer Pool for the Configuration %s') % data['config_handle_id']
            LOG.info(msg)
            redirect = reverse(self.failure_url)
            exceptions.handle(request, msg, redirect=redirect)
