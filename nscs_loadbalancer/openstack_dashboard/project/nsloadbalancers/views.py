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
import datetime
import logging

from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from openstack_dashboard import api
from horizon import exceptions
from horizon import forms
from horizon import tables
from horizon import workflows

from .tables import LoadbalancersTable, ConfigurationsTable
from .forms import MapLoadbalancer, UpdateConfig, UnMapLoadbalancer
from .workflows import CreateConfiguration

LOG = logging.getLogger(__name__)

class IndexView(tables.DataTableView):
    table_class = ConfigurationsTable
    template_name = 'project/nsloadbalancers/index.html'

    def get_data(self):
        try:
            tenant_id = self.request.user.tenant_id
            configurations = api.crdlbaas.config_handle_list_for_tenant(self.request,
                                                           tenant_id,
							   slug='loadbalancer')
        except:
            configurations = []
            msg = _('Configuration list can not be retrieved.')
            exceptions.handle(self.request, msg)
        for n in configurations:
            n.set_id_as_name_if_empty()
        return configurations

class CreateView(workflows.WorkflowView):
    workflow_class = CreateConfiguration
    template_name = 'project/nsloadbalancers/create.html'

    def get_initial(self):
        pass

class UpdateView(forms.ModalFormView):
    form_class = UpdateConfig
    template_name = 'project/nsloadbalancers/update.html'
    context_object_name = 'configuration'
    success_url = reverse_lazy('horizon:project:nsloadbalancers:index')

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        context["config_id"] = self.kwargs['config_id']
        return context
    
    def _get_object(self, *args, **kwargs):
        if not hasattr(self, "_object"):
            config_id = self.kwargs['config_id']
            try:
                self._object = api.crdlbaas.config_handle_get(self.request, config_id)
            except:
                redirect = self.success_url
                msg = _('Unable to retrieve Configuration details')
                exceptions.handle(self.request, msg, redirect=redirect)
        return self._object

    def get_initial(self):
        configuration = self._get_object()
        return {'config_id': configuration['id'],
                'tenant_id': configuration['tenant_id'],
                'name': configuration['name']}

class MapLoadbalancerView(forms.ModalFormView):
    form_class = MapLoadbalancer
    template_name = 'project/nsloadbalancers/updatelb.html'
    context_object_name = 'loadbalancer'
    success_url = reverse_lazy('horizon:project:nsloadbalancers:index')

    def get_context_data(self, **kwargs):
        context = super(MapLoadbalancerView, self).get_context_data(**kwargs)
        context["config_id"] = self.kwargs['config_id']
        return context
    
    def _get_object(self, *args, **kwargs):
        if not hasattr(self, "_object"):
            config_id = self.kwargs['config_id']
            try:
                self._object = api.crdlbaas.config_handle_get(self.request, config_id)
            except:
                redirect = self.success_url
                msg = _('Unable to retrieve Configuration details')
                exceptions.handle(self.request, msg, redirect=redirect)
        return self._object

    def get_initial(self):
        config_handle = self._get_object()
        return {'config_handle_id': config_handle['id'],
                'tenant_id': config_handle['tenant_id']}

class ListLoadbalancerView(tables.DataTableView):
    table_class = LoadbalancersTable
    template_name = 'project/nsloadbalancers/lbindex.html'

    def get_data(self):
        try:
            tenant_id = self.request.user.tenant_id
	    config_id = self.kwargs['config_id']
            nsloadbalancers = api.crdlbaas.pool_list(self.request,
						 tenant_id=tenant_id,
						 config_handle_id=config_id)
	    for lb in nsloadbalancers:
		config_name = ''
                config_handle_id = lb.config_handle_id
		if config_handle_id:
		    config_handle = api.crdlbaas.config_handle_get(self.request, config_handle_id)
		    config_name = config_handle.name
                setattr(lb, 'config_name', config_name)
        except:
            nsloadbalancers = []
            msg = _('Loadbalancer Pool list can not be retrieved.')
            exceptions.handle(self.request, msg)
        for n in nsloadbalancers:
            n.set_id_as_name_if_empty()
        return nsloadbalancers
    
class UnMapLoadbalancerView(forms.ModalFormView):
    form_class = UnMapLoadbalancer
    template_name = 'project/nsloadbalancers/unmaplb.html'
    context_object_name = 'loadbalancer'
    success_url = reverse_lazy('horizon:project:nsloadbalancers:index')

    def get_context_data(self, **kwargs):
        context = super(UnMapLoadbalancerView, self).get_context_data(**kwargs)
        context["config_id"] = self.kwargs['config_id']
	context["lb_id"] = self.kwargs['lb_id']
        return context
    
    def _get_object(self, *args, **kwargs):
        if not hasattr(self, "_object"):
            lb_id = self.kwargs['lb_id']
            try:
                self._object = api.crdlbaas.pool_get(self.request, lb_id)
            except:
                redirect = self.success_url
                msg = _('Unable to retrieve Loadbalancer Pool details')
                exceptions.handle(self.request, msg, redirect=redirect)
        return self._object

    def get_initial(self):
        loadbalancer = self._get_object()
        return {'config_handle_id': loadbalancer['config_handle_id'],
                'lb_id': loadbalancer['id']}
