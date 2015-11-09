#!/bin/bash
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
neutron router-gateway-set test public
neutron router-interface-add test ${SUB_ID}

neutron security-group-rule-create --direction ingress --protocol ICMP default

nova boot --image cirros --flavor 1 watchdog_vm

FLOATING=$(neutron floatingip-create public | grep 'floating_ip_address' | awk '{ print $4 }')
nova floating-ip-associate watchdog_vm ${FLOATING}
ping ${FLOATING}
