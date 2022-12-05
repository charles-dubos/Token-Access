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


# Load logger
import logging.config
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers':False,
    'formatters':{
        'default_formatter':{
            'format':'%(levelname)s:%(asctime)s\t%(message)s',
        },
    },
    'handlers':{
        "file_handler":{
            'class':'logging.FileHandler',
            'filename':'adminTasks.log',
            'encoding':'utf-8',
            'formatter':'default_formatter',
        },
    },
    'loggers':{
        'tknAcsAPI':{
            'handlers':['file_handler'],
            'level':'DEBUG',
            'propagate':True
        }
    }
})
logger = logging.getLogger('tknAcsAPI')


# Load config
from lib.LibTAServer import *
context.loadFromConfig(CONFIG_FILE)


# Inner dependances
from lib.LibTACrypto import HashText
import lib.LibTADatabase as dbManage


# Opening Database
logger.debug('Opening {} database:'.format( context.DATABASE['db_type'] ))
if context.DATABASE['db_type'] in ["sqlite3", "mysql"]:
    database = getattr(
        dbManage,
        context.DATABASE['db_type'] + "DB"
    )(**context.DATABASE)
else:
    raise FileNotFoundError


def addUserToDb(userEmail:str):
    """Adds a user to the database

    Args:
        userEmail (str): user email
    """
    database.addUser(
        userEmail=userEmail,
    )


def delUserInDb(userEmail:str):
    """Removes a user in the database.
    If token are defined, also deletes all existing tokens.

    Args:
        userEmail (str): user email
    """
    tokens = database.getAllTokensUser(userEmail=userEmail)

    for (token, sender) in tokens:
        logger.warning(f"Deleting user {user}: Removing {token} requested by {sender}")
        database.deleteToken(
            userEmail=userEmail,
            token=token,
        )

    database.delUser(
        userEmail=userEmail,
    )
