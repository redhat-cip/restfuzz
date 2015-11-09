#!/usr/bin/python

import argparse
import os
import gzip

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

    args = parser.parse_args()

    methods = {}
    for api in args.api:
        api_methods = method.load_methods(api)
        methods.update(api_methods)

    api = Api()
    if args.token:
        api.set_header("X-Auth-Token", args.token)

    fuzzer = ApiRandomCaller(api, methods)
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

    while True:
        event = fuzzer.step(args.debug)
        if health:
            for d in health.check():
                if d[0] == "res":
                    event.res = d[1]
                elif d[0] == "tb":
                    event.tracebacks.append(d[1])
                else:
                    print "Unknown health tupple", d

        if args.db:
            db.append(event)

        if event.code in (400, 404, 409):
            print event.render('\033[94m')
        elif event.code >= 200 and event.code < 300:
            print event.render('\033[92m')
        else:
            print event.render('\033[91m')

        if event.code == 401 and event.json_output and "auth" in event.json_output.lower() and "OS_USERNAME" in os.environ:
            print "[+] Requesting a new token"
            try:
                refresh_keystone_token()
            except:
                print "[+] Could not get keystone token"
                raise


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
                if tb["hash"] not in stats["tb"]:
                    stats["tb"][tb["hash"]] = [0, tb["id"], tb["tb"]]
                stats["tb"][tb["hash"]][0] += 1
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
