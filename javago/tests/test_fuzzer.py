#!/usr/bin/python

import unittest
import time
import javago.method

from javago.tests.utils import API_DIR, FakeApi
from javago.fuzzer import ApiRandomCaller


class FuzzerTests(unittest.TestCase):
    def test_api_random_caller(self, display=False):
        methods = javago.method.load_methods(API_DIR)
        api = FakeApi()
        fuzzer = ApiRandomCaller(api, methods)
        method_called = set()
        for i in xrange(10):
            event = fuzzer.step()
            self.assertTrue(len(event.url) > 5)
            method_called.add(event.name)
            if display:
                print event
                time.sleep(0.3)
        self.assertTrue(len(method_called) > 1)
        return

    def test_api_random_caller_ressouce_mgmt(self):
        methods = {
            'update': javago.method.Method({
                'name': 'update',
                'url': ['PUT', '%(resource_id)s.json'],
                'inputs': {'url_input': {'resource_id': {'type': 'resource', 'required': 'True'}}}
            }, base_url='http://localhost')
        }
        api = FakeApi(resp_code=404)
        fuzzer = ApiRandomCaller(api, methods, chaos_monkey=False)
        fuzzer.ig.resources['resource_id'] = ['aaaa-aa']
        event = fuzzer.step()
        # Test resources is used in url
        self.assertEquals(event.url, 'http://localhost/aaaa-aa.json')
        # Test resource is removed because api returned 404
        self.assertEquals(len(fuzzer.ig.resources), 0)

        methods = {
            'delete': javago.method.Method({
                'name': 'delete',
                'url': ['DELETE', '%(resource_id)s.json'],
                'inputs': {'url_input': {'resource_id': {'type': 'resource', 'required': 'True'}}}
            }, base_url='http://localhost')
        }
        api = FakeApi(resp_code=200)
        fuzzer = ApiRandomCaller(api, methods, chaos_monkey=False)
        fuzzer.ig.resources['resource_id'] = ['aaaa-aa']
        # Test resource is removed because DELETE method called
        fuzzer.step()
        self.assertEquals(len(fuzzer.ig.resources), 0)

        methods = {
            'resource_list': javago.method.Method({
                'name': 'resource_list',
                'url': ['GET', 'list.json'],
                'outputs': {'resource_id': {'type': 'resource', 'json_extract': 'lambda x: [i["id"] for i in x]'}}
            }, base_url='http://localhost'),
            'delete': javago.method.Method({
                'name': 'delete',
                'url': ['DELETE', '%(resource_id)s.json'],
                'inputs': {'url_input': {'resource_id': {'type': 'resource', 'required': 'True'}}}
            }, base_url='http://localhost')
        }
        api = FakeApi(resp_content='[{"id": "41"}, {"id": "43"}]', resp_code=200)
        fuzzer = ApiRandomCaller(api, methods, chaos_monkey=False)
        fuzzer.sync_resources()
        self.assertTrue('41' in fuzzer.ig.resources['resource_id'])

if __name__ == "__main__":
    t = FuzzerTests('test_api_random_caller')
    t.test_api_random_caller(True)