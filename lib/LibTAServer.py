#!/usr/bin/env python3
#- *- coding:utf-8 -*-
"""This module contains functionalities for Token Access server

- EmailAdress class to parse email addresses
- Context class to manage the configuration file
- ParseXML class to parse XML librairies that containts SQL files
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
from xml.dom.minidom import parse as domParser
from logging import getLogger


# Module directives
## Load logger
logger=getLogger('tknAcsAPI')


## Constants
CONFIG_FILE="${TKNACS_PATH}/tokenAccess.conf"


DEFAULT_CONFIG="""
[GLOBAL]
logging=${TKNACS_PATH}/tknAcs.log
log_level=WARNING

[WEB_API]
; API host:port and SSL HTTPS connection parameters
host=127.0.0.1
port=8443
ssl_keyfile=${TKNACS_PATH}/certs/TokenAccessAPI.pem
ssl_certfile=${TKNACS_PATH}/certs/TokenAccessAPI.pem

[SMTP_SERVER]
host=127.0.0.1
port=465
ssl_keyfile=${TKNACS_PATH}/certs/TokenAccessSMTP.pem
ssl_certfile=${TKNACS_PATH}/certs/TokenAccessSMTP.pem


[DATABASE]
; You can choose to use sqlite3 or mysql for database: 
db_type=sqlite3

; - SQLite3 is not recommended (no security on database), but easy to use
; - mySQL is more powerfull. You need to install a database server
;   On Debian, the installation can be done with 'apt install mariadb-server'
;   Then you have to execute 'mysql_secure_installation'
; SQLdatabase is the database file (sqlite) or name (mysql)
sqlite3_path=${TKNACS_PATH}/tokenAccess.db

; mysql-specific configurations
mysql_db=tokenAccess
mysql_host=localhost
mysql_user=admin
mysql_pass=Password


[CRYPTO]
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
"""


# Classes

class EmailAddress:
    extensions=[]
    
    def __init__(self, name:str=None, user:str=None, extensions:list=[], domain:str=None):
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

    
    def parser(self,address: str):
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


class ParseXML:
    def __init__(self,xmlFile:str):
        """Parses an XML file starting with a <command> data container.

        Args:
            xmlFile (str): xml filename to parse 
        """
        self._dom=domParser(file=xmlFile).getElementsByTagName('command')[0]
    
    def extract(self,path:str) -> str:
        """Get the element of the parsed XML file.

        Args:
            path (str): Path to the wanted content separed with '/' 

        Returns:
            str: content of the precised path.
        """
        pathList = path.split(sep="/")
        dom = self._dom
        for domLevel in pathList:
            dom = dom.getElementsByTagName(domLevel)[0]
        return dom.firstChild.nodeValue


class Context:
    contexts=[
        'GLOBAL',
        'WEB_API',
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


    def loadFromConfig(self,filename:str):
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


# Late-defined directives

## Creation of default context
context = Context()