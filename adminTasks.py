"""Admin tasks for database:
   -------------------------
Impements administrative functions for SMTP and API servers, after loading configuration:
- addUserToDb: adds a user to the configured DB
- delUserInDb: removes a user in the configured DB
"""


# PROJECT PERIMETER
## Creation of environment var for project
from os import environ
from os.path import dirname, abspath
environ['TKNACS_PATH'] = dirname(abspath(__file__))
environ['TKNACS_CONF'] = environ["TKNACS_PATH"] + "/tokenAccess.conf"


# CONFIGURATION
## Loading conf file
from lib.utils import CONFIG, LOGGER, EmailAddress


## WebAPI variables

DOMAINS = CONFIG.get('GLOBAL','domains').split(',')
DBTYPE = CONFIG.get('DATABASE','type')
DATABASE = CONFIG.get('DATABASE','SQLdatabase')


# Inner dependances

import lib.cryptoFunc as cryptoFunc
import lib.dbManage as dbManage
from lib.policy import Policy

# LAUNCH API

LOGGER.debug(f'Opening {DBTYPE} database: {DATABASE}')
if DBTYPE == "sqlite3":
    database = dbManage.sqliteDB(dbName=DATABASE,defaultDomain=DOMAINS[0])
elif DBTYPE == "mysql":
    database = dbManage.mysqlDB(dbName=DATABASE, defaultDomain=DOMAINS[0])
else:
    raise FileNotFoundError


def addUserToDb(user:str, password:str, domain:str=None):
    """Adds a user to the database (if domain is none, use the database domain)

    Args:
        user (str): user name
        password (str): user password (not hashed)
        domain (str, optional): user domain. Defaults to None.
    """
    database.addUser(
        user=user,
        domain=domain,
        password=cryptoFunc.HashText(password).getHash()
    )


def delUserInDb(user:str, domain:str=None):
    """Removes a user in the database. If token are defined, also deletes all existing tokens.

    Args:
        user (str): user name
        domain (str, optional): user domain. Defaults to None.
    """
    tokens = database.getAllTokensUser(user=user, domain=domain)

    for (token, sender) in tokens:
        LOGGER.warning(f"Deleting user {user}: REMOVING TOKEN {token} REQUESTED BY {sender}")
        database.deleteToken(
            user=user,
            token=token,
            domain=domain
        )

    database.delUser(
        user=user,
        domain=domain
    )
