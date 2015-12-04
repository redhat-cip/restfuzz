#!/bin/bash
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

# delete ressource of a tenant

for instance in $(nova list | awk '{ print $2 }' | grep -- -); do
    nova delete $instance
done

for domain in $(designate domain-list | awk '{ print $2 }' | grep -- -); do
    designate domain-delete $domain
done


export OS_TOKEN=$(keystone token-get | grep ' id ' | awk '{ print $4}')
export OS_URL=http://localhost:9696/

for port in $(neutron port-list | awk '{ print $2 }' | grep -- -); do
    neutron port-delete $port && continue
    gateway_id=$(neutron port-show $port | grep device_id | awk '{ print $4 }')
    neutron router-interface-delete $gateway_id port=$port
done
for obj in router port subnet net security-group; do
    for i in $(neutron ${obj}-list | awk '{ print $2 }' | grep -- -); do
        neutron ${obj}-delete $i
    done
done

# Clean logs
for obj in /var/log/*/*; do
    echo -n | sudo tee $obj
done
