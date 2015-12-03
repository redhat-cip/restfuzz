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
import os
import restfuzz.health
from restfuzz.event import Event as Ev
import glob


class Health:
    def __init__(self):
        os.system("sudo cgcreate -g memory,cpuacct:/glance")
        glance_pid = set()
        for i in glob.glob("/sys/fs/cgroup/*/*/*glance*.service/tasks"):
            for l in open(i).readlines():
                glance_pid.add(int(l))
        np = " ".join(map(str, glance_pid))
        print "[=] Adding to glance cgroup", np
        os.system("sudo cgclassify -g memory,cpuacct:/glance %s" % np)

        self.cpu_file = glob.glob("/sys/fs/cgroup/*/glance/cpuacct.stat")[0]
        self.mem_file = glob.glob("/sys/fs/cgroup/*/glance/memory.usage_in_bytes")[0]

        self.log_files = {}

        os.system("sudo chown -R 1000:glance /var/log/glance")
        os.system("sudo chmod -R 770 /var/log/glance")

        self.uniq_tb = set()

    def open_logs(self):
        for fn in os.listdir("/var/log/glance"):
            if fn in self.log_files:
                continue
            self.log_files[fn] = open("/var/log/glance/%s" % fn)
            self.log_files[fn].seek(0, 2)

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
                    yield ("tb", {"hash": tb_hash, "id": tb_id, "tb": tb})
                else:
                    # known tb, don't yield full trace
                    yield ("tb", {"hash": tb_hash, "id": tb_id})

        cpu = open(self.cpu_file).read().split()
        mem = int(open(self.mem_file).read())
        user_cpu, system_cpu = int(cpu[1]), int(cpu[3])
        yield ("res", {"uc": user_cpu, "us": system_cpu, "mem": mem})
