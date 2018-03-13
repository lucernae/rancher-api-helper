# coding=utf-8

import unittest

import os

from rancher_api.api_endpoint import APIEndpoint


class TestAPIAccess(unittest.TestCase):

    def setUp(self):
        access_key = os.environ.get('RANCHER_ACCESS_KEY')
        secret_key = os.environ.get('RANCHER_SECRET_KEY')
        base_url = os.environ.get('RANCHER_BASE_URL')
        self.stack_id = os.environ.get('RANCHER_TARGET_STACK_ID')

        self.api = APIEndpoint(base_url, access_key, secret_key)

    def test_stack_upgrade(self):
        stack = self.api.stacks(self.stack_id)
        print stack.state
        stack.upgrade()
        print stack.state
        stack.wait_valid_state()
        stack.refresh()
        print stack.state

    def test_stack_finish_upgrade(self):
        stack = self.api.stacks(self.stack_id)
        print stack.state
        stack.finish_upgrade()
        print stack.state
        stack.wait_valid_state()
        stack.refresh()
        print stack.state
