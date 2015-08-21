#!/bin/env python
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

print "Javago demo REST API server"
print "---------------------------"
print ""
print "Run python ./bin/javago.py --api ./demo/demo.yaml"
print

print "Listening on",
app.run()
