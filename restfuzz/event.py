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

import time
import cPickle as pickle


class Event(object):
    # Contains all the information about a method call
    def __init__(self, name=None, method=None, url=None, json_input=None, inputs=None, data=None):
        if data:
            self.__dict__ = data
            return
        self.start_time = time.time()
        self.name = name
        self.method = method
        self.url = url
        self.json_input = json_input
        self.json_output = None
        self.inputs = inputs
        self.outputs = None
        self.elapsed = 0
        self.code = -1
        self.tracebacks = []
        self.resources = None

    def get(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

    def set_resp(self, resp):
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time
        self.code = resp.status_code
        self.json_output = resp.text

    def render(self, color=''):
        def strip(txt):
            if not txt:
                return txt
            txt = filter(lambda x: ord(x) >= 32 and ord(x) < 127, txt)
            return txt
        ftime = "%s.%03.0f" % (
            time.strftime("%Y-%m-%d %H:%M:%S"),
            (self.start_time - int(self.start_time)) * 1000
        )
        tb = ""
        new_tb = []
        for t in self.tracebacks:
            if "uniq_tb" in t:
                new_tb.append(t["uniq_tb"])
            tb += ", %s" % t["tb_id"]
        if new_tb:
            new_tb = "\n%s" % "\n".join(new_tb)
        else:
            new_tb = ""
        return "[%s] \033[93m%s\033[0m: %s%d| curl -X %4s %s\033[0m -d '%s' -> '%s'%s%s" % (
            ftime, self.name, color,
            self.code, self.method, strip(self.url),
            strip(self.json_input), strip(self.json_output),
            tb, new_tb
        )

    def __str__(self):
        return self.render()

    def __repr__(self):
        return str(self)


class EventDb:
    def __init__(self, db_file):
        self.db = db_file

    def __del__(self):
        self.db.close()

    def append(self, event):
        pickle.dump(event.__dict__, self.db)

    def list(self):
        self.db.seek(0)
        try:
            while True:
                try:
                    e = pickle.load(self.db)
                    yield Event(data = e)
                except Exception, e:
                    print "[+] could not pickle.load at offset", self.db.tell(), e
                    break
        except EOFError:
            pass
