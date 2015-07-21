# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2013 New Dream Network, LLC (DreamHost)
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
# @author: Mark McClain, DreamHost

import uuid
import configparser
import os
from oslo.config import cfg

from nscs.crdservice.common import constants as q_const
from nscs.crdservice.common import exceptions as n_exc
from nscs.crdservice.common import rpc as q_rpc
from nscs_loadbalancer.crdservice import topics
from nscs_loadbalancer.crdservice.db import agents_db
from nscs_loadbalancer.crdservice.db import loadbalancer_db
from nscs_loadbalancer.crdservice.extensions import lbaas_agentscheduler
from nscs.crdservice.extensions import portbindings
from nscs.crdservice.openstack.common import importutils
from nscs.crdservice.openstack.common import log as logging
from nscs.crdservice.openstack.common import rpc
from nscs.crdservice.openstack.common.rpc import proxy
from nscs_loadbalancer.crdservice.plugins.common import constants
from nscs_loadbalancer.crdservice.drivers import abstract_driver
from neutronclient.v2_0 import client as neutron_client
from nscs_loadbalancer.crdservice.agent.linux import ip_lib
from nscs_loadbalancer.crdservice.agent.linux import utils

LOG = logging.getLogger(__name__)

#AGENT_SCHEDULER_OPTS = [
#    cfg.StrOpt('loadbalancer_pool_scheduler_driver',
#               default='crd.services.loadbalancer.agent_scheduler'
#                       '.ChanceScheduler',
#               help=_('Driver to use for scheduling '
#                      'pool to a default loadbalancer agent')),
#]
#
#cfg.CONF.register_opts(AGENT_SCHEDULER_OPTS)


modconf = configparser.ConfigParser()
confpath = cfg.CONF.config_file[0]
confpath = confpath.replace('nscs.conf', 'modules/loadbalancer.conf')
modconf.read(confpath)
nwservice_driver = str(modconf.get("DEFAULT","nwservice_driver"))


crd_nwservices_load_opts = [
    cfg.StrOpt('admin_user',default="crd"),
    cfg.StrOpt('admin_password',default="service_pass"),
    cfg.StrOpt('admin_tenant_name',default="service"),
    cfg.StrOpt('auth_url'),
]
#cfg.CONF.register_opts(crd_nwservices_load_opts, "nscs_authtoken")

NS_PREFIX = 'qlbaas-'

class DriverNotSpecified(n_exc.CrdException):
    message = _("Device driver for agent should be specified "
                "in plugin driver.")


class LoadBalancerCallbacks(object):

    RPC_API_VERSION = '2.0'
    # history
    #   1.0 Initial version
    #   2.0 Generic API for agent based drivers
    #       - get_logical_device() handling changed;
    #       - pool_deployed() and update_status() methods added;

    def __init__(self, plugin):
        self.plugin = plugin

    def create_rpc_dispatcher(self):
        return q_rpc.PluginRpcDispatcher(
            [self, agents_db.AgentExtRpcCallback(self.plugin)])

    def get_ready_devices(self, context, host=None):
        with context.session.begin(subtransactions=True):
            agents = self.plugin.get_lbaas_agents(context,
                                                  filters={'host': [host]})
            if not agents:
                return []
            elif len(agents) > 1:
                LOG.warning(_('Multiple lbaas agents found on host %s'), host)
            pools = self.plugin.list_pools_on_lbaas_agent(context,
                                                          agents[0].id)
            pool_ids = [pool['id'] for pool in pools['pools']]

            qry = context.session.query(loadbalancer_db.Pool.id)
            qry = qry.filter(loadbalancer_db.Pool.id.in_(pool_ids))
            qry = qry.filter(
                loadbalancer_db.Pool.status.in_(
                    constants.ACTIVE_PENDING_STATUSES))
            up = True  # makes pep8 and sqlalchemy happy
            qry = qry.filter(loadbalancer_db.Pool.admin_state_up == up)
            return [id for id, in qry]

    def get_logical_device(self, context, pool_id=None):
        with context.session.begin(subtransactions=True):
            qry = context.session.query(loadbalancer_db.Pool)
            qry = qry.filter_by(id=pool_id)
            pool = qry.one()
            retval = {}
            retval['pool'] = self.plugin._make_pool_dict(pool)

            if pool.vip:
                retval['vip'] = self.plugin._make_vip_dict(pool.vip)
                retval['vip']['port'] = (
                    self.plugin._core_plugin._make_port_dict(pool.vip.port)
                )
                for fixed_ip in retval['vip']['port']['fixed_ips']:
                    fixed_ip['subnet'] = (
                        self.plugin._core_plugin.get_subnet(
                            context,
                            fixed_ip['subnet_id']
                        )
                    )
            retval['members'] = [
                self.plugin._make_member_dict(m)
                for m in pool.members if (
                    m.status in constants.ACTIVE_PENDING_STATUSES or
                    m.status == constants.INACTIVE)
            ]
            retval['healthmonitors'] = [
                self.plugin._make_health_monitor_dict(hm.healthmonitor)
                for hm in pool.monitors
                if hm.status in constants.ACTIVE_PENDING_STATUSES
            ]
            retval['driver'] = (
                self.plugin.drivers[pool.provider.provider_name].device_driver)

            return retval

    def pool_deployed(self, context, pool_id):
        with context.session.begin(subtransactions=True):
            qry = context.session.query(loadbalancer_db.Pool)
            qry = qry.filter_by(id=pool_id)
            pool = qry.one()

            # set all resources to active
            if pool.status in constants.ACTIVE_PENDING_STATUSES:
                pool.status = constants.ACTIVE

            if (pool.vip and pool.vip.status in
                    constants.ACTIVE_PENDING_STATUSES):
                pool.vip.status = constants.ACTIVE

            for m in pool.members:
                if m.status in constants.ACTIVE_PENDING_STATUSES:
                    m.status = constants.ACTIVE

            for hm in pool.monitors:
                if hm.status in constants.ACTIVE_PENDING_STATUSES:
                    hm.status = constants.ACTIVE

    def update_status(self, context, obj_type, obj_id, status):
        model_mapping = {
            'pool': loadbalancer_db.Pool,
            'vip': loadbalancer_db.Vip,
            'member': loadbalancer_db.Member,
            'health_monitor': loadbalancer_db.PoolMonitorAssociation
        }
        if obj_type not in model_mapping:
            raise n_exc.Invalid(_('Unknown object type: %s') % obj_type)
        try:
            if obj_type == 'health_monitor':
                self.plugin.update_pool_health_monitor(
                    context, obj_id['monitor_id'], obj_id['pool_id'], status)
            else:
                self.plugin.update_status(
                    context, model_mapping[obj_type], obj_id, status)
        except n_exc.NotFound:
            # update_status may come from agent on an object which was
            # already deleted from db with other request
            LOG.warning(_('Cannot update status: %(obj_type)s %(obj_id)s '
                          'not found in the DB, it was probably deleted '
                          'concurrently'),
                        {'obj_type': obj_type, 'obj_id': obj_id})

    def pool_destroyed(self, context, pool_id=None):
        """Agent confirmation hook that a pool has been destroyed.

        This method exists for subclasses to change the deletion
        behavior.
        """
        pass

    def plug_vip_port(self, context, port_id=None, host=None):
        if not port_id:
            return

        try:
            port = self.plugin._core_plugin.get_port(
                context,
                port_id
            )
        except n_exc.PortNotFound:
            msg = _('Unable to find port %s to plug.')
            LOG.debug(msg, port_id)
            return

        port['admin_state_up'] = True
        port['device_owner'] = 'crd:' + constants.LOADBALANCER
        port['device_id'] = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(host)))
        port[portbindings.HOST_ID] = host
        self.plugin._core_plugin.update_port(
            context,
            port_id,
            {'port': port}
        )

    def unplug_vip_port(self, context, port_id=None, host=None):
        if not port_id:
            return

        try:
            port = self.plugin._core_plugin.get_port(
                context,
                port_id
            )
        except n_exc.PortNotFound:
            msg = _('Unable to find port %s to unplug.  This can occur when '
                    'the Vip has been deleted first.')
            LOG.debug(msg, port_id)
            return

        port['admin_state_up'] = False
        port['device_owner'] = ''
        port['device_id'] = ''

        try:
            self.plugin._core_plugin.update_port(
                context,
                port_id,
                {'port': port}
            )

        except n_exc.PortNotFound:
            msg = _('Unable to find port %s to unplug.  This can occur when '
                    'the Vip has been deleted first.')
            LOG.debug(msg, port_id)

    def update_pool_stats(self, context, pool_id=None, stats=None, host=None):
        self.plugin.update_pool_stats(context, pool_id, data=stats)


class LoadBalancerAgentApi(proxy.RpcProxy):
    """Plugin side of plugin to agent RPC API."""

    BASE_RPC_API_VERSION = '2.0'
    # history
    #   1.0 Initial version
    #   1.1 Support agent_updated call
    #   2.0 Generic API for agent based drivers
    #       - modify/reload/destroy_pool methods were removed;
    #       - added methods to handle create/update/delete for every lbaas
    #       object individually;

    def __init__(self, topic):
        super(LoadBalancerAgentApi, self).__init__(
            topic, default_version=self.BASE_RPC_API_VERSION)
        self.db = loadbalancer_db.LoadBalancerPluginDb()
        self.nws_driver = importutils.import_object(nwservice_driver)
        self.listen_conn = rpc.create_connection(new=True)
        
    def _cast(self, context, method_name, method_args, host, version=None):
        pool_id = None
        if method_name == 'create_vip' or method_name == 'update_vip' or method_name == 'delete_vip':
            pool_id = method_args['vip']['pool_id']
        elif method_name == 'create_pool' or method_name == 'update_pool' or method_name == 'delete_pool':
            pool_id = method_args['pool']['id']
        elif method_name == 'create_member' or method_name == 'update_member' or method_name == 'delete_member':
            pool_id = method_args['member']['pool_id']
        elif method_name == 'create_pool_health_monitor' or method_name == 'update_pool_health_monitor' or method_name == 'delete_pool_health_monitor':
            pool_id = method_args['pool_id']
            
        if pool_id:
            pool_details = self.db.get_pool(context, pool_id)
            if pool_details['config_handle_id']:
                config_details = self.db.get_config_handle(context, pool_details['config_handle_id'])
                if config_details:
                    config_mode = config_details['config_mode']
                    if config_mode == 'NFV':
                        #Kill Haproxy in Network Node, if mode is NFV
                        topic_name = '%s.%s' % (self.topic, host)
                        self.listen_conn.join_consumer_pool(None,topic_name,topic_name,'crd')
                        pool = {'id': pool_id}
                        self.cast(
                            context,
                            self.make_msg('delete_pool', pool=pool),
                            topic='%s.%s' % (self.topic, host),
                            version=version
                        )
                        
                        #Send to Relay Agent
                        self.prepare_update(pool_details['config_handle_id'], constants.LB_UPDATE)
                    elif config_mode == 'NN':
                        print "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"
                        print "Sending Cast to Loadbalancer Agent...."
                        print str(method_name)
                        print str(method_args)
                        print str(self.topic)
                        print str(context)
                        print str(host)
                        print str(context.to_dict())
                        print "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"
                        
                        #Create instance_mapping entry for the respective pool
                        topic_name = '%s.%s' % (self.topic, host)
                        self.listen_conn.join_consumer_pool(None,topic_name,topic_name,'crd')
                        if method_name != 'create_pool':
                            pool = {'driver_name':'haproxy_ns', 'pool': pool_details}
                            self.cast(
                                context,
                                self.make_msg('create_pool', **pool),
                                topic='%s.%s' % (self.topic, host),
                                version=version
                            )
                            
                        #Send RPC Notification to neutron-lbaas-agent
                        return self.cast(
                            context,
                            self.make_msg(method_name, **method_args),
                            topic='%s.%s' % (self.topic, host),
                            version=version
                        )
                    elif config_mode == 'OFC':
                        #Need to handle CRD Consumer Notifier
                        pass
            else:
                print "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"
                print "Sending Cast to Loadbalancer Agent...."
                print str(method_name)
                print str(method_args)
                print str(self.topic)
                print str(context)
                print str(host)
                print str(context.to_dict())
                print "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"
                topic_name = '%s.%s' % (self.topic, host)
                self.listen_conn.join_consumer_pool(None,topic_name,topic_name,'crd')
                
                #Create instance_mapping entry for the respective pool
                if method_name != 'create_pool':
                    pool = {'driver_name':'haproxy_ns', 'pool': pool_details}
                    self.cast(
                        context,
                        self.make_msg('create_pool', **pool),
                        topic='%s.%s' % (self.topic, host),
                        version=version
                    )
                    
                #Send RPC Notification to neutron-lbaas-agent
                return self.cast(
                    context,
                    self.make_msg(method_name, **method_args),
                    topic='%s.%s' % (self.topic, host),
                    version=version
                )
                LOG.error("Config Handle NOT Mapped!!!")

    def create_vip(self, context, vip, host):
        return self._cast(context, 'create_vip', {'vip': vip}, host)

    def update_vip(self, context, old_vip, vip, host):
        return self._cast(context, 'update_vip',
                          {'old_vip': old_vip, 'vip': vip}, host)

    def delete_vip(self, context, vip, host):
        return self._cast(context, 'delete_vip', {'vip': vip}, host)

    def create_pool(self, context, pool, host, driver_name):
        return self._cast(context, 'create_pool',
                          {'pool': pool, 'driver_name': driver_name}, host)

    def update_pool(self, context, old_pool, pool, host):
        return self._cast(context, 'update_pool',
                          {'old_pool': old_pool, 'pool': pool}, host)

    def delete_pool(self, context, pool, host):
        return self._cast(context, 'delete_pool', {'pool': pool}, host)

    def create_member(self, context, member, host):
        return self._cast(context, 'create_member', {'member': member}, host)

    def update_member(self, context, old_member, member, host):
        return self._cast(context, 'update_member',
                          {'old_member': old_member, 'member': member}, host)

    def delete_member(self, context, member, host):
        return self._cast(context, 'delete_member', {'member': member}, host)

    def create_pool_health_monitor(self, context, health_monitor, pool_id,
                                   host):
        return self._cast(context, 'create_pool_health_monitor',
                          {'health_monitor': health_monitor,
                           'pool_id': pool_id}, host)

    def update_pool_health_monitor(self, context, old_health_monitor,
                                   health_monitor, pool_id, host):
        return self._cast(context, 'update_pool_health_monitor',
                          {'old_health_monitor': old_health_monitor,
                           'health_monitor': health_monitor,
                           'pool_id': pool_id}, host)

    def delete_pool_health_monitor(self, context, health_monitor, pool_id,
                                   host):
        return self._cast(context, 'delete_pool_health_monitor',
                          {'health_monitor': health_monitor,
                           'pool_id': pool_id}, host)

    def agent_updated(self, context, admin_state_up, host):
        return self._cast(context, 'agent_updated',
                          {'payload': {'admin_state_up': admin_state_up}},
                          host)
    
    def prepare_update(self, config_handle_id, method):
        #LOG.debug(_("Firewall Config Handle ID => %s"),(str(config_handle_id)))
        if config_handle_id:
            update_dict = { "header":"request",
                        "config_handle_id":config_handle_id,
                        "slug":"loadbalancer",
                        "version":"0.0",
                      }
            #LOG.debug(_("Notification Data : %s" % str(update_dict)))
            self.send_modified_notification(config_handle_id, {'config':update_dict})
        return

    def send_modified_notification(self, config_handle_id, notify_data):
        #LOG.debug(_('Send modified notification to NS Driver: Data: %s' % str(notify_data)))
        self.nws_driver.send_rpc_msg(config_handle_id,notify_data)
    
    ###This is only for NFV Mode: KILL Namespace Haproxy process in Network Node
    def _undeploy_instance(self, pool_id):
        namespace = get_ns_name(pool_id)
        ns = ip_lib.IPWrapper('sudo', namespace)
        pid_path = self._get_state_file_path(pool_id, 'pid')

        # kill the process
        print "***************************"
        print str(pid_path)
        print "***************************"
        kill_pids_in_file('sudo', pid_path)
        
    def _get_state_file_path(self, pool_id, kind, ensure_state_dir=True):
        """Returns the file name for a given kind of config file."""
        state_path = '/var/lib/neutron/lbaas'
        confs_dir = os.path.abspath(os.path.normpath(state_path))
        conf_dir = os.path.join(confs_dir, pool_id)
        if ensure_state_dir:
            if not os.path.isdir(conf_dir):
                os.makedirs(conf_dir, 0o755)
        return os.path.join(conf_dir, kind)


class AgentDriverBase(abstract_driver.LoadBalancerAbstractDriver):

    # name of device driver that should be used by the agent;
    # vendor specific plugin drivers must override it;
    device_driver = None

    def __init__(self, plugin):
        if not self.device_driver:
            raise DriverNotSpecified()

        self.agent_rpc = LoadBalancerAgentApi(topics.LOADBALANCER_AGENT)

        self.plugin = plugin
        self._set_callbacks_on_plugin()
        self.plugin.agent_notifiers.update(
            {q_const.AGENT_TYPE_LOADBALANCER: self.agent_rpc})

        #self.pool_scheduler = importutils.import_object(
        #    cfg.CONF.loadbalancer_pool_scheduler_driver)

    def _set_callbacks_on_plugin(self):
        # other agent based plugin driver might already set callbacks on plugin
        if hasattr(self.plugin, 'agent_callbacks'):
            return

        self.plugin.agent_callbacks = LoadBalancerCallbacks(self.plugin)
        self.plugin.conn = rpc.create_connection(new=True)
        self.plugin.conn.create_consumer(
            topics.LOADBALANCER_PLUGIN,
            self.plugin.agent_callbacks.create_rpc_dispatcher(),
            fanout=False)
        self.plugin.conn.consume_in_thread()

    def get_pool_agent(self, context, pool_id):
        #agent = self.plugin.get_lbaas_agent_hosting_pool(context, pool_id)
        nc = self.neutronclient(context)
        agent = nc.get_lbaas_agent_hosting_pool(pool_id)
        if not agent:
            raise lbaas_agentscheduler.NoActiveLbaasAgent(pool_id=pool_id)
        return agent['agent']

    def create_vip(self, context, vip):
        agent = self.get_pool_agent(context, vip['pool_id'])
        self.agent_rpc.create_vip(context, vip, agent['host'])

    def update_vip(self, context, old_vip, vip):
        agent = self.get_pool_agent(context, vip['pool_id'])
        if vip['status'] in constants.ACTIVE_PENDING_STATUSES:
            self.agent_rpc.update_vip(context, old_vip, vip, agent['host'])
        else:
            self.agent_rpc.delete_vip(context, vip, agent['host'])

    def delete_vip(self, context, vip):
        self.plugin._delete_db_vip(context, vip['id'])
        agent = self.get_pool_agent(context, vip['pool_id'])
        self.agent_rpc.delete_vip(context, vip, agent['host'])

    def create_pool(self, context, pool):
        #agent = self.pool_scheduler.schedule(self.plugin, context, pool,
        #                                     self.device_driver)
        #agent = self.schedule(self.plugin, context, pool,
        #                                     self.device_driver)
        agent = self.get_pool_agent(context, pool['id'])
        if not agent:
            raise lbaas_agentscheduler.NoEligibleLbaasAgent(pool_id=pool['id'])
        self.agent_rpc.create_pool(context, pool, agent['host'],
                                   self.device_driver)

    def update_pool(self, context, old_pool, pool):
        agent = self.get_pool_agent(context, pool['id'])
        if pool['status'] in constants.ACTIVE_PENDING_STATUSES:
            self.agent_rpc.update_pool(context, old_pool, pool,
                                       agent['host'])
        else:
            self.agent_rpc.delete_pool(context, pool, agent['host'])

    def delete_pool(self, context, pool):
        # get agent first to know host as binding will be deleted
        # after pool is deleted from db
        #agent = self.plugin.get_lbaas_agent_hosting_pool(context, pool['id'])
        nc = self.neutronclient(context)
        agent = nc.get_lbaas_agent_hosting_pool(pool['id'])
        self.plugin._delete_db_pool(context, pool['id'])
        if agent:
            self.agent_rpc.delete_pool(context, pool, agent['agent']['host'])

    def create_member(self, context, member):
        agent = self.get_pool_agent(context, member['pool_id'])
        self.agent_rpc.create_member(context, member, agent['host'])

    def update_member(self, context, old_member, member):
        agent = self.get_pool_agent(context, member['pool_id'])
        # member may change pool id
        if member['pool_id'] != old_member['pool_id']:
            #old_pool_agent = self.plugin.get_lbaas_agent_hosting_pool(
            #    context, old_member['pool_id'])
            nc = self.neutronclient(context)
            old_pool_agent = nc.get_lbaas_agent_hosting_pool(old_member['pool_id'])
            if old_pool_agent:
                self.agent_rpc.delete_member(context, old_member,
                                             old_pool_agent['agent']['host'])
            self.agent_rpc.create_member(context, member, agent['host'])
        else:
            self.agent_rpc.update_member(context, old_member, member,
                                         agent['host'])

    def delete_member(self, context, member):
        self.plugin._delete_db_member(context, member['id'])
        agent = self.get_pool_agent(context, member['pool_id'])
        self.agent_rpc.delete_member(context, member, agent['host'])

    def create_pool_health_monitor(self, context, healthmon, pool_id):
        # healthmon is not used here
        agent = self.get_pool_agent(context, pool_id)
        self.agent_rpc.create_pool_health_monitor(context, healthmon,
                                                  pool_id, agent['host'])

    def update_pool_health_monitor(self, context, old_health_monitor,
                                   health_monitor, pool_id):
        agent = self.get_pool_agent(context, pool_id)
        self.agent_rpc.update_pool_health_monitor(context, old_health_monitor,
                                                  health_monitor, pool_id,
                                                  agent['host'])

    def delete_pool_health_monitor(self, context, health_monitor, pool_id):
        self.plugin._delete_db_pool_health_monitor(
            context, health_monitor['id'], pool_id
        )

        agent = self.get_pool_agent(context, pool_id)
        self.agent_rpc.delete_pool_health_monitor(context, health_monitor,
                                                  pool_id, agent['host'])

    def stats(self, context, pool_id):
        pass
    
    def neutronclient(self, context):
        c = neutron_client.Client(
            username=cfg.CONF.nscs_authtoken.admin_user,
            password=cfg.CONF.nscs_authtoken.admin_password,
            tenant_name=cfg.CONF.nscs_authtoken.admin_tenant_name,
            auth_url=cfg.CONF.nscs_authtoken.auth_url,
            auth_strategy='keystone',
        )
        return c
    
    def url_for(self, context, service_type, admin=False, endpoint_type=None):
        endpoint_type = endpoint_type or 'publicURL'
        catalog = context.service_catalog
        service = self.get_service_from_catalog(catalog, service_type)
        if service:
            try:
                if admin:
                    return service['endpoints'][0]['adminURL']
                else:
                    return service['endpoints'][0][endpoint_type]
            except (IndexError, KeyError):
                raise n_exc.ServiceCatalogException(service_name=str(service_type))
        else:
            raise n_exc.ServiceCatalogException(service_name=str(service_type))
            
    def get_service_from_catalog(self, catalog, service_type):
        if catalog:
            for service in catalog:
                if service['type'] == service_type:
                    return service
        return None


def get_ns_name(namespace_id):
    return NS_PREFIX + namespace_id

def kill_pids_in_file(root_helper, pid_path):
    if os.path.exists(pid_path):
        with open(pid_path, 'r') as pids:
            for pid in pids:
                pid = pid.strip()
                try:
                    utils.execute(['kill', '-9', pid], root_helper)
                except RuntimeError:
                    LOG.exception(
                        _('Unable to kill haproxy process: %s'),
                        pid
                    )
