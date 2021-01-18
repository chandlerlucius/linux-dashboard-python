#!/bin/sh

#Set function name to call from script parameter
function_to_call="$*"

export LC_ALL=C

# CPU Idle & Total
# https://stackoverflow.com/a/23376195
# http://colby.id.au/calculating-cpu-usage-from-proc-stat/
cpu_idle_total() {    
    cpu=$(sed -n 's/^cpu\s//p' /proc/stat)
    idle=$(echo "$cpu" | awk '{print $4 + $5}')
    guest=$(echo "$cpu" | awk '{print $9 + $10}')

    total=0
    for value in $cpu
    do
        total=$((total+value))
    done
    total=$((total-guest))

    echo "{ \"cpu_idle\" : $idle, \"cpu_total\": $total }"
}

# Memory/Swap Available & Total
# https://stackoverflow.com/a/41251290
mem_available_total() {
    mem_total=$(sed -n 's/^MemTotal:*//p' /proc/meminfo | awk '{print $1}')
    mem_free=$(sed -n 's/^MemFree:*//p' /proc/meminfo | awk '{print $1}')
    mem_buffers=$(sed -n 's/^Buffers:*//p' /proc/meminfo | awk '{print $1}')
    mem_cached=$(sed -n 's/^Cached:*//p' /proc/meminfo | awk '{print $1}')
    mem_sreclaimable=$(sed -n 's/^SReclaimable:*//p' /proc/meminfo | awk '{print $1}')
    mem_shmem=$(sed -n 's/^Shmem:*//p' /proc/meminfo | awk '{print $1}')
    mem_available=$((mem_free + mem_buffers + mem_cached + mem_sreclaimable - mem_shmem))
    
    swap_total=$(sed -n 's/^SwapTotal:*//p' /proc/meminfo | awk '{print $1}')
    swap_available=$(sed -n 's/^SwapFree:*//p' /proc/meminfo | awk '{print $1}')
    
    echo "{ \"mem_available\" : $mem_available, \"mem_total\": $mem_total, \"swap_available\" : $swap_available, \"swap_total\": $swap_total }"
}

help() {
    grep "^.*()" "$0" | grep -v "help"
}

if [ "_$1" = "_" ]
then
    help
else
    "$function_to_call"
fi