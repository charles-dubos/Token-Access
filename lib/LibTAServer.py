#!/usr/bin/env python3
#- *- coding:utf-8 -*-
"""This module contains functionalities for Token Access server

- EmailAdress class to parse email addresses
- Context class to manage the configuration file
"""
__author__='Charles Dubos'
__license__='GNUv3'
__credits__='Charles Dubos'
__version__="0.1.0"
__maintainer__='Charles Dubos'
__email__='charles.dubos@telecom-paris.fr'
__status__='Development'



# Built-in

from configparser import ConfigParser
from os.path import exists, expandvars
from os import environ, popen
from logging import getLogger



# Owned libs

import lib.LibTADatabase as dbManage



# Module directives

## Load logger
logger=getLogger('tknAcsServers')
logger.debug(f'Logger loaded in {__name__}')

## Constants
CONFIG_FILE="${TKNACS_PATH}/tokenAccess.conf"

DEFAULT_CONFIG="""\
[GLOBAL]
; This section gives common configuration items (for logging and HOTP, shared
; between the API server, the SMTP server and eventually passed to the client).
; window is the half-size of HOTP-window allowed by client researches.
window=50
; Logging elements, including file path and level.
logging=${TKNACS_PATH}/tknAcs.log
log_level=WARNING


[WEB_API]
; API server listening host & port
host=127.0.0.1
port=8443
; SSL key & certificate for HTTPS connection
ssl_keyfile=${TKNACS_PATH}/certs/TokenAccessAPI.key
ssl_certfile=${TKNACS_PATH}/certs/TokenAccessAPI.pem


[SMTP_SERVER]
; SMTP server listening host & port
host=127.0.0.1
port=2525
; SSL key & certificate for SMTPS connection
ssl_keyfile=${TKNACS_PATH}/certs/TokenAccessSMTP.key
ssl_certfile=${TKNACS_PATH}/certs/TokenAccessSMTP.pem
; TLS server mode (STARTTLS for STARTTLS over SMTP or SSL for SMTPS)
ssl_mode=SSL
; The behavior sets what to do if no or bad token given, it can be:
; RELAY, SUBJECT_TAGGED_RELAY, FIELD_TAGGED_RELAY, REQUEST_TOKEN, REFUSE, DROP
behavior=RELAY

[SMTP_MDA]
; SMTP mail delivery agent to forward the validated incoming messages.
; If None, only displays the message and don't relays it to a MDA...
mda_host=None
mda_port=None


[DATABASE]
; You can use sqlite3 or mysql for user database.
db_type=sqlite3
; 
;        -=SQLITE 3 CONFIGURATION=-
;   SQLite3 is not recommended (no security on database content), but easy to
;   use.
; Sqlite3 works with a file. If this files does not exists, it creates it.
sqlite3_path=${TKNACS_PATH}/tokenAccess.db
; 
;        -=MYSQL CONFIGURATION=-
;   MySQL is more powerfull. However, you need to install a database server.
;   On Linux, you can use mariadb-server. You should then execute 
;   'mysql_secure_installation' for security sake.
; Mysql connector needs a database name (automagically created if not exists)
; and a hostname.
mysql_db=tokenAccess
mysql_host=localhost
; You need also to give the user & pass to access database (root access not 
; recommended).
mysql_user=admin
mysql_pass=Password


[CRYPTO]
; This section contains advanced cryptography configurations.
; BE ATTENTIVE IF CHANGING THESE VALUES
[elliptic]
; Elliptic curve must be supported by cryptography.hazmat.primitives.assymetric
; (x25519 or x448, default to x25519)
curve=x25519
[hash]
; ExportBase must be supported by base64 (default to b64)
base=b64
; Hash function must be supported by cyptography.hazmat.primitives.hashes
; (default to SHA256)
algorithm=SHA256
[hotp]
; Length of HOTP in digits (default to 6)
length=6


; The ${TKNACS_PATH} environment variable is the current root directory, set by
; the servers when launched. It can be used in all path variables
"""



# Classes

class EmailAddress:
    extensions=[]
    
    def __init__(
        self,
        name:str=None,
        user:str=None,
        extensions:list=[],
        domain:str=None):
        """Parses e-mail adresses into user/extension/domain.

        Args:
            name (str, optional): Displayed name. Defaults to None.
            user (str, optional): email address user. Defaults to None.
            extensions (list, optional): email adress extensions. Defaults to empty list.
            domain (str, optional): email adress domain. Defaults to None.
        """
        self.displayedName=name
        self.user=user
        self.extensions=extensions
        self.domain=domain

    
    def parser(self, address: str):
        """Parses an email address given the folowing formats: 
        - user[+extension[s]]@domain.
        - displayedName<user+extensions@domain>.

        Args:
            address (str): e-mail address (explicit or with <>delimiters)

        Raises:
            SyntaxError: Unexploitable string syntax

        Returns:
            EmailAdress: object containing
                user: str with user name 
                extensions: list of str extensions folowing a + sign
                domain: str with domain name 
        """
        
        if address.count('<') != 0 or address.count('>') != 0:
            if address.count('<') != 1 or address.count('>') != 1:
                raise SyntaxError
            if address.find('>', address.find('<')) == -1:
                raise SyntaxError
            self.displayedName = address[:address.find('<')]
            address = address[address.find('<')+1:
                address.find('>', address.find('<'))]

        splitAddress = address.split('@')
        if len(splitAddress) != 2:
            raise SyntaxError
        splitUsername = splitAddress[0].split('+')
        
        self.user = splitUsername[0]
        self.extensions = splitUsername[1:]
        self.domain = splitAddress[1]
        return self

    
    def getEmailAddr(self, enableExt=False) -> str:
        """Returns the email address with format user[+extensions]@domain

        Args:
            enableExt (bool, optional): Return the address with extensions. Defaults to False.

        Raises:
            TypeError: Domain or user not given

        Returns:
            str: email address
        """
        if self.user is None or self.domain is None:
            raise TypeError("user and domain cannot be 'None'")
        output = self.user
        if enableExt:
            for extension in self.extensions:
                output = output + "+" + extension
        output = output + "@" + self.domain
        return output

    
    def getFullAddr(self, enableExt=False) -> str:
        """Returns email address formatted with displayed name if exists (displayedName <user@domain>).

        Args:
            enableExt (bool, optional): Eanbles extensions in returned address. Defaults to False.

        Returns:
            str: the email address
        """
        output = self.getEmailAddr(enableExt=enableExt)
        if self.displayedName is not None:
            output = self.displayedName + "<" + output + ">"
        return output


class Context:
    contexts=[
        'GLOBAL',
        'WEB_API',
        'SMTP_SERVER',
        'SMTP_MDA',
        'DATABASE',
        'elliptic',
        'hash',
        'hotp',
    ]
    def __init__(self):
        """This class loads the configurations for given contexts.
        It initiates the contexts to empty dicts.
        """
        for context in self.contexts:
            self.__setattr__(context, {})


    def loadConfig(self,filename:str):
        """Load specific contexts defined in configuration file, and save it in the
        contexts defined in this module.

        Args:
            filename (str): path name of config file.
        """
        filename=expandvars(filename)
        if not exists(filename):
            logger.warning(f'Cannot find {filename}, creating a default one.')
            with open(filename,"w") as file:
                    file.write(DEFAULT_CONFIG)

        # Loading config
        logger.debug(f'Loading config from {filename}.')
        config=ConfigParser(comment_prefixes=";")
        config.read(filename)

        for context in self.contexts:
            logger.debug(f'\tLoading {context} context:')
            resolEnvVar=dict(config[context])
            for key, value in resolEnvVar.items():
                if value.find('$') != -1:
                    resolEnvVar[key]=expandvars(value)
                    logger.debug(f'Resolving {resolEnvVar[key]}')
            self.__setattr__(context, resolEnvVar)
            logger.debug('\t\t{}'.format(self.__getattribute__(context)))

    
    def loadDatabase(self):
        """Loads a database as specified in config and returns it.

        Returns:
            dbManage._SQLDB: database
        """
        db_type = self.DATABASE['db_type']
        db_class = db_type.title() + 'DB'
        logger.debug(f'Loading {db_type} database (instance of {db_class})')
        return getattr(dbManage, db_class)(**self.DATABASE)



# Late-defined directives

## Creation of default context
context = Context()
