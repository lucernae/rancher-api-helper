# coding=utf-8
import ast
import json
import re
import time
from encodings.base64_codec import base64_decode

from hammock import Hammock
from websocket import WebSocketApp


class APIEndpoint(object):

    def __init__(self, rancher_base_url, access_key, secret_key,
                 use_account_api=False, project_id=None):
        super(APIEndpoint, self).__init__()

        self.rancher_base_url = rancher_base_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.use_account_api = use_account_api

        self.endpoint = Hammock(rancher_base_url)

        # endpoint starts from base/v2-beta
        self.endpoint = self.endpoint('v2-beta')

        # if it is an Account API access, you should provide project_id
        if use_account_api:
            if not project_id:
                raise Exception('missing project_id')
            self.endpoint = self.endpoint.projects(project_id)

    @property
    def auth_param(self):
        return self.access_key, self.secret_key

    @property
    def request_contexts(self):
        return {
            'auth': self.auth_param
        }

    def stacks(self, stack_id):
        """
        :param stack_id:
        :return:
        :rtype: StackResource
        """
        response = self.endpoint.stacks(stack_id).GET(**self.request_contexts)
        obj = response.json()
        return StackResource(self, obj)

    def services(self, service_id):
        """
        :param service_id:
        :return:
        :rtype: ServiceResource
        """
        response = self.endpoint.services(service_id).GET(**self.request_contexts)
        obj = response.json()
        return ServiceResource(self, obj)

    def containers(self, instance_id):
        """
        :param instance_id:
        :return:
        :rtype: ContainerResource
        """
        response = self.endpoint.containers(instance_id).GET(**self.request_contexts)
        obj = response.json()
        return ContainerResource(self, obj)

    def websocket(self, host_access, **kwargs):
        """
        :param host_access:
        :type host_access: HostAccess

        :return:
        """
        ws = BaseRancherWSApp(host_access=host_access)
        return ws


class BaseRancherWSApp(WebSocketApp):

    def __init__(self, host_access, **kwargs):
        """
        :param host_access:
        :type host_access: HostAccess
        :param kwargs:
        """
        url = '{url}?token={token}'.format(
            url=host_access.url, token=host_access.token)
        handlers = ['message', 'open', 'close', 'data', 'error']

        # set default handlers
        for h in handlers:
            handler_name = 'on_{}'.format(h)
            if 'on_{}'.format(h) not in kwargs:
                kwargs.update({
                    handler_name: getattr(self, handler_name)
                })

        super(BaseRancherWSApp, self).__init__(url=url, **kwargs)


    def on_message(ws, message):
        # Rancher message was encoded in utf-8 base64
        print base64_decode(message)[0]

    def on_close(ws):
        print 'WS Closed'

    def on_open(ws):
        print 'WS Opened'

    def on_data(ws, **kwargs):
        print 'Data'
        print kwargs

    def on_error(ws, error):
        print 'Error'
        print error


class RancherResource(object):

    STATE_ACTIVE = 'active'
    STATE_UPGRADING = 'upgrading'
    STATE_UPGRADED = 'upgraded'
    STATE_FINISHING_UPGRADE = 'finishing-upgreade'

    def __init__(self, api, resource):
        """a
        :param api:
        :type api: APIEndpoint

        :param resource:
        :type resource: dict
        """
        super(RancherResource, self).__init__()
        self.api = api
        self.resource = resource

    @property
    def id(self):
        return self.resource['id']

    @property
    def type(self):
        return self.resource['type']

    @property
    def state(self):
        return self.resource['state']


class HostAccess(RancherResource):

    def __init__(self, api, resource):
        super(HostAccess, self).__init__(api, resource)

    @property
    def url(self):
        return self.resource['url']

    @property
    def token(self):
        return self.resource['token']


class StackResource(RancherResource):

    def __init__(self, api, resource):
        super(StackResource, self).__init__(api, resource)

    @property
    def dockerCompose(self):
        return self.resource['dockerCompose']

    @property
    def rancherCompose(self):
        return self.resource['rancherCompose']

    @property
    def environment(self):
        return self.resource['environment']

    @property
    def externalId(self):
        return self.resource['externalId']

    @property
    def name(self):
        return self.resource['name']

    @property
    def answers(self):
        return self.resource['answers']

    @property
    def templates(self):
        return self.resource['templates']

    @property
    def serviceIds(self):
        return self.resource['serviceIds']

    @property
    def services(self):
        for service_id in self.serviceIds:
            yield self.api.services(service_id)

    def exportConfig(self):
        request_contexts = {
            'params': {
                'action': 'exportconfig'
            },
            'headers': {
                'content-type': 'application/json'
            }
        }
        request_contexts.update(self.api.request_contexts)
        response = self.api.endpoint.stacks(self.id).POST(**request_contexts)
        return response.json()

    def upgrade(self):
        # Get current compose config

        exportconfig_ret = self.exportConfig()

        data = {
            'answers': self.answers,
            'dockerCompose': exportconfig_ret['dockerComposeConfig'],
            'environment': self.environment,
            'externalId': self.externalId,
            'rancherCompose': exportconfig_ret['rancherComposeConfig'],
            'templates': self.templates
        }
        excluded_keys = []
        for key, value in data.iteritems():
            if not value:
                excluded_keys.append(key)

        for k in excluded_keys:
            data.pop(k)
        request_contexts = {
            'params': {
                'action': 'upgrade'
            },
            'headers': {
                'content-type': 'application/json'
            },
            'data': json.dumps(data)
        }
        request_contexts.update(self.api.request_contexts)
        response = self.api.endpoint.stacks(self.id).POST(**request_contexts)
        self.resource = response.json()

    def finish_upgrade(self):
        request_contexts = {
            'params': {
                'action': 'finishupgrade'
            }
        }
        request_contexts.update(self.api.request_contexts)
        response = self.api.endpoint.stacks(self.id).POST(**request_contexts)
        self.resource = response.json()

    def refresh(self):
        response = self.api.endpoint.stacks(self.id).GET(
            **self.api.request_contexts)
        self.resource = response.json()

    def wait_valid_state(self):
        while (
                not self.state == self.STATE_UPGRADED and
                not self.state == self.STATE_ACTIVE):
            time.sleep(20)
            self.refresh()

    def upgrade_service_for_image(self, image_name):
        """Auto upgrade all service in this service given an image_name used.

        """
        # Get key value pair of services and its image name in launch config
        image_used = {}
        for s_id in self.serviceIds:
            service = self.api.services(s_id)
            image_used[s_id] = service

            if service.imageUuid == image_name:
                service.upgrade()

        # Finishing upgrade services
        for s_id, service in image_used.iteritems():
            service.wait_valid_state()
            service.finish_upgrade()

    def upgrade_service_with_pattern(self, replace_what, replace_to):
        """Auto upgrade all services that matches pattern `replace what`.

        All matching services will be changed into `replace_to`

        :param replace_what: Regex pattern of image to replace
        :param replace_to: Image to replace
        """
        # We expect a raw literal string from replace_what, in case of regex
        try:
            pattern_string = ast.literal_eval(replace_what)
        except:
            pattern_string = replace_what
        pattern = re.compile(pattern_string)

        # Get key value pair of services and its image name in launch config
        image_used = {}
        for s_id in self.serviceIds:
            service = self.api.services(s_id)
            image_used[s_id] = service

            if pattern.search(service.imageUuid):
                launch_config = {
                    'imageUuid': replace_to
                }
                service.upgrade(launch_config=launch_config)

        # Finishing upgrade services
        for s_id, service in image_used.iteritems():
            service.wait_valid_state()
            service.finish_upgrade()


class ServiceResource(RancherResource):

    def __init__(self, api, resource):
        super(ServiceResource, self).__init__(api, resource)

    @property
    def launchConfig(self):
        return self.resource['launchConfig']

    @property
    def imageUuid(self):
        return self.launchConfig['imageUuid']

    @property
    def instanceIds(self):
        return self.resource['instanceIds']

    @property
    def instances(self):
        """
        :return:
        :rtype: list(ContainerResource)
        """
        for instance_id in self.instanceIds:
            yield self.api.containers(instance_id)

    def upgrade(self, launch_config=None):
        # Get current compose config

        try:
            data = {
                'inServiceStrategy': self.resource.get('upgrade', {}).get(
                    'inServiceStrategy', {})
            }
        except AttributeError:
            data = {
                'inServiceStrategy': {
                    'launchConfig': self.resource['launchConfig']
                }
            }
        excluded_keys = []
        for key, value in data.iteritems():
            if not value:
                excluded_keys.append(key)

        for k in excluded_keys:
            data.pop(k)

        # Change launch config
        launch_config_data = data['inServiceStrategy'].get('launchConfig', {})

        if not launch_config:
            launch_config = {}

        for k, v in launch_config.iteritems():
            launch_config_data[k] = v

        data['inServiceStrategy']['launchConfig'] = launch_config_data

        request_contexts = {
            'params': {
                'action': 'upgrade'
            },
            'headers': {
                'content-type': 'application/json'
            },
            'data': json.dumps(data)
        }
        request_contexts.update(self.api.request_contexts)
        response = self.api.endpoint.services(self.id).POST(**request_contexts)
        self.resource = response.json()

    def finish_upgrade(self):
        request_contexts = {
            'params': {
                'action': 'finishupgrade'
            }
        }
        request_contexts.update(self.api.request_contexts)
        response = self.api.endpoint.services(self.id).POST(**request_contexts)
        self.resource = response.json()

    def refresh(self):
        response = self.api.endpoint.services(self.id).GET(
            **self.api.request_contexts)
        self.resource = response.json()

    def wait_valid_state(self):
        while (
                not self.state == self.STATE_UPGRADED and
                not self.state == self.STATE_ACTIVE):
            time.sleep(20)
            self.refresh()


class ContainerResource(RancherResource):

    def __init__(self, api, resource):
        super(ContainerResource, self).__init__(api, resource)

    @property
    def name(self):
        return self.resource['name']

    @property
    def serviceIds(self):
        return self.resource['serviceIds']

    def restart(self):
        request_contexts = {
            'params': {
                'action': 'restart'
            }
        }
        request_contexts.update(self.api.request_contexts)
        response = self.api.endpoint.containers(self.id).POST(
            **request_contexts)
        self.resource = response.json()

    def start(self):
        request_contexts = {
            'params': {
                'action': 'start'
            }
        }
        request_contexts.update(self.api.request_contexts)
        response = self.api.endpoint.containers(self.id).POST(
            **request_contexts)
        self.resource = response.json()

    def stop(self):
        request_contexts = {
            'params': {
                'action': 'stop'
            }
        }
        request_contexts.update(self.api.request_contexts)
        response = self.api.endpoint.containers(self.id).POST(
            **request_contexts)
        self.resource = response.json()

    def execute(self, command, attach_stdin=True, attach_stdout=True, tty=True):
        if not isinstance(command, list):
            command = command.split(' ')
        data = {
            'attachStdin': attach_stdin,
            'attachStdout': attach_stdout,
            'tty': tty,
            'command': command
        }
        # data = {
        #     'follow': True,
        #     'lines': 100
        # }
        request_contexts = {
            'params': {
                'action': 'execute'
                # 'action': 'logs'
            },
            'headers': {
                'content-type': 'application/json'
            },
            'data': json.dumps(data)
        }
        request_contexts.update(self.api.request_contexts)
        response = self.api.endpoint.containers(self.id).POST(
            **request_contexts)
        host_access = response.json()
        host_access = HostAccess(self.api, host_access)

        ws = self.api.websocket(host_access)
        ws.run_forever()
