# Notes from ExaCS Patching

Loosely collected Notes

## Disk Space

We need to ensure disk space is sufficient, especially on the clusters with nodes that have smaller partitions.  Please check all nodes before patching

* /u02 > 15G
* /u01 > 5-6G
* / > 5.5G

### ExaWatcher

To clean up `/` partition, remove some files by reconfiging ExaWatcher.  Before:

```
[opc@exadb-demo1-vrqv32 ~]$ df -h
Filesystem                                                Size  Used Avail Use% Mounted on
/dev/mapper/VGExaDb-LVDbSys1                               15G   11G  4.8G  69% /
```
To clean up, stop the service, then edit `/opt/oracle.ExaWatcher/ExaWatcher.conf` and change `SpaceLimit` to be lower.  In this case, it goes from 3070 -> 2048.  Then restart and wait a couple min.

```
[root@exadb-demo1-vrqv32 oracle.ExaWatcher]# systemctl stop exawatcher
(vi) 
[root@exadb-demo1-vrqv32 oracle.ExaWatcher]# grep SpaceLimit ExaWatcher.conf
# <SpaceLimit> [Space in MB] (integer)
<SpaceLimit> 2048

[root@exadb-demo1-vrqv32 oracle.ExaWatcher]# systemctl start exawatcher
```
After 2-3 min:
```
[root@exadb-demo1-vrqv32 oracle.ExaWatcher]# df -h
Filesystem                                                Size  Used Avail Use% Mounted on
/dev/mapper/VGExaDb-LVDbSys1                               15G  9.2G  5.9G  62% /
```

### Trace Files
How to reconfigure trace files TBD

### DB Homes
If the DB Homes are taking up too much space, do the easy thing first - delete any that have no databases.  After that, look for single-use homes, move those DBs, and delete homes.

There is an ongoing effort to reduce homes down to (Latest, N-1, N-2, N-3) and force users to use one of those.  This will take time.

## Packages
From OL7 to OL8 we needed to pay attention to non OL8 packages, remove them, and re-add.  Dynamic Scaling for example.

For OL8 patching, we noticed patch failures due to this:
```
[root@dbnode-giusq2 ~]# rpm -qa|grep firmware
linux-nano-firmware-20230516-999.26.git6c9e0ed5.el7.noarch
linux-firmware-core-20230516-999.27.git6c9e0ed5.el8.noarch
```

To solve this we had to remove the RPM and retry the patch:
```
[root@dbnode-giusq2 ~]# rpm -e linux-nano-firmware-20230516-999.26.git6c9e0ed5.el7.noarch
[root@dbnode-giusq2 ~]# rpm -qa|grep firmware
linux-firmware-core-20230516-999.27.git6c9e0ed5.el8.noarch
```
