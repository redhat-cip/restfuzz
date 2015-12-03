#!/bin/env python
#
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

import random
from input_generator import InputGenerator


class ApiRandomCaller:
    def __init__(self, api, methods, chaos_monkey=True):
        self.api = api
        self.methods = methods
        self.methods_list = methods.values()
        self.ig = InputGenerator(chaos_monkey)

    def call(self, method, inputs=None):
        event = method.call(self.api, params=inputs)
        # Remove resources that results in a 404
        if event.code == 404 and 'url_input' in inputs:
            for input_name, input_value in inputs['url_input'].items():
                self.ig.resource_remove(input_name, input_value)
        # Remove resources that were deleted
        if method.http_method == 'DELETE' and event.code >= 200 and event.code < 300:
            for input_name, input_value in inputs['url_input'].items():
                self.ig.resource_remove(input_name, input_value)

        # Adds output to resources
        self.ig.resources_add(event.outputs)
        return event

    def step(self, ask_before_call=False):
        random.shuffle(self.methods_list)
        # Pick a callable method
        for method in self.methods_list:
            # Tries to avoid delete
            if method.http_method != 'DELETE' or self.ig.once_every(200):
                break
        # Generate inputs
        inputs = self.ig.generate_inputs(method.inputs)
        if ask_before_call:
            raw_input("\nPress enter to call %s (%s/%s) -d '%s' " % (method.name, method.base_url, method.url, inputs))
        return self.call(method, inputs)

    def sync_resources(self):
        # Refresh internal resources list
        tenant_id = self.ig.resources.setdefault('tenant_id', None)
        self.ig.resources_clear()
        if tenant_id:
            self.ig.resources["tenant_id"] = tenant_id
        for name, method in self.methods.items():
            if not name.endswith("_list"):
                continue
            event = method.call(self.api)
            # Adds output to resources
            self.ig.resources_add(event.outputs)
