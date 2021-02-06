#!/bin/sh

#Set function name to call from script parameter
function_to_call="$*"

export LC_ALL=C

db_name="system_stats"
db_url="http://localhost:8086"
db_time_format="ms"

get_categories() {
    echo '[
        { "id": "cpu_usage", "interval": 1 }, 
        { "id": "mem_usage", "interval": 1 },
        { "id": "cpu_info", "interval": 10 }
    ]'
}

get_statistics() {
    echo '[
        { "id": "set_cpu_usage", "interval": 1 },
        { "id": "set_mem_usage", "interval": 1 }
    ]'
}

setup_db() {
    results=$(curl -sS -X POST "$db_url/query" --data-urlencode "q=CREATE DATABASE $db_name")
}

# Query table for last record
# Parameters: table name
query_table_for_last_record() {
    last_record=$(query_db "SELECT * FROM $1 GROUP BY * ORDER BY DESC LIMIT 1")
    echo "$last_record"
}

# Query DB
# Parameters: query statement
query_db() {
    results=$(curl -sSG "$db_url/query?epoch=$db_time_format&db=$db_name" --data-urlencode "q=$1")
    format_results "$results"
}

# Write to DB
# Parameters: data to write
write_db() {
    setup_db
    results=$(curl -sS -X POST "$db_url/write?db=$db_name" --data-binary "$1")
    format_results "$results"
}

# Format json results with "series" or empty {}
format_results() {
    series=$(echo "$1" | jq '.results[].series[]?')
    if [ "$series" != "" ]
    then
        echo "$series"
    else
        echo "{}"
    fi
}

# CPU Idle & Total
# https://stackoverflow.com/a/23376195
# http://colby.id.au/calculating-cpu-usage-from-proc-stat/
set_cpu_usage() {    
    cpu=$(sed -n 's/^cpu\s//p' /proc/stat)
    idle=$(echo "$cpu" | awk '{print $4 + $5}')
    guest=$(echo "$cpu" | awk '{print $9 + $10}')

    total=0
    for value in $cpu
    do
        total=$((total+value))
    done
    total=$((total-guest))

    prev_cpu=$(query_table_for_last_record "cpu_usage")
    prev_cpu=$(echo "$prev_cpu" | jq ' [.columns, .values[]] | transpose | map( {(.[0]): .[1]}) | add')
    prev_idle=$(echo "$prev_cpu" | jq .cpu_idle)
    prev_total=$(echo "$prev_cpu" | jq .cpu_total)

    idle_diff=$((idle-prev_idle))
    total_diff=$((total-prev_total))
    usage=$(((1000*(total_diff-idle_diff)/total_diff+5)/10))

    write_db "cpu_usage cpu_idle=$idle
    cpu_usage cpu_total=$total
    cpu_usage cpu_usage=$usage"
}

# Memory/Swap Available & Total
# https://stackoverflow.com/a/41251290
set_mem_usage() {
    mem_total=$(sed -n 's/^MemTotal:*//p' /proc/meminfo | awk '{print $1}')
    mem_free=$(sed -n 's/^MemFree:*//p' /proc/meminfo | awk '{print $1}')
    mem_buffers=$(sed -n 's/^Buffers:*//p' /proc/meminfo | awk '{print $1}')
    mem_cached=$(sed -n 's/^Cached:*//p' /proc/meminfo | awk '{print $1}')
    mem_sreclaimable=$(sed -n 's/^SReclaimable:*//p' /proc/meminfo | awk '{print $1}')
    mem_shmem=$(sed -n 's/^Shmem:*//p' /proc/meminfo | awk '{print $1}')
    mem_available=$((mem_free + mem_buffers + mem_cached + mem_sreclaimable - mem_shmem))
    
    swap_total=$(sed -n 's/^SwapTotal:*//p' /proc/meminfo | awk '{print $1}')
    swap_available=$(sed -n 's/^SwapFree:*//p' /proc/meminfo | awk '{print $1}')
    
    mem_usage=$(((mem_total - mem_available) * 100 / mem_total))
    if [ "$swap_total" -gt 0 ]
    then
        swap_usage=$(((swap_total - swap_available) * 100 / swap_total))
    fi

    write_db "mem_usage mem_available=$mem_available
    mem_usage mem_total=$mem_total
    mem_usage mem_usage=$mem_usage
    mem_usage swap_available=$swap_available
    mem_usage swap_total=$swap_total
    mem_usage swap_usage=$swap_usage"
}

# Disk Stats
# https://www.percona.com/doc/percona-toolkit/2.1/pt-diskstats.html
set_disk_usage() {
    io_millis=$(awk '$2 == "0" { print $13 " " }' /proc/diskstats | tr -d '\n')
    curr_millis=0
    for millis in $io_millis
    do
        curr_millis=$((curr_millis + millis))
    done
    curr_time=$(date +%s%3N)

    prev_disk=$(query_table_for_last_record "disk_usage")
    prev_disk=$(echo "$prev_disk" | jq ' [.columns, .values[]] | transpose | map( {(.[0]): .[1]}) | add')
    prev_millis=$(echo "$prev_disk" | jq .io_millis)
    prev_time=$(echo "$prev_disk" | jq .time)

    echo "$prev_time - $prev_millis - $curr_time - $curr_millis"
    diff_millis=$((curr_millis - prev_millis))
    diff_time=$((curr_time - prev_time))
    disk_usage=$((diff_millis * 100 / diff_time))
    echo "$disk_usage"

    write_db "disk_usage io_millis=$curr_millis
    disk_usage disk_usage=$disk_usage"
}

# CPU Usage
cpu_usage() {
    usage=$(query_db "SELECT cpu_usage FROM cpu_usage WHERE time > now() - 1m")
    echo "$usage" | jq '. += {"type": "status", "id": "cpu", "name": "cpu", "max": 100, "suffix": "%"}'
}

# Memory Usage
mem_usage() {
    usage=$(query_db "SELECT mem_usage FROM mem_usage WHERE time > now() - 1m")
    echo "$usage" | jq '. += {"type": "status", "id": "memory", "name": "memory", "max": 100, "suffix": "%"}'
}

# Disk Usage
disk_usage() {
    usage=$(query_db "SELECT disk_usage FROM disk_usage WHERE time > now() - 1m")
    echo "$usage" | jq '. += {"type": "status", "id": "disk", "name": "disk", "max": 100, "suffix": "%"}'
}

# CPU Info
cpu_info() {
    lscpu --json | sed -e 's/"field"/"key"/g' -e 's/"data"/"value"/g' -e 's/"lscpu"/"data"/g' | jq '. += {"type": "info", id: "cpu-info", "name": "CPU Info"}'
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