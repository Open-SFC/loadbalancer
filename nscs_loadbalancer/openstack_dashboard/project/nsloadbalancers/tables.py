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

from django import template
from django.core.urlresolvers import reverse
from django.utils.http import urlencode
from django.template import defaultfilters as filters
from django.utils.translation import ugettext_lazy as _

from openstack_dashboard import api
from horizon import exceptions
from horizon import tables


LOG = logging.getLogger(__name__)

class DeleteConfig(tables.DeleteAction):
    data_type_singular = _("Configuration")
    data_type_plural = _("Configurations")

    def delete(self, request, configuration_id):
        try:
            api.crdlbaas.config_handle_delete(request, configuration_id)
            LOG.debug('Deleted configuration %s successfully' % configuration_id)
        except:
            msg = _('Failed to delete configuration %s') % configuration_id
            LOG.info(msg)
            redirect = reverse("horizon:project:nsloadbalancers:index")
            exceptions.handle(request, msg, redirect=redirect)

class MapLoadbalancer(tables.LinkAction):
    name = "maplb"
    verbose_name = _("Map Loadbalancer")
    url = "horizon:project:nsloadbalancers:maplb"
    classes = ("ajax-modal", "btn-edit")

class CreateConfig(tables.LinkAction):
    name = "create"
    verbose_name = _("Add Configuration")
    url = "horizon:project:nsloadbalancers:create"
    classes = ("ajax-modal", "btn-create")

class EditConfig(tables.LinkAction):
    name = "update"
    verbose_name = _("Edit Configuration")
    url = "horizon:project:nsloadbalancers:update"
    classes = ("ajax-modal", "btn-edit")

class ListLoadbalancers(tables.LinkAction):
    name = "listlbs"
    verbose_name = _("List Loadbalancers")
    url = "horizon:project:nsloadbalancers:listlbs"
    
class UnMapLoadbalancer(tables.LinkAction):
    name = "unmaplb"
    verbose_name = _("Unmap Pool")
    url = "horizon:project:nsloadbalancers:unmaplb"
    classes = ("ajax-modal", "btn-edit")
    
    def get_link_url(self, pool):
        config_id = self.table.kwargs['config_id']
        return reverse(self.url, args=(config_id, pool.id))

class ConfigurationsTable(tables.DataTable):
    name = tables.Column("name",
                         verbose_name=_("Name"))
    config_mode = tables.Column("config_mode", verbose_name=_("Mode"))
    status = tables.Column("status", verbose_name=_("Status"))

    class Meta:
        name = "configurations"
        verbose_name = _("Configurations")
        table_actions = (CreateConfig, DeleteConfig)
        row_actions = (ListLoadbalancers, MapLoadbalancer, EditConfig, DeleteConfig)

class LoadbalancersTable(tables.DataTable):
    name = tables.Column("name",
                         verbose_name=_("Name"),
                         link="horizon:project:loadbalancers:pooldetails")
    config_name = tables.Column("config_name", verbose_name=_("Mapped Configurations"))
    status = tables.Column("status", verbose_name=_("Status"))

    class Meta:
        name = "nsloadbalancers"
        verbose_name = _("Loadbalancers")
        row_actions = (UnMapLoadbalancer,)
