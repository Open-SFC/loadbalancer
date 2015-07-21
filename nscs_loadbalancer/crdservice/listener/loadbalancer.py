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

from nscs.crdservice.openstack.common import log as logging
from nscs.crdservice.openstack.common import context
from nscs.crdservice import context as crd_context
from nscs.crdservice.openstack.common import rpc
from nscs.crdservice.openstack.common.rpc import dispatcher
from nscs.crdservice.openstack.common.rpc import proxy
from oslo.config import cfg


import re
import socket



LOG = logging.getLogger(__name__)



class LoadbalancerListener(proxy.RpcProxy):
    """
    Keep listening on Firewall and CRD-Consumer Notifications
    """
    RPC_API_VERSION = '1.0'
    
    def __init__(self):
	self.context = crd_context.Context('crd', 'crd',
                                                   is_admin=True)
        polling_interval = 2
        reconnect_interval = 2
        self.rpc = True
        
        self.polling_interval = polling_interval
        self.reconnect_interval = reconnect_interval
        if self.rpc:
            self.setup_rpc()
        LOG.info("Loadbalancer RPC Listener initialized successfully, now running...")
        
    
    def setup_rpc(self):
        self.host = self.get_hostname()
	self.listen_topic = "generate_slb_config"
	# CRD RPC Notification
        self.listen_context = context.RequestContext('crd', 'crd',
                                              is_admin=False)
        
        # Handle updates from service
        self.dispatcher = self.create_rpc_dispatcher()
       
	# Define the listening consumers for the agent
        self.listen_conn = rpc.create_connection(new=True)
        self.listen_conn.create_consumer(self.listen_topic, self.dispatcher, fanout=False)
        self.listen_conn.consume_in_thread()
        
        
    def get_hostname(self):
        return "%s" % socket.gethostname()
    
    def create_rpc_dispatcher(self):
        '''Get the rpc dispatcher for this manager.

        If a manager would like to set an rpc API version, or support more than
        one class as the target of rpc messages, override this method.
        '''
        return dispatcher.RpcDispatcher([self])

    
    
    
    