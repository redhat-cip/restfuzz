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


import json

API_DIR = "%s/api" % (__file__[:__file__.index('/restfuzz/tests')])


class FakeApi:
    def __init__(self, resp_content=None, resp_code=200):
        self.text = resp_content
        self.status_code = resp_code

    def request(self, method, endpoint, data, content_type = ''):
        class FakeRequest:
            status_code = self.status_code
            text = self.text

            def json(self):
                return json.loads(self.text)
        return FakeRequest()
