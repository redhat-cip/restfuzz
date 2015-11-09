#!/usr/bin/python

import requests


class Api:
    # Wrapper around requests
    def __init__(self):
        self.headers = {'User-Agent': 'restfuzz-0.1.0', 'Accept': 'application/json'}

    def set_header(self, k, v):
        self.headers[k] = v

    def request(self, http_method, endpoint, data, content_type = 'application/json'):
        self.headers['Content-Type'] = content_type
        try:
            return requests.request(http_method, url=endpoint, headers=self.headers, data=data)
        except:
            print "[E] Could not call %s %s with [%s]" % (http_method, endpoint, data)
            raise
