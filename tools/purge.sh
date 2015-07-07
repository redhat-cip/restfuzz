#!/bin/bash
# delete ressource of a tenant

for instance in $(nova list | awk '{ print $2 }' | grep -- -); do
    nova delete $instance
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
