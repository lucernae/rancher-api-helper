#!/usr/bin/env python
# coding=utf-8
import os

import sys

from rancher_api.api_endpoint import APIEndpoint

if __name__ == '__main__':

    try:

        rancher_base_url = os.environ.get('RANCHER_BASE_URL')
        access_key = os.environ.get('RANCHER_ACCESS_KEY')
        secret_key = os.environ.get('RANCHER_SECRET_KEY')
        project_id = os.environ.get('RANCHER_PROJECT_ID')
        api = APIEndpoint(
            rancher_base_url, access_key, secret_key,
            use_account_api=bool(project_id),
            project_id=project_id)

        service_id = os.environ.get('RANCHER_TARGET_SERVICE_ID')
        print 'Service ID: {0}'.format(service_id)
        service = api.services(service_id)

        command = os.environ.get('RANCHER_TARGET_SERVICE_COMMAND')
        print 'Command to execute in containers:'
        print command

        for c in service.instances:
            container = c
            """:type container: rancher_api.api_endpoint.ContainerResource"""
            container.execute(command=command)
        sys.exit(0)
    except BaseException as e:
        print e
        raise
