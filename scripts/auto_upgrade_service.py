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

        # Use the new image version
        # Replace image being used in service RANCHER_TARGET_SERVICE_ID
        # into RANCHER_NEW_IMAGE_UUID
        # Useful for upgrading new releases.
        new_image_uuid = os.environ.get('RANCHER_NEW_IMAGE_UUID')
        if new_image_uuid:
            service.resource['upgrade']['inServiceStrategy'][
                'launchConfig']['imageUuid'] = new_image_uuid

        service.upgrade()
        print service.state
        print 'Waiting upgrade process'
        service.wait_valid_state()
        print 'Upgraded. Finishing upgrade process.'
        service.finish_upgrade()
        service.wait_valid_state()
        print 'Upgrade finished'
        print service.state
        print

        sys.exit(0)
    except BaseException as e:
        print e
        raise
