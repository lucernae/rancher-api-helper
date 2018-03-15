# coding=utf-8
import json
import threading

import time
from hammock import Hammock


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
        response = self.endpoint.stacks(stack_id).GET(**self.request_contexts)
        obj = response.json()
        return StackResource(self, obj)

    def services(self, service_id):
        response = self.endpoint.services(service_id).GET(**self.request_contexts)
        obj = response.json()
        return ServiceResource(self, obj)


class RancherResource(object):

    STATE_ACTIVE = 'active'
    STATE_UPGRADING = 'upgrading'
    STATE_UPGRADED = 'upgraded'
    STATE_FINISHING_UPGRADE = 'finishing-upgreade'

    def __init__(self, api, resource):
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


class ServiceResource(RancherResource):

    def __init__(self, api, resource):
        super(ServiceResource, self).__init__(api, resource)

    @property
    def launchConfig(self):
        return self.resource['launchConfig']

    @property
    def imageUuid(self):
        return self.launchConfig['imageUuid']

    def upgrade(self):
        # Get current compose config

        data = {
            'inServiceStrategy': self.resource['upgrade']['inServiceStrategy']
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
