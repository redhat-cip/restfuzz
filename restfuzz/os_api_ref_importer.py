# Copyright 2017 Red Hat
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
import re
import yaml


class OsApiRefFile:
    parameters_db = {}

    def __init__(self, fobj):
        """Load os-api-ref documentation files"""
        if isinstance(fobj, str):
            fobj = open(fobj)
        self.filename = fobj.name
        self.fobj = fobj
        self.methods = []

        method = {}

        last_title = None
        last_line = None

        parameters = None

        parameter_block = []

        while True:
            line = self.fobj.readline()
            if not line:
                self.fobj.close()
                break
            if line == "\n":
                continue
            line = line[:-1]
            if re.match(r'^==*$', line) or re.match(r'^--*$', line):
                last_title = last_line

            elif line.startswith(".. rest_method:"):
                if method:
                    if parameter_block:
                        method["parameters"].append(parameter_block)
                    self.methods.append(method)
                method = {'name': last_title,
                          'url': line[16:].strip(),
                          'parameters': []}

            elif line.startswith(".. rest_parameters::"):
                param_file = line.split()[-1]
                if param_file not in self.parameters_db:
                    self.parameters_db[param_file] = yaml.load(open(
                        os.path.join(os.path.dirname(self.filename),
                                     param_file)))
                parameters = self.parameters_db[param_file]

            elif parameters is not None:
                if not re.match(r"^ *- ", line):
                    # End of parameter list
                    method["parameters"].append(parameter_block)
                    parameters = None
                    parameter_block = []
                else:
                    name, param_name = line.split(': ')
                    name = re.match(r'\s+-\s*(.*)', name).groups()[0].strip()
                    param_name = param_name.strip()
                    param = parameters[param_name]
                    parameter_block.append((name, param))
            last_line = line

        if method:
            if parameter_block:
                method["parameters"].append(parameter_block)
            self.methods.append(method)

    def render(self, method_name=None):
        """Render restfuzz api description"""
        results = {}
        for method in self.methods:
            rmethod = {
                'name': method["name"].lower().replace(' ', '_'),
                'url': method["url"].split(),
            }
            if rmethod["name"] in results:
                print("Skipping duplicate method name %s" % rmethod["name"])
                continue
            if method_name is not None and method_name != rmethod["name"]:
                continue
            print("INFO: processing %s" % rmethod["name"])
            if method_name:
                print(method)
            # Change url format {} to %()s
            rmethod["url"][1] = rmethod["url"][1].replace(
                '{', '%(').replace('}', ')s')

            if len(method["parameters"]) == 2:
                inputs, outputs = method["parameters"]
            elif len(method["parameters"]) == 1:
                if rmethod['url'][0] == "GET":
                    inputs = None
                    outputs = method["parameters"][0]
                else:
                    inputs = method["parameters"][0]
                    outputs = None
            else:
                raise RuntimeError("Couldn't render %s" % method)
            if inputs:
                rmethod["inputs"] = {}
                input_object = None
                # Fix input structure for some methods
                if rmethod["name"] == "create_trunk":
                    input_object = "trunk"
                if rmethod["name"] == "create_subnet":
                    input_object = "subnet"

                for name, inp in inputs:
                    if inp["in"] == "path":
                        rmethod["inputs"].setdefault("url_input", {})[name] = {
                            '_type': 'resource',
                            'required': inp["required"],
                        }
                        input_object = name.replace('_id', '')

                    elif inp["in"] == "query":
                        print("TODO: implement query string for %s" % name)
                        pass

                    elif inp["in"] == "body":
                        # Try to reconstruct object structure of body
                        if inp["type"] == "object":
                            if input_object is None:
                                # First object usualy define the body structure
                                input_object = name
                                rmethod["inputs"][name] = {}
                            else:
                                # This happens for nested object structure
                                print("TODO: implement multiple object input "
                                      "(%s)" % name)
                        else:
                            # Fix type for restfuzz
                            if inp["type"] == "boolean":
                                inp["type"] = "bool"

                            if inp["type"] == "array":
                                inp["type"] = "list_string"

                            # Assume '_id' are uuid
                            if name.endswith("_id"):
                                inp["type"] = "resource"

                            # Those are actually not required
                            if name in ("vip_address", "subnet"):
                                inp["required"] = False

                            # Fix true resource name
                            if name == "vip_subnet_id":
                                name = "subnet_id"
                            if name == "floating_network_id":
                                name = "network_id"

                            if name == "ip_version":
                                inp['type'] = "ip_version"
                            if name == "cidr":
                                inp['type'] = "cidr"
                            if name == "allocation_pools":
                                inp['type'] = "allocation_pool"
                            if name == "dns_nameservers":
                                inp['type'] = "list_ip"

                            # Skip admin-only inputs
                            if name in (
                                    "project_id", "router:external",
                                    "provider:segmentation_id",
                                    "provider:network_type",
                            ):
                                continue

                            if input_object is None:
                                print("TODO: implement direct body input (%s)"
                                      % name)
                            else:
                                rmethod["inputs"].setdefault(
                                    input_object, {})[name] = {
                                        '_type': inp["type"],
                                        'required': inp['required']}
                    else:
                        print("TODO: implement in type %s" % inp["in"])
            if outputs:
                rmethod["outputs"] = {}

                for name, out in outputs:
                    if len(rmethod["outputs"]) >= 1:
                        print("TODO: implement multiple output %s" % name)
                        continue
                    if rmethod["name"] == "list_trunks":
                        name = "trunks"
                    if name[-1] == "s":
                        name = name[:-1]
                    if name.replace('_', '-') not in rmethod["url"][1]:
                        print("TODO: implement nested output %s" % name)
                        continue
                    name_id = "%s_id" % name
                    if name_id in rmethod.get("inputs", {}) or \
                       name_id in rmethod.get("inputs", {}).get(
                           "url_input", {}):
                        print("Skipping output given in input")
                        continue
                    if rmethod["url"][0] == "GET" and out["type"] == "array":
                        rmethod["outputs"][name_id] = {
                            "_type": "resource",
                            "json_extract": 'lambda x: [i["id"] '
                                            'for i in x["%ss"]]' % name
                        }
                    elif out["type"] == "object":
                        rmethod["outputs"]["%s_id" % name] = {
                            '_type': 'resource',
                            'json_extract': 'lambda x: x["%s"]["id"]' % name,
                        }
                    else:
                        print("TODO: implement output %s: %s" % (name, out))
            results[rmethod['name']] = rmethod

        return results


def main():
    if len(sys.argv[1:]) < 2 or not os.path.isdir(sys.argv[-1]):
        print("usage: [input-os-api-ref-files] output-restfuzz-dir")

    for fn in sys.argv[1:-1]:
        oarf = OsApiRefFile(open(fn))
        methods = oarf.render()
        if not methods:
            print("%s: Skipping empty file" % fn)
            continue
        yaml_str = []
        yaml_str.append("methods:")
        for _, method in methods.items():
            yaml_str.append("  - name: '%s'" % method["name"])
            yaml_str.append("    url: %s" % method["url"])
            if method.get("inputs"):
                yaml_str.append("    inputs:")
                yaml_str.append(
                    "      " +
                    yaml.dump(
                        method["inputs"],
                        default_flow_style=False).replace('\n',
                                                          '\n      ')[:-7])
            if method.get("outputs"):
                yaml_str.append("    outputs:")
                yaml_str.append(
                    "      " +
                    yaml.dump(
                        method["outputs"],
                        default_flow_style=False).replace('\n',
                                                          '\n      ')[:-7])
            yaml_str.append("")

        ofn = os.path.join(sys.argv[-1],
                           os.path.basename(fn) + ".yaml").replace('.inc', '')
        with open(ofn, "w") as of:
            of.write("\n".join(yaml_str))
        print("%s: generated from %s" % (ofn, fn))


if __name__ == "__main__":
    main()
