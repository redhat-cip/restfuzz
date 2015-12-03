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

# demo api server

import os
import time
import json
import random
import uuid
try:
    import web
except:
    raise RuntimeError("Demo server needs web.py (http://www.webpy.org)")

urls = (
    '/demo/(.*)', 'Demo'
)
web.config.debug = False
app = web.application(urls, globals())


ports = []
# create random object
for i in xrange(0, random.randint(1, 5)):
    ports.append({'id': str(uuid.uuid4()), 'name': 'port%d' % i})


class Demo:
    def GET(self, dummy):
        return json.dumps(ports)

    def PUT(self, port_name):
        if not port_name:
            return
        new_port = {'id': str(uuid.uuid4()), 'name': port_name}
        ports.append(new_port)
        return json.dumps(new_port)

    def POST(self, port_id):
        update_port = None
        for port in ports:
            if port_id == port['id']:
                update_port = port
                break
        if not update_port:
            return
        i = json.loads(web.data())
        for k,v in i.items():
            update_port[k] = v
        return json.dumps(update_port)

print "RestFuzz demo REST API server"
print "-----------------------------"
print ""
print "Run python ./bin/restfuzz.py --api ./demo/demo.yaml"
print

print "Listening on",
app.run()
