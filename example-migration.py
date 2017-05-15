import ipdb
import pdb
from sqlalchemy import update
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import migration_db
from db import Client, Grant, Token, User


class migrate(object):
    version = "v1.0.0.0"
    description = "add email column to user table"
    db_path = "/path/to/foo.db"

    UPGRADE = {
"sequence": [
    {"sql": """ALTER TABLE user ADD COLUMN email VARCHAR(40);"""},
    ## need to move this migrate_version to this projects db
    {"sql": """
CREATE TABLE migrate_version (
	id INTEGER NOT NULL,
	git_version VARCHAR(20),
	migration_filename TEXT,
	migration_direction VARCHAR(20),
	migration_timestamp VARCHAR(20),
	PRIMARY KEY (id)
);
"""},
    ]
}

    DOWNGRADE = {
"sequence": [
    # to drop a column we have to do the following
    # drop column begin
    {"sql": """DROP TABLE user;"""},
    {"sql": """
CREATE TABLE user (
	id INTEGER NOT NULL, 
	username VARCHAR(40), 
	PRIMARY KEY (id), 
	UNIQUE (username)
);
""" },
    {"sql": """
ATTACH '{0}' as original;
INSERT INTO user SELECT id, username FROM original.user;
""" },
    ]
}


    def __init__(self):
        pass


    def pre_upgrade(self):
        """
        This is run prior to the UPGRADE
        """
        # This will be run prior to the upgrade
        # You edit this at your will
        return True


    def post_upgrade(self):
        """
        This is run post to the UPGRADE
        """
        # This will be run prior to the upgrade
        # You edit this at your will
        print "POST-UPGRADE"
        try:
            users = User.query.filter_by()
            for user in users:
                email = '%s@%s' % (user.username, 'foo.bar')
                db.session.query(User).filter_by(id=user.id).update({"email": email})
                db.session.commit()
        except Exception as e:
            print e, e.message
            return False
        return True


    def pre_downgrade(self):
        """
        This is run prior to the DOWNGRADE
        """
        # This will be run prior to the downgrade
        # You edit this at your will
        print "PRE-DOWNGRADE"
        return True


    def post_downgrade(self):
        """
        This is run post to the DOWNGRADE
        """
        # This will be run prior to the downgrade
        # You edit this at your will
        print "POST-DOWNGRADE"
        return True


def main():
    obj = migrate()
    obj.post_migrate()


if __name__ in "__main__":
    main()
