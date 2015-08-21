#!/usr/bin/python

import unittest
import javago.input_generator
import javago.method

from javago.tests.utils import API_DIR, FakeApi


class InputGeneratorTests(unittest.TestCase):
    def test_call_all_generator(self):
        # Make sure generator are working
        ig = javago.input_generator.InputGenerator()
        for input_type in ig.generator_list:
            self.assertIsNotNone(
                ig.generate(input_type)
            )
        with self.assertRaises(RuntimeError):
            ig.generate("unknown_type")

    def test_check_all_known_types_are_generated(self):
        methods = javago.method.load_methods(API_DIR)
        ig = javago.input_generator.InputGenerator()
        for method in methods.values():
            for k, v in method.iter_inputs():
                self.assertIsNotNone(
                    ig.generate_input(v["type"])
                )

    def test_generate_inputs(self):
        method = javago.method.Method({
            'name': 'test',
            'url': ['POST', 'create.json'],
            'inputs': {'obj': {'name': {'type': 'string', 'required': 'True'}}}
        }, base_url='http://localhost:8080')
        ig = javago.input_generator.InputGenerator()
        params = ig.generate_inputs(method.inputs)
        self.assertTrue('name' in params['obj'])

    def test_resources(self):
        ig = javago.input_generator.InputGenerator()
        outputs = {'net_id': ['aaaa-aa'], 'subnet_id': ['bbbb-bb', 'cccc-cc']}
        ig.resources_add(outputs)
        self.assertEquals(len(ig.resources['subnet_id']), 2)
        ig.resource_remove('subnet_id', 'cccc-cc')
        self.assertEquals(len(ig.resources['subnet_id']), 1)
        self.assertEquals(ig.gen_resource("subnet_id"), "bbbb-bb")
        ig.resource_remove('subnet_id', 'bbbb-bb')
        ig.resource_remove('wrong_id', 'aaaa-aa')
        ig.resources_clear()
        self.assertEquals(len(ig.resources), 0)

    def test_collect_and_use_resource(self):
        ig = javago.input_generator.InputGenerator(False)

        method = javago.method.Method({
            'name': 'list',
            'url': ['GET', 'list.json'],
            'outputs': {'id': {'json_extract': 'lambda x: [i["id"] for i in x]'}}
        }, base_url='http://localhost:8080')
        api = FakeApi(resp_content='[{"id": "42"}, {"id": "43"}]')
        event = method.call(api)
        ig.resources_add(event.outputs)

        method = javago.method.Method({
            'name': 'update',
            'url': ['PUT', 'put.json'],
            'inputs': {'id': {'type': 'resource', 'required': 'True'}}
        }, base_url='http://localhost:8080')
        params = ig.generate_inputs(method.inputs)
        self.assertTrue(params['id'] in ('42', '43'))

    def test_expand_input(self):
        ig = javago.input_generator.InputGenerator(False)
        method = javago.method.Method({
            'name': 'test',
            'url': ['POST', 'create.json'],
            'inputs': {'obj': {'name': {'type': 'record', 'expand': 'True', 'required': 'True'}}}
        }, base_url='http://localhost:8080')
        params = ig.generate_inputs(method.inputs)
        self.assertTrue("type" in params['obj'])
        self.assertTrue("records" in params['obj'])
