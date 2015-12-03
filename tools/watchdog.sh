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

# create watchdog ressources

set -ex

TEST_USER=${1:-watchdog}

export OS_USERNAME=admin
export OS_TENANT_NAME=${OS_USERNAME}
keystone tenant-create --name ${TEST_USER}
keystone user-create --name ${TEST_USER} --tenant ${TEST_USER} --pass $OS_PASSWORD --enabled true
export OS_USERNAME=${TEST_USER}
export OS_TENANT_NAME=${OS_USERNAME}
NET_ID=$(neutron net-create test | grep ' id ' | awk '{ print $4 }')
SUB_ID=$(neutron subnet-create --enable-dhcp ${NET_ID} 192.168.42.1/24 | grep ' id ' | awk '{ print $4 }')

neutron router-create test
neutron router-gateway-set test external_network
neutron router-interface-add test ${SUB_ID}

neutron security-group-rule-create --direction ingress --protocol ICMP default

nova boot --image cirros --flavor 1 --nic net-id=${NET_ID} watchdog_vm

FLOATING=$(neutron floatingip-create external_network | grep 'floating_ip_address' | awk '{ print $4 }')
nova floating-ip-associate watchdog_vm ${FLOATING}
ping ${FLOATING}


# ./tools/purge.sh
# keystone tenant-delete ${TEST_USER}
# keystone user-delete ${TEST_USER}
