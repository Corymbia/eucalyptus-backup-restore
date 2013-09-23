#!/usr/bin/python

# Backup and restore a Eucalyptus Cloud Controller DB & Keys
#
# Software License Agreement (BSD License)
#
# Copyright (c) 2013, Eucalyptus Systems, Inc.
# All rights reserved.
#
# Redistribution and use of this software in source and binary forms, with or
# without modification, are permitted provided that the following conditions
# are met:
#
#   Redistributions of source code must retain the above
#   copyright notice, this list of conditions and the
#   following disclaimer.
#
#   Redistributions in binary form must reproduce the above
#   copyright notice, this list of conditions and the
#   following disclaimer in the documentation and/or other
#   materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Author: Tom Ellis <tom.ellis@eucalyptus.com>
# Author: Neil Soman <neil@eucalyptus.com>

import sys
import time
import os
from optparse import OptionParser
import logging
import commands
import shutil

prog_name = sys.argv[0]
date_fmt = time.strftime('%Y-%m-%d-%H%M')
date = time.strftime('%Y-%m-%d')
backup_dir = "/home/neil/eucalyptus-backup"
backup_subdir = backup_dir + "/" + date
backup_file = backup_subdir + "/eucalyptus-pg_dumpall-" + date_fmt + ".sql"

#Eucalyptus paths and properties
db_port = "8777"
db_user = "root"
db_dir = "var/lib/eucalyptus/db/data"
key_dir = "var/lib/eucalyptus/keys"
db_root = "var/lib/eucalyptus/db"
db_socket = db_dir + "/.s.PGSQL." + db_port
pg_dumpall_path = "/usr/bin/pg_dumpall"
euca_user = "neil"

# Enable debug logging
logger = logging.getLogger('euca-clc-backup')
logging.basicConfig(format='%(asctime)s:%(filename)s:%(levelname)s: %(message)s', level=logging.DEBUG)

def get_args():
    # Parse options
    parser = OptionParser()
    parser.add_option("--eucahome", dest="euca_home", default="/")
    parser.add_option("--backup", action="store_true", dest="backup", default=False)
    parser.add_option("--restore", action="store_true", dest="restore", default=False)
    parser.add_option("--forreal", action="store_true", dest="forreal", default=False)
    parser.add_option("--file", "-f", dest="backup_file")
    (options, args) = parser.parse_args()
    return options

def do_backup(euca_home):
    # is the db running? socket should exist
    if not os.path.exists(euca_home + db_socket):
        logging.critical("PostgreSQL database not running. Please start eucalyptus-cloud.")
        sys.exit(1)

    # does pg_dumpall exist?
    # TODO: better check
    if not os.path.isfile(pg_dumpall_path):
        logging.critical("pg_dumpall does not exist at: %s", (pg_dumpall_path))
        sys.exit(1)

    # does the backup dir exist? create it
    if not os.path.exists(backup_dir):
        logging.warn("Backup directory %s does not exist, creating...", (backup_dir))
        os.makedirs(backup_dir)

    ##########
    # Backup #
    ##########

    # Trying...
    # 1. pg_dumpall
    # 2. pg_dump each eucalyptus db
    # 3. db dir backup
    # 4. Eucalyptus keys dir

    # Create a subdir for today
    if not os.path.exists(backup_subdir):
        os.makedirs(backup_subdir)

    # Run a pg_dumpall dump
    logging.info("Running pg_dumpall backup")
    dump_all="sudo pg_dumpall -h%s -p%s -U%s -f%s" % (euca_home + db_dir, db_port, db_user, backup_file)
    os.popen(dump_all)
    logging.info("pg_dumpall complete: %s", (backup_file))

    # List of individual databases in postgres 
    database_list = "sudo psql -U%s -d%s -p%s -h%s --tuples-only -c 'select datname from pg_database' | grep -E -v '(template0|template1|^$)'" % (db_user, "postgres", db_port, euca_home + db_dir)

    # Dump only global objects (roles and tablespaces) which include system grants
    system_grants = "sudo pg_dumpall -h%s -p%s -U%s -g > %s/system.%s.gz" % (euca_home + db_dir, db_port, db_user, backup_subdir, date_fmt)
    #system_grants = "pg_dumpall --oids -c -h%s -p%s -U%s -g > %s/system.%s.gz" % (db_dir, db_port, db_user, backup_subdir, date_fmt)

    logging.info("Backing up global objects")
    os.popen(system_grants)

    logging.info("Running pg_dump on each database")
    for base in os.popen(database_list).readlines():
        base = base.strip()
        filename = "%s/%s-%s.sql" % (backup_subdir, base, date)
        dump_cmd = "sudo pg_dump -C -F c -U%s -p%s -h%s %s > %s" % (db_user, db_port, euca_home + db_dir, base, filename)
        logging.debug("Running pg_dump on %s", (base))
        os.popen(dump_cmd)

    logging.info("Backup complete")

def do_restore(euca_home, backup_file, forreal):
    output = commands.getoutput("ps -ef")
    if "eucalyptus-cloud" in output:
        logging.critical("Eucalyptus (eucalyptus-cloud) is currently running. Please stop eucalyptus-cloud before attempting to restore")
        sys.exit(1)
    if not forreal:
        logging.info("Dry run only. Run with --forreal to really restore to " + euca_home + db_dir)
    else:
        logging.info("Restoring from backup to " + euca_home + db_dir)
    logging.info("Removing the old database directory...")
    if forreal:
        if os.path.exists(euca_home + db_root):
            shutil.rmtree(euca_home + db_root)
        else:
            logging.warning("No database dir found...proceeding with restore...")
    #logging.info("Removing old DB key...")
    #if forreal:
    #    os.remove(euca_home + key_dir + "euca.p12")
    logging.info("Initializing a clean database. This will take a while...")
    if forreal:
        os.popen("sudo " + euca_home + "usr/sbin/euca_conf --setup")
        os.popen("su %s -c '%s/usr/sbin/euca_conf --initialize'" % (euca_user, euca_home))
    logging.info("Starting PostreSQL DB...")
    if forreal:
        startdb(euca_home)
    logging.info("Restoring database from: " + backup_file)
    if forreal:
        os.popen("psql -U" + db_user + " -d postgres -p " + db_port + " -h " + euca_home + db_dir + " -f " + backup_file)
    logging.info("Shutting down PostgreSQL DB")
    if forreal:
        stopdb(euca_home)
    logging.info("Restore complete. Please start eucalyptus-cloud.")


# Start Eucalyptus PostgreSQL DB
def startdb(euca_home):
    print("su %s -c '/usr/pgsql-9.1/bin/pg_ctl start -w -s -D%s -o -h0.0.0.0/0 -p8777'" % (euca_user, euca_home + db_dir))
    os.popen("su %s -c '/usr/pgsql-9.1/bin/pg_ctl start -w -s -D%s -o -h0.0.0.0/0 -p8777'" % (euca_user, euca_home + db_dir))

# Stop Eucalyptus PostgreSQL DB
def stopdb(euca_home):
    os.popen("su %s -c '/usr/pgsql-9.1/bin/pg_ctl stop -D%s'" % (euca_user, euca_home + db_dir))


if __name__ == "__main__":
    options = get_args()
    if options.backup and options.restore:
        logging.critical("Only one of backup or restore can be specified.")
        sys.exit(1)
    else:
        if options.backup:
            do_backup(options.euca_home)
            sys.exit(0)
        elif options.restore:
            if not options.backup_file:
                logging.critical("SQL backup file not specified. Aborting")
                sys.exit(1)
            else:
                if not os.path.exists(options.backup_file):
                    logging.critical("SQL backup file not found. Aborting.")
                    sys.exit(1)
            do_restore(options.euca_home, options.backup_file, options.forreal)
            sys.exit(0)
        else:
            logging.critical("Either backup or restore must be specified")
            sys.exit(1);

