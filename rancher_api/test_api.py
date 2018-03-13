# coding=utf-8

import unittest

import os

from rancher_api.api_endpoint import APIEndpoint


class TestAPIAccess(unittest.TestCase):

    def setUp(self):
        access_key = os.environ.get('ACCESS_KEY')
        secret_key = os.environ.get('SECRET_KEY')
        base_url = os.environ.get('API_BASE_URL')

        self.api = APIEndpoint(base_url, access_key, secret_key)

    def test_stack_upgrade(self):
        stack = self.api.stacks('1st467')
        print stack.state
        stack.upgrade()
        print stack.state
        stack.wait_valid_state()
        stack.refresh()
        print stack.state

    def test_stack_finish_upgrade(self):
        stack = self.api.stacks('1st467')
        print stack.state
        stack.finish_upgrade()
        print stack.state
        stack.wait_valid_state()
        stack.refresh()
        print stack.state
