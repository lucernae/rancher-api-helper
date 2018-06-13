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

        stack_id = os.environ.get('RANCHER_TARGET_STACK_ID')

        target_image_id = None
        if 'RANCHER_TARGET_IMAGE_ID' in os.environ:
            target_image_id = os.environ.get('RANCHER_TARGET_IMAGE_ID')

        if project_id:
            print 'Project ID: {0}'.format(project_id)

        print 'Stack ID: {0}'.format(stack_id)
        stack = api.stacks(stack_id)
        stack.upgrade()
        print stack.state
        print 'Waiting upgrade process'
        stack.wait_valid_state()
        print 'Upgraded. Finishing upgrade process.'
        stack.finish_upgrade()
        stack.wait_valid_state()
        print 'Upgrade finished'
        print stack.state
        print

        if target_image_id:
            print 'Attempt to upgrade service with this image: {0}'.format(target_image_id)
            stack.upgrade_service_for_image(target_image_id)
            print 'Upgrade finished'

        sys.exit(0)
    except BaseException as e:
        print e
        raise
