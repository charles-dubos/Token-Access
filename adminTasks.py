#!/usr/bin/env python3
#- *- coding:utf-8 -*-
"""This module provides functionalities for Token Access server-side actions

It impements administrative functions for SMTP and API servers, after loading configuration.
"""
__author__='Charles Dubos'
__license__='GNUv3'
__credits__='Charles Dubos'
__version__="0.1.0"
__maintainer__='Charles Dubos'
__email__='charles.dubos@telecom-paris.fr'
__status__='Development'


# Built-in
from os import environ, system
from os.path import dirname, abspath
import logging.config


# Owned libs
from lib.LibTAServer import *
from lib.LibTACrypto import HashText
import lib.LibTADatabase as dbManage


# Module directives

## Creation of environment var for project & configuration loading
environ['TKNACS_PATH'] = dirname(abspath(__file__))
context.loadFromConfig(CONFIG_FILE)
setattr(self, 'process_name', 'ADMIN')

## Creating specially-configured logger for admin tasks 
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers':False,
    'formatters':{
        'default_formatter':{
            'format':'%(levelname)s:  %(asctime)s  [%(process)d][%(filename)s][%(funcName)s]  %(message)s',
        },
    },
    'handlers':{
        "file_handler":{
            'class':'logging.FileHandler',
            'filename':context.GLOBAL['logging'],
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


## Load logger
logger = logging.getLogger('tknAcsAPI')


## Opening Database
logger.debug('Opening {} database:'.format( context.DATABASE['db_type'] ))
if context.DATABASE['db_type'] in ["sqlite3", "mysql"]:
    database = getattr(
        dbManage,
        context.DATABASE['db_type'] + "DB"
    )(**context.DATABASE)
else:
    raise FileNotFoundError


# Functions
class test:
    pass


def addUserInDb(userEmail:str):
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

print("""Hello admin!
It impements administrative functions for common SMTP and API servers database,
after loading configuration: be particularly vigilent when using it!
""")
