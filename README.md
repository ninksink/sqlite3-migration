# WORK IN PROGRESS
I will have something more useful soon

# sqlite3-migration

Schema migration tool for sqlite3.  Yes, alembic is great, until you have to redefine a column, sqlite3 does not support that.

Schema migration tool.  Works both up and down.  I know. alembic would do just fine and it does great, until you have to redefine a column or drop a column, then sqlite3 causes a failure, so this little project is here to help.  It's a full, up and down migration and it archives your schema's before each event.

# SYSTEM REQUIREMENTS
sqlalchemy


# USER REQUIREMENTS
* Knowledge of sql
* Knowledge of sqlite3 and it's caveats, such as it cannot *drop* or *alter existing* columns.
   * Yes, the horror.  What you have to do is drop the table and recreate it.
      * Now you see the advantage of archiving.  With archiving we open the archive
        and run code to pull data from the archive back into the columns that were not altered.
* Knowledge of python
   * This tool is meant to give you, the developer a lot of leeway in making special migrations and a knowledge of python will help you immensely, especially when concerning pre and post migration data migration efforts.  Such as when you have to drop a column by recreating the db, you can attach an archive that is copied to /tmp and import data into your new db.

## Example:
```
sqlite3 /path/to/db
sqlite> .schema user
CREATE TABLE user (
	id INTEGER NOT NULL, 
	username VARCHAR(40), 
    email VARCHAR(40), 
	PRIMARY KEY (id), 
	UNIQUE (username)
);
```
In your `v0.0.1.py` you will have then this
```
    DOWNGRADE = {
"sequence": [
    # to drop the email column we have to do the following
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

```
Above the `{0}` will be the path to a copy of your archived db placed in `/tmp/` prior to this operation
