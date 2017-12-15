# Copyright 2017 Red Hat
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
from io import StringIO

from restfuzz.os_api_ref_importer import OsApiRefFile


FakeOsApiRef = """
Show network details
====================

.. rest_method::  GET /v2.0/networks/{network_id}

Shows details for a network.

Request
-------

.. rest_parameters:: parameters.yaml

   - network_id: network_id-path
"""

FakeOsApiRefParameters = {
    "network_id-path": {
        'in': 'path',
        'required': True,
        'type': 'string',
    }
}


class OsApiRefFileTest(unittest.TestCase):
    def setUp(self):
        fobj = StringIO(FakeOsApiRef)
        fobj.name = "test.inc"
        OsApiRefFile.parameters_db["parameters.yaml"] = FakeOsApiRefParameters
        self.oarf = OsApiRefFile(fobj)

    def test_load(self):
        self.assertEqual(len(self.oarf.methods), 1)

    def test_render(self):
        methods = self.oarf.render()
        self.assertIn("show_network_details", methods)
