#!/usr/bin/python

import string
import random
import uuid


class InputGenerator(object):
    def __init__(self, chaos_monkey=True):
        self.generator_list = []
        for generator in dir(self):
            if generator.startswith('gen_'):
                self.generator_list.append(generator[4:])
        self.resources = {}
        # Chaos monkey switchs types
        if chaos_monkey:
            self.once_every = lambda number: random.randint(1, number) == number
        else:
            self.once_every = lambda dummy: False

    def generate(self, input_type, resource_name=None):
        # Call generator
        if input_type not in self.generator_list:
            raise RuntimeError("Missing generator for input type: %s" % (input_type))
        generator = self.__getattribute__("gen_%s" % input_type)
        if input_type == "resource":
            return generator(resource_name)
        return generator()

    def gen_mx(self):
        return "%d %s" % (random.randint(0, 65535 * 2), self.generate_input("domain"))

    def gen_soa(self):
        return "%s %s %d %d %d %d %d" % (
            self.generate_input("domain"),
            self.generate_input("domain"),
            random.randint(0, 65535 * 2),
            random.randint(0, 65535 * 2),
            random.randint(0, 65535 * 2),
            random.randint(0, 65535 * 2),
            random.randint(0, 65535 * 2),
        )

    def gen_spf(self):
        return "v=spf1 +all"

    def gen_srv(self):
        return "%d %d %d %s" % (
            random.randint(0, 65535 * 2),
            random.randint(0, 65535 * 2),
            random.randint(0, 65535 * 2),
            self.generate_input("domain"),
        )

    def gen_sshfp(self):
        return "1 2 aa2df857dc65c5359f02ca75ec5c4308c0100594d931e8d243a42f586257b5e8"

    def gen_record_type(self):
        return random.choice([u'A', u'AAAA', u'CNAME', u'MX', u'TXT', u'SPF', u'SRV', u'PTR', u'SSHFP', u'SOA', u'NS'])

    def gen_record(self):
        record_type = self.generate_input("record_type")
        record_type_generator = {
            "A": "ipv4",
            "AAAA": "ipv6",
            "CNAME": "hostname",
            "PTR": "hostname",
            "NS": "domain",
            "MX": "mx",
            "TXT": "string",
            "SPF": "spf",
            "SRV": "srv",
            "SSHFP": "sshfp",
            "SOA": "soa",
        }
        try:
            input_type = record_type_generator[record_type]
        except:
            input_type = random.choice(record_type_generator.values())
        if self.once_every(5):
            input_type = random.choice(record_type_generator.values())
        records = self.generate_input("list_%s" % input_type)
        return {'type': record_type, 'records': records}

    def gen_zone_type(self):
        return random.choice([u'PRIMARY', u'SECONDARY'])

    def gen_domain(self):
        return "%s." % self.generate_input("hostname")

    def gen_byte(self):
        return int(random.random() * 2 ** 8)

    def gen_short(self):
        return int(random.random() * 2 ** 16)

    def gen_integer(self):
        return int(random.random() * 2 ** 64)

    def gen_volume_status(self):
        return random.choice(('creating', 'available', 'attaching', 'in-use', 'deleting', 'error', 'error_deleting', 'backing-up', 'restoring-backup', 'error_restoring', 'error_extending'))

    def gen_hostname(self):
        domain = []
        for i in xrange(0, random.randint(0, 5)):
            domain.append(
                ''.join(random.choice(string.letters + string.digits) for _ in range(random.randint(1, 30)))
            )
            domain.append(".")
        return "".join(domain[:-1])

    def gen_mail(self):
        return "%s@%s" % (
            ''.join(random.choice(string.letters + string.digits) for _ in range(random.randint(1, 30))),
            self.generate_input("hostname")
        )

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

    def gen_visibility(self):
        return random.choice(('public', 'private'))

    def gen_disk_format(self):
        return random.choice(('ami', 'ari', 'aki', 'vhd', 'vmdk', 'raw', 'qcow2', 'vdi', 'iso'))

    def gen_container_format(self):
        return random.choice(('ami', 'ari', 'aki', 'bare', 'ovf'))

    def gen_image_status(self):
        return random.choice(('pending', 'accepted', 'refused'))

    def gen_patch_operation(self):
        return random.choice(('add', 'remove', 'replace'))

    def gen_dict(self):
        d = {}
        for i in xrange(0, random.randint(1, 30)):
            s = self.gen_string()
            d[str(s)] = self.generate("string")
        return d

    def gen_unicode(self):
        chunk = open("/dev/urandom").read(random.randint(0, 512))
        return unicode(chunk, errors='ignore')

    def gen_ascii(self):
        return ''.join(random.choice(string.letters + string.digits) for _ in range(random.randint(1, 512))),

    def gen_string(self):
        if self.once_every(10):
            return self.gen_unicode()
        if self.once_every(5):
            return self.gen_ascii()
        return random.choice((
            "JaVaScRiPt:alert('XSS')",
            'alert(document.cookie)',
            "' OR 1 == 1",
            "jav&#x0D;ascript:alert('XSS');",
        ))

    def gen_ip_version(self):
        return random.choice((4, 6))

    def gen_port(self):
        return random.randint(0, 65535)

    def gen_address_pair(self):
        return {
            "ip_address": self.generate_input("cidr"),
            "mac_address": self.generate_input("mac_address")
        }

    def gen_cidr(self):
        addr = self.generate_input("ip")
        try:
            if self.oncne_every(5) or ":" in addr:
                return "%s/%d" % (addr, random.randint(0, 128))
        except:
            pass
        return "%s/%d" % (addr, random.randint(0, 32))

    def gen_ipv6_mode(self):
        return random.choice(['dhcpv6-stateful', 'dhcpv6-stateless', 'slaac'])

    def gen_allocation_pool(self):
        return {'start': self.generate_input("ip"), 'end': self.generate_input("ip")}

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
        if self.once_every(2):
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

    def gen_ip(self, ip_version=4):
        if self.once_every(10):
            ip_version = random.choice((4, 6))
        if ip_version == 4:
            return self.generate_input("ipv4")
        else:
            return self.generate_input("ipv6")

    def gen_fixed_ip(self):
        d = {}
        if not self.once_every(3):
            d['ip_address'] = self.generate_input("ip")
        if not self.once_every(3):
            d['subnet_id'] = random.randint(0, 32)
        return d

    def gen_hostroute(self):
        return {
            'destination': random.randint(0, 32),
            'nexthop': self.generate_input("ip")
        }

    def generate_input(self, input_type=None, resource_name=None):
        # Once in a while, switch generator
        if not input_type or self.once_every(20):
            input_type = random.choice(self.generator_list)

        # Check if it's a list
        is_list = False
        if input_type.startswith('list_'):
            is_list = True
            input_type = input_type[5:]

        # Once in a while, invert is_list status
        if self.once_every(20):
            is_list = not is_list

        if is_list:
            result = []
            for i in xrange(0, random.randint(0, 5)):
                result.append(self.generate(input_type, resource_name))
        else:
            result = self.generate(input_type, resource_name)
        return result

    def generate_inputs(self, input_description):
        # Generate params
        call_params = {}

        def walk_inputs(data_set, params):
            # For each input
            for input_name, v in data_set.items():
                if 'type' not in v:
                    # If not an input definition, recurse object
                    inputs = walk_inputs(v, {})
                    if inputs:
                        params[input_name] = inputs
                    continue
                if 'required' in v or self.once_every(5):
                    # If input is required or once in a while, generate input type
                    resource_name = None
                    if v['type'] in ('resource', 'list_resource'):
                        resource_name = v.setdefault('resource_name', input_name)
                    new_input = self.generate_input(v['type'], resource_name)
                    if "expand" in v and isinstance(new_input, dict):
                        for k, v in new_input.items():
                            params[k] = v
                    else:
                        params[input_name] = new_input
            return params
        walk_inputs(input_description, call_params)
        return call_params

    # resource managements
    def resource_add(self, resource_name, resource):
        if resource_name not in self.resources:
            self.resources[resource_name] = []
        if resource not in self.resources[resource_name]:
            self.resources[resource_name].append(resource)

    def resources_add(self, output):
        if not output:
            return
        for resource_name in output:
            for resource in output[resource_name]:
                self.resource_add(resource_name, resource)

    def resource_remove(self, resource_name, resource):
        if resource_name not in self.resources or resource_name == "tenant_id":
            return
        try:
            self.resources[resource_name].remove(resource)
        except ValueError:
            pass
        if len(self.resources[resource_name]) == 0:
            del self.resources[resource_name]

    def gen_resource(self, resource_name=None):
        if resource_name in self.resources:
            return random.choice(self.resources[resource_name])
        return self.generate_input("string")

    def resources_clear(self):
        self.resources.clear()
