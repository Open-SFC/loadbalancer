# Copyright 2013 Freescale Semiconductor, Inc.
# All Rights Reserved
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
#
# vim: tabstop=4 shiftwidth=4 softtabstop=4

import logging
from nscs.crdclient.v2_0 import client as crd_client

_logger = logging.getLogger(__name__)

class Client(object):
    """
    SLB related Client Functions in CRD
    """
    networkfunctions_path = "/lb/networkfunctions"
    networkfunction_path = "/lb/networkfunctions/%s"
    config_handles_path = "/lb/config_handles"
    config_handle_path = "/lb/config_handles/%s"
    
    ##Loadbalancer URLs
    vips_path = "/lb/vips"
    vip_path = "/lb/vips/%s"
    pools_path = "/lb/pools"
    pool_path = "/lb/pools/%s"
    pool_path_stats = "/lb/pools/%s/stats"
    members_path = "/lb/members"
    member_path = "/lb/members/%s"
    health_monitors_path = "/lb/health_monitors"
    health_monitor_path = "/lb/health_monitors/%s"
    associate_pool_health_monitors_path = "/lb/pools/%s/health_monitors"
    disassociate_pool_health_monitors_path = (
        "/lb/pools/%(pool)s/health_monitors/%(health_monitor)s")
    slb_configs_path = "/lb/configs"
    
    SLB_EXTED_PLURALS = {'vips': 'vip',
                     'pools': 'pool',
                     'members': 'member',
                     'health_monitors': 'health_monitor',
                     }

    ################################################################
    ##                LBaaS Service Management                    ##
    ################################################################
    
    @crd_client.APIParamsCall
    def list_vips(self, retrieve_all=True, **_params):
        """Fetches a list of all load balancer vips for a tenant."""
        # Pass filters in "params" argument to do_request
        return self.crdclient.list('vips', self.vips_path, retrieve_all,
                         **_params)

    @crd_client.APIParamsCall
    def show_vip(self, vip, **_params):
        """Fetches information of a certain load balancer vip."""
        return self.crdclient.get(self.vip_path % (vip), params=_params)

    @crd_client.APIParamsCall
    def create_vip(self, body=None):
        """Creates a new load balancer vip."""
        return self.crdclient.post(self.vips_path, body=body)

    @crd_client.APIParamsCall
    def update_vip(self, vip, body=None):
        """Updates a load balancer vip."""
        return self.crdclient.put(self.vip_path % (vip), body=body)

    @crd_client.APIParamsCall
    def delete_vip(self, vip):
        """Deletes the specified load balancer vip."""
        return self.crdclient.delete(self.vip_path % (vip))

    @crd_client.APIParamsCall
    def list_pools(self, retrieve_all=True, **_params):
        """Fetches a list of all load balancer pools for a tenant."""
        # Pass filters in "params" argument to do_request
        return self.crdclient.list('pools', self.pools_path, retrieve_all,
                         **_params)

    @crd_client.APIParamsCall
    def show_pool(self, pool, **_params):
        """Fetches information of a certain load balancer pool."""
        return self.crdclient.get(self.pool_path % (pool), params=_params)

    @crd_client.APIParamsCall
    def create_pool(self, body=None):
        """Creates a new load balancer pool."""
        return self.crdclient.post(self.pools_path, body=body)

    @crd_client.APIParamsCall
    def update_pool(self, pool, body=None):
        """Updates a load balancer pool."""
        return self.crdclient.put(self.pool_path % (pool), body=body)

    @crd_client.APIParamsCall
    def delete_pool(self, pool):
        """Deletes the specified load balancer pool."""
        return self.crdclient.delete(self.pool_path % (pool))

    @crd_client.APIParamsCall
    def retrieve_pool_stats(self, pool, **_params):
        """Retrieves stats for a certain load balancer pool."""
        return self.crdclient.get(self.pool_path_stats % (pool), params=_params)

    @crd_client.APIParamsCall
    def list_members(self, retrieve_all=True, **_params):
        """Fetches a list of all load balancer members for a tenant."""
        # Pass filters in "params" argument to do_request
        return self.crdclient.list('members', self.members_path, retrieve_all,
                         **_params)

    @crd_client.APIParamsCall
    def show_member(self, member, **_params):
        """Fetches information of a certain load balancer member."""
        return self.crdclient.get(self.member_path % (member), params=_params)

    @crd_client.APIParamsCall
    def create_member(self, body=None):
        """Creates a new load balancer member."""
        return self.crdclient.post(self.members_path, body=body)

    @crd_client.APIParamsCall
    def update_member(self, member, body=None):
        """Updates a load balancer member."""
        return self.crdclient.put(self.member_path % (member), body=body)

    @crd_client.APIParamsCall
    def delete_member(self, member):
        """Deletes the specified load balancer member."""
        return self.crdclient.delete(self.member_path % (member))

    @crd_client.APIParamsCall
    def list_health_monitors(self, retrieve_all=True, **_params):
        """Fetches a list of all load balancer health monitors for a tenant."""
        # Pass filters in "params" argument to do_request
        return self.crdclient.list('health_monitors', self.health_monitors_path,
                         retrieve_all, **_params)

    @crd_client.APIParamsCall
    def show_health_monitor(self, health_monitor, **_params):
        """Fetches information of a certain load balancer health monitor."""
        return self.crdclient.get(self.health_monitor_path % (health_monitor),
                        params=_params)

    @crd_client.APIParamsCall
    def create_health_monitor(self, body=None):
        """Creates a new load balancer health monitor."""
        return self.crdclient.post(self.health_monitors_path, body=body)

    @crd_client.APIParamsCall
    def update_health_monitor(self, health_monitor, body=None):
        """Updates a load balancer health monitor."""
        return self.crdclient.put(self.health_monitor_path % (health_monitor), body=body)

    @crd_client.APIParamsCall
    def delete_health_monitor(self, health_monitor):
        """Deletes the specified load balancer health monitor."""
        return self.crdclient.delete(self.health_monitor_path % (health_monitor))

    @crd_client.APIParamsCall
    def associate_health_monitor(self, pool, body):
        """Associate  specified load balancer health monitor and pool."""
        return self.crdclient.post(self.associate_pool_health_monitors_path % (pool),
                         body=body)

    @crd_client.APIParamsCall
    def disassociate_health_monitor(self, pool, health_monitor):
        """Disassociate specified load balancer health monitor and pool."""
        path = (self.disassociate_pool_health_monitors_path %
                {'pool': pool, 'health_monitor': health_monitor})
        return self.crdclient.delete(path)
    
    @crd_client.APIParamsCall
    def generate_slb_config(self, body=None):
        """
        Generate the specified configuration
        """
        return self.crdclient.post(self.slb_configs_path, body=body)
    ##################### End of Loadbalancer Management ####
    
    ####### Network Function API start######################################    
    @crd_client.APIParamsCall
    def list_networkfunctions(self, **_params):
        """
        Fetches a list of all networkfunctions for a tenant
        """
        # Pass filters in "params" argument to do_request
        return self.crdclient.get(self.networkfunctions_path, params=_params)
        
    @crd_client.APIParamsCall
    def create_networkfunction(self, body=None):
        """
        Creates a new Networkfunction
        """
        return self.crdclient.post(self.networkfunctions_path, body=body)
        
    @crd_client.APIParamsCall
    def delete_networkfunction(self, networkfunction):
        """
        Deletes the specified networkfunction
        """
        return self.crdclient.delete(self.networkfunction_path % (networkfunction))
    
    @crd_client.APIParamsCall
    def show_networkfunction(self, networkfunction, **_params):
        """
        Fetches information of a certain networkfunction
        """
        return self.crdclient.get(self.networkfunction_path % (networkfunction), params=_params)
        
    @crd_client.APIParamsCall
    def update_networkfunction(self, networkfunction, body=None):
        """
        Updates a networkfunction
        """
        return self.crdclient.put(self.networkfunction_path % (networkfunction), body=body)
    ####### Network Function API End######################################
    
    ####### Config handle API Begin######################################
    @crd_client.APIParamsCall
    def list_config_handles(self, **_params):
        """
        Fetches a list of all config_handles for a tenant
        """
        # Pass filters in "params" argument to do_request
        return self.crdclient.get(self.config_handles_path, params=_params)
        
    @crd_client.APIParamsCall
    def create_config_handle(self, body=None):
        """
        Creates a new Config_handle
        """
        return self.crdclient.post(self.config_handles_path, body=body)
        
    @crd_client.APIParamsCall
    def delete_config_handle(self, config_handle):
        """
        Deletes the specified config_handle
        """
        return self.crdclient.delete(self.config_handle_path % (config_handle))
    
    @crd_client.APIParamsCall
    def show_config_handle(self, config_handle, **_params):
        """
        Fetches information of a certain config_handle
        """
        return self.crdclient.get(self.config_handle_path % (config_handle), params=_params)
        
    @crd_client.APIParamsCall
    def update_config_handle(self, config_handle, body=None):
        """
        Updates a config_handle
        """
        return self.crdclient.put(self.config_handle_path % (config_handle), body=body)
    ####### Config handle API End######################################
        
    
    def __init__(self, **kwargs):
        self.crdclient = crd_client.Client(**kwargs)
        self.crdclient.EXTED_PLURALS.update(self.SLB_EXTED_PLURALS)
        self.format = 'json'
    
