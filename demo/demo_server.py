#!/bin/env python3
#
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

import random
import uuid

from aiohttp import web


class Server:
    ports = []

    def __init__(self):
        # create random object
        for i in range(0, random.randint(1, 5)):
            self.ports.append({'id': str(uuid.uuid4()), 'name': 'port%d' % i})

    async def port_list(self, request):
        return web.json_response(self.ports)

    async def port_create(self, request):
        port_name = request.match_info["port"]
        if not port_name:
            raise web.HTTPNotFound()
        new_port = {'id': str(uuid.uuid4()), 'name': port_name}
        self.ports.append(new_port)
        return web.json_response(new_port)

    async def port_update(self, request):
        port_name = request.match_info["port"]
        ports = [port for port in self.ports if port['id'] == port_name]
        if not ports:
            raise web.HTTPNotFound()
        port = ports[0]
        json = await request.json()
        for k, v in json.items():
            port[k] = v
        return web.json_response(port)

    def run(self):
        app = web.Application()
        app.router.add_get('/demo/', self.port_list)
        app.router.add_put('/demo/{port}', self.port_create)
        app.router.add_post('/demo/{port}', self.port_update)
        web.run_app(app, port=8080)


print("RestFuzz demo REST API server")
print("-----------------------------")
print("")
print("Run restfuzz --api ./demo/demo.yaml --verbose --debug")
print()
Server().run()
