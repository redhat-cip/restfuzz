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

import argparse
import os
import gzip
import time
from sys import stdout

import method
from api import Api
from fuzzer import ApiRandomCaller
from event import EventDb


def do_restfuzz():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", nargs='+', metavar="file_or_dir", help="Api description", required=True)
    parser.add_argument("--token", help="X-Auth-Token to use")
    parser.add_argument("--tenant_id", nargs='+', default=[], help="Adds tenant ids")
    parser.add_argument("--db", help="File path to store event in")
    parser.add_argument("--health", help="Python module path to call after each call")
    parser.add_argument("--debug", action="store_const", const=True)
    parser.add_argument("--verbose", action="store_const", const=True)
    parser.add_argument("--seed", help="PRNG seed")
    parser.add_argument("--max_events", help="Maximum number of event", default=1e6, type=int)
    parser.add_argument("--max_time", help="Maximum running time", default=3600 * 12, type=int)

    args = parser.parse_args()

    def verbose(msg):
        if args.verbose:
            print msg

    methods = {}
    for api in args.api:
        api_methods = method.load_methods(api)
        methods.update(api_methods)

    api = Api()
    if args.token:
        api.set_header("X-Auth-Token", args.token)

    fuzzer = ApiRandomCaller(api, methods, args.seed)
    if args.db:
        db = EventDb(open(args.db, "w"))

    health = None
    if args.health:
        import imp
        health = imp.load_source('health', args.health).Health()

    for tenant_id in args.tenant_id:
        fuzzer.ig.resource_add("tenant_id", tenant_id)

    def refresh_keystone_token():
        token, tenant_id = os.popen("openstack token issue | grep ' id\|project_id' | awk '{ print $4 }'").read().split()
        api.set_header("X-Auth-Token", token)
        fuzzer.ig.resource_add("tenant_id", tenant_id)
        fuzzer.sync_resources()
        return token, tenant_id

    if "OS_USERNAME" in os.environ and not args.token:
        refresh_keystone_token()

    print "[+] Syncing resources..."
    fuzzer.sync_resources()
    for k, v in fuzzer.ig.resources.items():
        print "->", k, v

    stats = {"total": 0, "http_code": {}, "start_time": time.time(), "last_speed": [0, time.time()]}
    while stats["total"] < args.max_events and (time.time() - stats["start_time"]) < args.max_time:
        new_traceback = False
        event = fuzzer.step(args.debug)
        if event is None:
            continue
        if health:
            for health_event in health.check():
                if "tb_id" in health_event:
                    if "uniq_tb" in health_event:
                        new_traceback = True
                    event.tracebacks.append(health_event)
                else:
                    print "Unknown health event", health_event

        if args.db:
            db.append(event)

        if new_traceback:
            print "\n\n%s\n" % event.render('\033[91m')
        else:
            if event.code in (400, 404, 409):
                verbose(event.render('\033[94m'))
            elif event.code >= 200 and event.code < 300:
                verbose(event.render('\033[92m'))
            else:
                verbose(event.render('\033[91m'))

        if event.code == 401 and event.json_output and "auth" in event.json_output.lower() and "OS_USERNAME" in os.environ:
            print "[+] Requesting a new token"
            try:
                refresh_keystone_token()
            except:
                print "[+] Could not get keystone token"
                raise

        stats["http_code"][event.code] = 1 + stats["http_code"].setdefault(event.code, 0)
        stats["total"] += 1
        if stats["total"] % 100 == 0:
            time_now = time.time()
            status_line = "\r%d sec elapsed, %dk events, (%03.02f events/seconds), http_code: %s " % (
                time_now - stats["start_time"],
                stats["total"] / 1000,
                (stats["total"] - stats["last_speed"][0]) / (time_now - stats["last_speed"][1]),
                stats["http_code"],
            )
            stats["last_speed"] = [stats["total"], time_now]
            print status_line,
            stdout.flush()
    print "\nOver."


def restfuzz():
    try:
        do_restfuzz()
    except KeyboardInterrupt:
        print "exiting..."


def reader():
    parser = argparse.ArgumentParser()
    parser.add_argument("db", help="File path to read event from")
    parser.add_argument("--stats", action='store_const', const=True, help="Show stats")
    parser.add_argument("--name", nargs='+', default=[], help="Filter method name")
    parser.add_argument("--code", nargs='+', default=[], type=int, help="Filter return code")
    parser.add_argument("--limit", type=int)

    args = parser.parse_args()

    if args.db.endswith(".gz"):
        db_file = gzip.GzipFile(args.db)
    else:
        db_file = open(args.db)

    db = EventDb(db_file)

    stats = {"event": {}, "tb": {}, "total": 0}
    for event in db.list():
        stats["total"] += 1
        if args.limit and stats["total"] >= args.limit:
            break
        if args.stats:
            if event.name not in stats["event"]:
                stats["event"][event.name] = {}
            ev_st = stats["event"][event.name]
            if event.code not in ev_st:
                ev_st[event.code] = [0, event]
            ev_st[event.code][0] += 1

            for tb in event.tracebacks:
                if tb["tb_hash"] not in stats["tb"]:
                    stats["tb"][tb["tb_hash"]] = [0, tb["tb_id"], tb["uniq_tb"]]
                stats["tb"][tb["tb_hash"]][0] += 1
        if event.name.endswith("_list"):
            continue
        if args.code and event.code not in args.code:
            continue
        if args.name and event.name not in args.name:
            continue
        if not args.stats:
            print event

    if args.stats:
        ev_list = stats["event"].keys()
        ev_list.sort()
        for ev in ev_list:
            print
            print "== %s ==" % ev
            for status_code in stats["event"][ev]:
                num, example = stats["event"][ev][status_code]
                print "%d: %d - [%s]\n\texample: %s" % (status_code, num, example.json_output, example)
        for tb in stats["tb"].values():
            print
            print "Uniq traceback %d count, %s" % (tb[0], tb[1])
            print tb[2]
        print
        print "Total events", stats["total"]
