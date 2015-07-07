#!/usr/bin/env python
#
# Copyright (C) 2015 Red Hat Inc
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
import sys
import yaml
import logging
import json
import random
import time
import uuid
import string
from pprint import pprint

import requests

seed = int(time.time() * os.getpid())
random.seed(seed)
print "Using seed %d" % seed

# globals
DEBUG="--debug" in sys.argv

def debug(msg):
    print "\033[93m%s\033[0m" % msg

class Api:
    # Wrapper around requests
    headers = {'User-Agent': 'javago-0.1.0', 'Content-Type': 'application/json', 'Accept': 'application/json'}
    def __init__(self, token = None):
        if token:
            self.set_token(token)

    def set_token(self, token):
        self.headers['X-Auth-Token'] = token

    def request(self, method, endpoint, data):
        return requests.request(method, url = endpoint, headers = self.headers, data = data)

class FakeApi:
    def request(self, method, endpoint, data):
        class FakeRequest:
            status_code = 200
            text = None
        return FakeRequest()

def walk_dict(data_set):
  # recursive generator of input definition from schema
  # yield input name, input description
  if not isinstance(data_set, dict):
      raise RuntimeError("%s: Missing type in input/output description" % data_set)
  for k,v in data_set.items():
    if 'type' in v:
        yield (k, v)
    else:
        for k2,v2 in walk_dict(v):
            if 'type' in v2:
                yield (k2, v2)

def find_input(data_set, input_name):
    # find an input value from inputs dictionnary
    for k,v in data_set.items():
        if k == input_name:
            return v
        elif isinstance(v, dict):
            v = find_input(v, input_name)
            if v:
                return v

class CallError(Exception):
    def __init__(self, code, error):
        self.code = code
        self.error = error
    def __repr__(self):
        return "%d - %s" % (self.code, self.error)
    def __str__(self):
        return self.__repr__()

class Method:
    def __init__(self, kwarg, base_url):
        # Create method object from yaml kwarg description
        self.base_url = base_url
        self.name = kwarg['name']
        self.http_method = kwarg['url'][0]
        self.url = kwarg['url'][1]
        self.inputs = kwarg.setdefault('inputs', {})
        self.outputs = kwarg.setdefault('outputs', {})

        # check method requirements/outputs
        self.requires = set()
        self.produces = set()
        for k,v in walk_dict(self.inputs):
            if v['type'] in ('ressource', 'list_ressource'):
                self.requires.add(v.setdefault('ressource_name', k))

        for k,v in walk_dict(self.outputs):
            if v['type'] in ('ressource', 'list_ressource'):
                self.produces.add(v.setdefault('ressource_name', k))

    def check_requirements(self, ressources):
        for i in self.requires:
            if i in ressources:
                return True

    def call(self, params, api):
        # Encode inputs
        url = "%s/%s" % (self.base_url, self.url)
        json_input = None
        if params:
            if "url_input" in params:
                url_input = params['url_input']
                url = url % params['url_input']
                del params['url_input']
                if params:
                    json_input = json.dumps(params)
                params['url_input'] = url_input
            else:
                json_input = json.dumps(params)

        # Call
        t = time.time()
        prefix = "[%s.%03.0f]" % (time.strftime("%Y-%m-%d %H:%M:%S"), (t - int(t))*1000)
        print "%s %s: curl -X %s %20s\t -d '%s'" % (
                prefix, self.name, self.http_method, url, json_input
        )
        resp = api.request(self.http_method, url, json_input)

        # Extract outputs from method results according to method outputs description
        outputs = {}
        if resp.status_code >= 200 and resp.status_code < 300 and resp.text:
            json_output = resp.json()
            for output in self.outputs:
                try:
                    outputs[output] = eval(self.outputs[output]['json_extract'])(json_output)
                except:
                    debug("Could not decode output [%s] with [%s] in '%s'" % (output, self.outputs[output], json_output))

        if resp.status_code >= 200 and resp.status_code < 300:
            print "%s -> \033[92m%03s: %s\033[0m" % (prefix, resp.status_code, outputs)
            return outputs
        else:
            if resp.status_code in (400, 404, 409):
                print "%s -> \033[94m%03s: %s\033[0m" % (prefix, resp.status_code, resp.text)
            else:
                print "%s -> \033[91m%03s: %s\033[0m" % (prefix, resp.status_code, resp.text)
            raise CallError(resp.status_code, resp.text)

    def __repr__(self):
        return "%s" % self.name

class Graph:
    # Graph that connects method's outputs to method's inputs
    def __init__(self, methods):
        self.graph = {}
        self.entry_points = set()
        for method in methods:
            if method.http_method == "DELETE":
                self.graph[method] = set()
                continue
            edges = set()
            for m in methods:
                if m == method:
                    continue
                if len(m.requires) and m.check_requirements(method.produces):
                    edges.add(m)
            self.graph[method] = edges
        # Find entry_point
        for method in methods:
            entrypoint=True
            for m in methods:
                if method in self.graph[m]:
                    entrypoint=False
                    break
            if entrypoint:
                self.entry_points.add(method)
        print "-- graph debug --"
        pprint(self.graph)

    def plot(self):
        of = open("/tmp/graph.dot", "w")
        of.write("digraph api {\n")
        for i in self.entry_points:
            of.write('  %s [color=orange];\n' % i)
        for i in self.graph:
            for j in self.graph[i]:
                of.write('  %s -> %s ;\n' % (i, j))
        of.write("}\n")
        of.close()
        os.system("dot -o /tmp/test.png -Tpng /tmp/graph.dot; feh /tmp/test.png")


once_every = lambda number: random.randint(1, number) == number

class InputGenerator(object):
    def __init__(self):
        self.generator_list = []
        for generator in dir(self):
            if generator.startswith('gen_'):
                self.generator_list.append(generator[4:])

    def generate_input(self, input_type = None):
        # Once in a while, switch generator
        if not input_type or once_every(20):
            input_type = random.choice(self.generator_list)

        # Check if it's a list
        is_list = False
        if input_type.startswith('list_'):
            is_list = True
            input_type = input_type[5:]

        # Once in a while, invert is_list status
        if once_every(20):
            is_list = not is_list

        if input_type not in self.generator_list:
            raise RuntimeError("Missing generator for input type: %s" % (input_type))
            input_type = random.choice(self.generator_list)
        generator = self.__getattribute__("gen_%s" % input_type)

        if is_list:
            result = []
            for i in xrange(0, random.randint(0, 5)):
                result.append(generator())
        else:
            result = generator()
        return result

    def gen_ethertype(self):
        return random.choice(("IPv4", "IPv6"))

    def gen_net_direction(self):
        return random.choice(("egress", "ingress"))

    def gen_net_protocol(self):
        return random.choice(("tcp", "icmp", "udp"))

    def gen_uuid(self):
        return str(uuid.uuid4())

    def gen_bool(self):
        return random.choice((True, False))

    def gen_string(self):
        return random.choice((
            "JaVaScRiPt:alert('XSS')",
            'alert(document.cookie)',
            '""><SCRIPT>alert("XSS")</SCRIPT>',
            "# onmouseover=\"alert('xxs')\"",
            '&#0000106&#0000097&#0000118&#0000097&#0000115&#0000099&#0000114&#0000105&#0000112&#0000116&#0000058&#0000097&'
            '#0000108&#0000101&#0000114&#0000116&#0000040&#0000039&#0000088&#0000083&#0000083&#0000039&#0000041',
            "jav&#x0D;ascript:alert('XSS');",
            "<BGSOUND SRC=\"javascript:alert('XSS');\">"
        ))


    def gen_ip_version(self):
        return 4 #random.choice((4,6))

    def gen_cidr(self):
        addr = self.gen_ip()
        if addr and ":" in addr:
            return "%s/%d" % (addr, random.randint(0, 128))
        else:
            return "%s/%d" % (addr, random.randint(0, 32))

    def gen_ipv6_mode(self):
        ipv6_mode = ['dhcpv6-stateful', 'dhcpv6-stateless', 'slaac']
        return random.choice(ipv6_mode)

    def gen_allocation_pool(self):
        return {'start': self.gen_ip(), 'end': self.gen_ip()}

    def gen_mac_address(self):
        return "%02X:%02X:%02X:%02X:%02X:%02X" % (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
        )

    def gen_ipv4(self):
        addr = ["0x42", "0x41.0x41.0x41.0x41", "044.0.0.041"
                "0.0.0.0", "255.255.255.255",
                "0.10.0.0", "0.0.0.1", "1.0.0.0",
                "192.168.255.0", "256.200.200.1"]
        if once_every(2):
            return "%d.%d.%d.%d" % (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
            )
        else:
            return random.choice(addr)

    def gen_ipv6(self):
        addr = ["::", "0x42::", "044:041::044",
                "ffff::ff", "ff3e:40:ff:80:ff:80::",
                ]
        return random.choice(addr)

    def gen_ip(self, ip_version = 4):
        if once_every(10):
            ip_version = random.choice((4, 6))
        if ip_version == 4:
            return self.gen_ipv4()
        else:
            return self.gen_ipv6()

    def gen_fixed_ip(self):
        d = {}
        if not once_every(3):
            d['ip_address'] = self.gen_ip()
        if not once_every(3):
            d['subnet_id'] = random.randint(0, 32)

    def gen_hostroute(self):
        return {
            'destination': random.randint(0,32),
            'nexthop': self.gen_ip()
        }

input_generator = InputGenerator().generate_input


# Random api walk with ressource management
class ApiRandomWalk:
    def __init__(self, api, methods):
        self.api = api
        self.methods = methods
        self.methods_list = list(methods)
        # create ressources lists
        self.ressources = {}
        self.ressources_dtor = {}
        for m in methods:
            for r in m.requires.union(m.produces):
                if r not in self.ressources:
                    self.ressources[r] = []
                if m.http_method == 'DELETE':
                    self.ressources_dtor[r] = m

    def purge_ressource(self, ressource_name, ressource):
        print "Cleaning ressources %s: %s" % (ressource_name, ressource)
        try:
            outputs = self.ressources_dtor[ressource_name].call({'url_input': {ressource_name: ressource}}, self.api)
            self.ressources[ressource_name].remove(ressource)
        except:
            pass

    def purge_ressources(self):
        for i in xrange(3):
            for ressource_name in self.ressources:
                for ressource in self.ressources[ressource_name]:
                    self.purge_ressource(ressource_name, ressource)

    def prepare_call(self, method):
        # Generate params
        call_params = {}
        def walk_inputs(data_set, params):
            # For each input
            for input_name,v in data_set.items():
                if 'type' not in v:
                    # If not an input definition, recurse object
                    inputs = walk_inputs(v, {})
                    if inputs:
                        params[input_name] = inputs
                    continue
                if v['type'] in ('ressource', 'list_ressource'):
                    # If input type is ressources
                    ressource_name = v.setdefault('ressource_name', input_name)
                    if once_every(90):
                        # Once in a while, generate random data
                        params[input_name] = input_generator()
                    else:
                        # Or pick ressources already collected
                        if v['type'] == 'list_ressource':
                            l = []
                            r_list = list(self.ressources[ressource_name])
                            random.shuffle(r_list)
                            for i in xrange(0, random.randint(0, len(r_list))):
                                l.append(r_list.pop())
                            params[input_name] = l
                        else:
                            if self.ressources[ressource_name]:
                                params[input_name] = random.choice(list(self.ressources[ressource_name]))
                elif 'required' in v or once_every(5):
                    # If input is required or once in a while, generate input type
                    params[input_name] = input_generator(v['type'])
            return params
        walk_inputs(method.inputs, call_params)
        return call_params

    def process_output(self, method, inputs, outputs):
        # Adds output to ressources
        for output in outputs:
            self.ressources[output].append(outputs[output])

        # Remove destroyed ressources
        if method.http_method == 'DELETE':
            for input_name in method.requires:
                inp = find_input(inputs, input_name)
                if inp in self.ressources[input_name]:
                    self.ressources[input_name].remove(inp)

    def step(self):
        random.shuffle(self.methods_list)
        # Pick a callable method
        for method in self.methods_list:
            if method.http_method != 'DELETE' or once_every(200):
                break


        if DEBUG:
            raw_input("--------------------------- Press enter to call %s " % method)
        try:
            inputs = self.prepare_call(method)
            outputs = method.call(inputs, self.api)
            self.process_output(method, inputs, outputs)
        except CallError, e:
            # Remove ressources that results in a 404
            if e.code == 404 and method.name.endswith("_update"):
                for input_name in method.requires:
                    inp = find_input(inputs, input_name)
                    if inp not in self.ressources[input_name]:
                        continue
                    self.ressources[input_name].remove(inp)

            # Purge all ressource when quota exceed
            #if e.code == 409:
            #    self.purge_ressources()
            if e.code == 401: # Authorization required... create a new token
                token, tenant_id = token_get()
                self.api.set_token(token)
                self.purge_ressources()

        sys.stdout.flush()


def load_methods(folder_or_file):
    files = []
    if os.path.isdir(folder_or_file):
        for fname in filter(lambda d: d.endswith('.yaml'), os.listdir(folder_or_file)):
            files.append("%s/%s" % (folder_or_file, fname))
    elif os.path.isfile(folder_or_file) and folder_or_file.endswith('.yaml'):
        files.append(folder_or_file)
    if not files:
        raise RuntimeError("Invalid api_descriptions, need .yaml files")

    methods = set()
    for fname in files:
        d = yaml.load(open(fname))
        if "base_url" not in d:
            raise RuntimeError("%s: missing base_url..." % fname)
        if "methods" not in d:
            raise RuntimeError("%s: missing methods list..." % fname)
        for method in d['methods']:
            methods.add(Method(method, d['base_url']))
    return methods

def token_get(self):
    # Return (token, tenant_id)
    token, tenant_id = os.popen("keystone token-get | grep ' id\|tenant_id' | awk '{ print $4 }'").read().strip().split()

def main(argv):
    if len(argv) < 2 or "--help" in argv:
        print "usage: %s api_folder_or_file [--graph] [--debug] [--dry_run]"
        exit(1)

    token, tenant_id = None, None
    methods = load_methods(argv[1])

    if "--graph" in argv:
        graph = Graph(methods)
        graph.plot()
        exit(0)

    if "--dry_run" in argv:
        api = FakeApi()
    else:
        if "OS_USERNAME" in os.environ:
            token, tenant_id = token_get()
        api = Api(token)

    a = ApiRandomWalk(api, methods)
    if tenant_id:
        a.ressources['tenant_id'] = [tenant_id]
    try:
        idx = 0
        while True:
            a.step()
            if idx % 1024 == 0:
                print "Current ressources", a.ressources
            idx += 1
    except:
        print "\nAborting..."
        a.purge_ressources()
        print "Done."
        raise

if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        pass
