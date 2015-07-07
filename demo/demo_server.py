#!/usr/bin/python
# demo api server

import web
import json
import time

urls = ('/', 'demo')
web.config.debug = False
app = web.application(urls, globals())

class demo:
    def POST(self):
        time.sleep(1)
        i = json.loads(web.data())
        if i['direction'] == 'ingress':
            port = 1
        elif i['direction'] == 'egress':
            port = 2
        return json.dumps({'port_id': port})

if __name__ == "__main__":
    app.run()
