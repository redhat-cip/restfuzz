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

import requests


class Api:
    # Wrapper around requests
    def __init__(self):
        self.headers = {
            'User-Agent': 'restfuzz-0.1.0',
            'Accept': 'application/json'}

    def set_header(self, k, v):
        self.headers[k] = v

    def request(self, http_method, endpoint, data,
                content_type='application/json'):
        self.headers['Content-Type'] = content_type
        return requests.request(
            http_method, url=endpoint, headers=self.headers, data=data)
