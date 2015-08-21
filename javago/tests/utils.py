#!/usr/bin/python

import json

API_DIR = "%s/api" % (__file__[:__file__.index('/javago/tests')])


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
