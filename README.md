Backup & Restore Eucalyptus cloud metadata.

This script will back up the contents of the Eucalyptus database and keys directory.

1. Backing up
-------------

The following options are required:

 *  --mode=backup: This indicates that we are backing up.
 *  --euca-home: Top level directory where EUCALYPTUS is installed. Defaults to "/" for most packaged installations.
 *  --backup-root: Top level directory where backups will be saved. The user running the backup script should have permission to write to this directory. Defaults to "/tmp/eucalyptus-backups"

For example, python eucalyptus-backup-restore.py --mode=backup  --backup-root=/home/eucauser/eucalyptus-backups

2. Restore from backup
----------------------

The following options are required:

 *  --mode=restore: This indicates that we are restoring from a backup.
 *  -f: This is the .SQL script to restore from.
 *  --backup-dir: The directory where the backup is stored.
 *  --forreal: When this option is passed, we will try to actually restore (not a dry run). This option must be passed if you want something to actually happen. 

For example, python eucalyptus-backup-restore.py --mode=restore -f /home/eucauser/eucalyptus-backups/2013-09-24-0616/eucalyptus-pg_dumpall.sql --backup-dir=/home/eucauser/eucalyptus-backups/2013-09-24-0616 --forreal

