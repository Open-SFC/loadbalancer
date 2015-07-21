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
import netaddr
import re

from django.utils.text import normalize_newlines
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from openstack_dashboard import api
from horizon import exceptions
from horizon import forms
from horizon import workflows
#from horizon.utils import fields


LOG = logging.getLogger(__name__)


class CreateConfigInfoAction(workflows.Action):
    CONFIG_MODE_CHOICES = (
        ("", _("Select Config Mode")),
        ("NFV", _("NFV")),
        ("NN", _("Network Node")),
        ("OFC", _("OFC")),
    )
    config_name = forms.CharField(label=_("Configuration Name"),
                                  required=True,
                                  initial="",
                                  help_text=_("Name of the Configuration"))
    config_mode = forms.ChoiceField(label=_("Config Mode"),
                                    choices=CONFIG_MODE_CHOICES,
                                    required=True)

    class Meta:
        name = ("Configuration")
        help_text = _("From here you can create a new configuration.\n"
                      ""
                      "")
        


class CreateConfigInfo(workflows.Step):
    action_class = CreateConfigInfoAction
    contributes = ("config_name", "networkfunction_id", "config_mode")

class CreateConfiguration(workflows.Workflow):
    slug = "create_config"
    name = _("Create Configuration")
    finalize_button_name = _("Create")
    success_message = _('Created Configuration "%s".')
    failure_message = _('Unable to create Configuration "%s".')
    success_url = "horizon:project:nsloadbalancers:index"
    default_steps = (CreateConfigInfo,
                    )

    def format_status_message(self, message):
        name = self.context.get('config_name') or self.context.get('networkfunction_id', '')
        return message % name

    def handle(self, request, data):
        # create the service
        try:
	    ###Check if a service is available with the name
	    tenant_id = self.request.user.tenant_id
	    is_config = api.crdlbaas.config_handle_list_for_tenant(request, tenant_id, 
                                                 name=data['config_name'])
	    #####
	    if is_config:
		return False
	    else:
		config = api.crdlbaas.config_handle_create(request,
						     name=data['config_name'],
						     status=1,
						     slug='loadbalancer',
						     config_mode=data['config_mode'])
		config.set_id_as_name_if_empty()
		msg = _('Configuration "%s" was successfully created.') % config.name
		LOG.debug(msg)
        except:
            msg = _('Failed to create Configuration "%s".') % data['config_name']
            LOG.info(msg)
            redirect = reverse('horizon:project:nsloadbalancers:index')
            exceptions.handle(request, msg, redirect=redirect)
            return False

        return True
