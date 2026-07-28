#!/usr/bin/bash

RG=$1
TIMESTAMP=`date +"%m-%d-%Y_%H%M"`
LOGFILE=atpscale_${RG}_${TIMESTAMP}.log
LOGDIR=/home/opc/log/atpscale_execution
#TOPIC_OCID="ocid1.onstopic.oc1.iad.aaaaaaaa6yr3liaddnj7fktygwovej5ldj7tjpseav2rf7zaa4kicpophnaq"

echo "Started ATP script ${RG} on `date +"%m-%d-%Y %H:%M"` "

python /home/opc/tenancy-admin/oci-atp-scale-down-threaded.py -ip -ipr $@ >$LOGDIR/$LOGFILE 2>&1

echo "Finished ATP script in ${RG} on `date +"%m-%d-%Y %H:%M"` "

find $LOGDIR/ -mtime +30 -name '*.log' -exec rm {} \;

