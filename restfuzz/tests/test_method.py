# Copyright 2015 Red Hat
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import unittest
import restfuzz
from io import StringIO

import restfuzz.method
from restfuzz.tests.utils import FakeApi


class MethodTests(unittest.TestCase):
    def test_method_basic_call(self):
        method = restfuzz.method.Method({
            'name': 'test',
            'url': ['GET', 'list.json'],
        }, base_url='http://localhost:8080')
        self.assertTrue("test" in str(method))
        api = FakeApi()
        event = method.call(api)
        self.assertEquals(event.url, 'http://localhost:8080/list.json')

    def test_method_inputs(self):
        method = restfuzz.method.Method({
            'name': 'test',
            'url': ['POST', 'create.json'],
            'inputs': {'name': {'_type': 'string'}}
        }, base_url='http://localhost:8080')
        api = FakeApi()
        event = method.call(api, params={'name': 'test_name'})
        self.assertEquals(event.json_input, '{"name": "test_name"}')

    def test_method_outputs(self):
        method = restfuzz.method.Method({
            'name': 'test',
            'url': ['GET', 'list.json'],
            'outputs': {
                'id': {'_type': 'resource',
                       'json_extract': 'lambda x: x["id"]'},
            }
        }, base_url='http://localhost:8080')
        api = FakeApi(resp_content='{"id": "42"}')
        event = method.call(api)
        self.assertIsNotNone(event.outputs)
        self.assertEqual(event.outputs, {"id": ["42"]})

    def test_method_url_inputs(self):
        method = restfuzz.method.Method({
            'name': 'test',
            'url': ['PUT', '%(test)s.json'],
            'inputs': {
                'url_input': {'test': {'_type': 'string'}}
            }
        }, base_url='http://localhost:8080')
        api = FakeApi(resp_content='{"id": "42"}')
        event = method.call(api, {'url_input': {'typo': 42}})
        self.assertTrue("%(test)s" in event.url)
        event = method.call(api, {'url_input': {'test': 42}})
        self.assertTrue("42.json" in event.url)

    # Coverage test
    def test_load_yaml(self):
        methods = {}
        with self.assertRaises(RuntimeError):
            # missing methods
            restfuzz.method.load_yaml(StringIO("base_url: ''"), methods)
        with self.assertRaises(RuntimeError):
            # invalid inputs
            restfuzz.method.Method({'name': 'test', 'url': ['GET', 'none'],
                                    'inputs': {'test': []}}, base_url='none')
        # invalid json extract
        m = restfuzz.method.Method(
            {
                'name': 'test',
                'url': ['GET', 'none'],
                'inputs': {'net_id': {'_type': 'resource',
                                      'required': 'True'}},
                'outputs': {'test_id': {'_type': 'resource',
                                        'json_extract': 'lambda x: typo'}}
            }, base_url='none)')
        self.assertTrue(m.check_requirements({'net_id': 42}))
        self.assertFalse(m.check_requirements({'subnet_id': 42}))
        api = FakeApi(resp_content='{"id": "42"}')
        m.call(api)
