#import ipdb
#import pdb
import sys, re, os, docopt
import datetime, time
import shutil
import docopt
import subprocess
from migration_config import CONFIG

shelp = """

PURPOSE: Migrate sqlite3 schema up or down using a python file as the guide

Usage: {0}
  [--python-migration-file=path]
  [--action=action]
  [--dry-run=boolean]

OPTIONS:
  -h --help
  --python-migration-file=<path>  Path to migration python file which consists
                                  of two dictionaries.  UPGRADE, DOWNGRADE
  --action=<value>  upgrade, downgrade. [default: None]
  --dry-run=<value>  Boolean if true only generate the schema sql [default: True]

EXAMPLE:
  * UPGRADE
    * PYTHONPATH=.:/path/to/model-dir python migrate.py --python-migration-file=/path/to/migration/file.py --action=upgrade --dry-run=False
  * DOWNGRADE
    * PYTHONPATH=.:/path/to/model-dir python migrate.py --python-migration-file=/path/to/migration/file.py --action=downgrade --dry-run=False

REALWORLD EXAMPLE
  * UPGRADE
    * PYTHONPATH=.:/foo/bar/models python migrate.py --python-migration-file=/foo/bar/schema/migrations/v1_1_0_0.py --action=upgrade --dry-run=True
      * with --dry-run=True you get a view of the sql to be executed
    * PYTHONPATH=.:/foo/bar/models python migrate.py --python-migration-file=/foo/bar/schema/migrations/v1_1_0_0.py --action=upgrade --dry-run=False
      * with --dry-run=False run the actual migration, in this case an upgrade

REQUIREMENTS
* Use of PYTHONPATH so we can load the version .py files
* user needs to be versed in sqlite3 and sql and understand the caveats of sqlite3
  such as sqlite3 does not have a drop column ability.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
""".format(__file__)


def run(**kwargs):
    options = kwargs['options']
    dry_run = options['--dry-run']
    if dry_run == 'True': dry_run = True
    if dry_run == 'False': dry_run = False
    migration_file = options['--python-migration-file']
    action = options['--action'].upper()

    # load the migration file
    try:
        tmp = os.path.basename(migration_file)
        tmp = tmp.split('.py')[0]
        migration_info = __import__(tmp, fromlist=[''])
        obj_migration_info = migration_info.migrate()
    except Exception as e:
        usage_msg(msg="%s: %s" % (e, e.message))

    try:
        migration_action=getattr(obj_migration_info, action)
        migration_db = obj_migration_info.db_path
        migration_sequence = migration_action['sequence']
    except Exception as e:
        usage_msg(msg="%s: %s" % (e, e.message))

    if not os.path.exists(migration_db):
        usage_msg(msg="DB File %s: does not exist." % (migration_db))

    db_archived = backup_db(db_path=migration_db, archive=True)
    db_backup = backup_db(db_path=migration_db)

    cmds = []
    for process in migration_sequence:
        try:
            sql = process['sql']
        except Exception as e:
            usage_msg(msg="%s: %s" % (e, e.message))

        if re.search(r'attach .* as original', sql, re.I):
            sql = sql.format(db_backup)  # fill in the {0}
        cmds.append(sql)
    try:
        tmp_dir = CONFIG.get('tmp_dir', '/tmp')
        cmds_file = '%s/cmds.sql' % tmp_dir
        fh = open(cmds_file, 'w')
        for cmd in cmds:
            fh.write(cmd.strip('\n').strip('\r')+'\n')
        fh.close()
    except Exception as e:
        usage_msg(msg="%s: %s" % (e, e.message))

    dothis = ['sqlite3', '{0}'.format(migration_db), '<', cmds_file]
    pre_post_methods = get_pre_post_methods(the_class=obj_migration_info)
    methods_to_use = {k:v for k,v in pre_post_methods.iteritems() if re.search(action, k, re.I)}
    pre_methods = {k:v for k,v in methods_to_use.iteritems() if re.search('pre', k, re.I)}
    post_methods = {k:v for k,v in methods_to_use.iteritems() if re.search('post', k, re.I)}
    if dry_run:
        print " PRE METHODS:", pre_methods.keys()
        print "     DRY RUN: This is the command that would have been run:", ' '.join(dothis)
        print "POST METHODS:", post_methods.keys()
        print "Review:", cmds_file, "for details."
    else:
        print "RUNNING PRE-METHODS:", pre_methods.keys()
        for key, obj in pre_methods.iteritems():
            result = obj()
            if result == False:
                print "ABORTING, method:{0} failed".format(key)
                usage_msg()

        print "RUNNING:", action, "generated from:", migration_file, "into:", cmds_file
        print ' '.join(dothis)
        try:
            subprocess.call(' '.join(dothis), shell=True)
        except Exception as e:
            print "{0} has failed, remember you have an archive of the db at:{1}".format(action, db_archived)
            usage_msg(msg="%s: %s" % (e, e.message))

        print "RUNNING POST-METHODS:", post_methods.keys()
        for key, obj in post_methods.iteritems():
            result = obj()
            if result == False:
                print "ABORTING, method:{0} failed".format(key)
                usage_msg()

        print "UPDATING migrate_version Table:", post_methods.keys()
        from db import db
        # another way to test table existence is 
        # db.engine.dialect.has_table(db.engine, 'migrate_version')
        if 'migrate_version' in db.metadata.tables.keys():
            from db import Migrate_Version
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            git_version = obj_migration_info.version
            migrate_version = Migrate_Version(
                git_version = git_version,
                migration_filename = migration_file,
                migration_direction = action,
                migration_timestamp = now,
            )
            db.session.add(migrate_version)
            db.session.commit()
        else:
            print "WARNING: table:'migrate_version' does not exist, WHY???"


def get_pre_post_methods(**kwargs):
    the_class = kwargs['the_class']
    results = {}
    for action in ['upgrade', 'downgrade']:
        for the_type in ['pre', 'post']:
            key = '{0}_{1}'.format(the_type, action)
            obj = test_def(the_class=the_class, def_name=key)
            if obj is not None:
                results.update({key: obj})
    return results


def test_def(**kwargs):
    the_class = kwargs['the_class']
    def_name = kwargs['def_name']
    obj = getattr(the_class, def_name)
    if callable(obj):
        return obj
    return None


def backup_db(**kwargs):
    db_path=kwargs['db_path']
    archive = kwargs.get('archive')
    dest = kwargs.get('destination_path', CONFIG.get('tmp_dir'))
    if archive is None:
        shutil.copy2(db_path, dest)
        return "{0}/{1}".format(dest, os.path.basename(db_path))

    if archive == True:
        now = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
        this_dir = os.path.abspath(__file__)
        this_dir = os.path.dirname(this_dir)
        archive_dir = "{0}/{1}".format(this_dir, "archive")
        filename = "{0}-{1}".format(os.path.basename(db_path), now)
        dest = "{0}/{1}".format(archive_dir, filename)
        shutil.copy2(db_path, dest)
        return dest


def usage_msg(**kwargs):
    print shelp
    if kwargs.get('msg'):
        print kwargs['msg']
    print "ABORTING"
    sys.exit(1)


def main(**kwargs):
    options = kwargs['options']
    if not os.path.exists(options['--python-migration-file']):
        usage_msg(msg="--python-migration-file:%s does not exist" %
                options['--python-migration-file'])
    if options['--action'].upper() not in ['UPGRADE', 'DOWNGRADE']:
        usage_msg(msg="--action value bad.")
    run(options=options)


if __name__ in "__main__":
    options = docopt.docopt(shelp)
    main(options=options)
