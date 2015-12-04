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

import os
import restfuzz.health


class Health:
    SERVICES=("neutron", "glance", "cinder")

    def __init__(self):
        self.log_files = {}

        for service in self.SERVICES:
            os.system("sudo chown :$USER /var/log/%s" % service)
            os.system("sudo chmod 750 /var/log/%s" % service)

        self.uniq_tb = set()

    def open_logs(self):
        for service in self.SERVICES:
            for fn in os.listdir("/var/log/%s" % service):
                fp = "%s/%s" % (service, fn)
                if fp in self.log_files:
                    continue
                st = os.stat("/var/log/%s" % fp)
                if st.st_gid != os.getgid():
                    os.system("sudo chown %d:%d /var/log/%s" % (
                        st.st_uid, os.getgid(), fp))
                self.log_files[fp] = open("/var/log/%s" % fp)
                self.log_files[fp].seek(0, 2)

    def check(self):
        self.open_logs()
        for lf in self.log_files.values():
            while True:
                t = restfuzz.health.collect_traceback(lf)
                if not t:
                    break
                tb_hash, tb_id, tb = t
                if tb_hash not in self.uniq_tb:
                    self.uniq_tb.add(tb_hash)
                    yield {"tb_id": tb_id, "tb_hash": tb_hash, "uniq_tb": tb}
                else:
                    # known tb, don't yield full trace
                    yield {"tb_id": tb_id, "tb_hash": tb_hash}
