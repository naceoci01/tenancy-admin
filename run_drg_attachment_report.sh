#!/usr/bin/bash

RG=$1
TIMESTAMP=`date +"%m-%d-%Y_%H%M"`
LOGFILE=drg_attachement_${RG}_${TIMESTAMP}.log
LOGDIR=/home/opc/log/drg_attachement_execution
MD_DIR=/home/opc/cloud-engineers/resources
#TOPIC_OCID="ocid1.onstopic.oc1.iad.aaaaaaaa6yr3liaddnj7fktygwovej5ldj7tjpseav2rf7zaa4kicpophnaq"

echo "Started DRG script ${RG} on `date +"%m-%d-%Y %H:%M"` "

python /home/opc/tenancy-admin/oci-drg-find-cidr.py -m ${MD_DIR} -ip -ipr $@ >$LOGDIR/$LOGFILE 2>&1

echo "Git"
cd ${MD_DIR}
git add drg_attachments_ocid1*
git commit -m "daily"
git push

echo "Finished DRG script in ${RG} on `date +"%m-%d-%Y %H:%M"` "

find $LOGDIR/ -mtime +30 -name '*.log' -exec rm {} \;

