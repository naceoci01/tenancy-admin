#!/usr/bin/bash

RG=$1
TIMESTAMP=`date +"%m-%d-%Y_%H%M"`
LOGFILE=adwconvert_${RG}_${TIMESTAMP}.log
LOGDIR=/home/opc/log/adwconvert_execution
#TOPIC_OCID="ocid1.onstopic.oc1.iad.aaaaaaaa6yr3liaddnj7fktygwovej5ldj7tjpseav2rf7zaa4kicpophnaq"

echo "Started ADW script ${RG} on `date +"%m-%d-%Y %H:%M"` "

python /home/opc/tenancy-admin/oci-adw-convert-threaded.py -ip -ipr $@ >$LOGDIR/$LOGFILE 2>&1

echo "Finished ADW script in ${RG} on `date +"%m-%d-%Y %H:%M"` "

find $LOGDIR/ -mtime +30 -name '*.log' -exec rm {} \;

