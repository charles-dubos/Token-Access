#!/usr/bin/env python3
#- *- coding:utf-8 -*-
"""This library provides functionalities for Token Access server-side actions.
It impements administrative functions for SMTP and API servers,
after loading configuration.
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
from os.path import dirname, abspath, exists
from inspect import signature
from datetime import datetime, timedelta
import logging.config, ipaddress



# Other libs

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization



# Owned libs

from lib.LibTAServer import *
from lib.LibTACrypto import HashText



# Module directives

## Creation of environment var for project & configuration loading
environ['TKNACS_PATH'] = dirname(abspath(__file__))
context.loadConfig(CONFIG_FILE)

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
        'tknAcsServers':{
            'handlers':['file_handler'],
            'level':'DEBUG',
            'propagate':True
        }
    }
})
logger = logging.getLogger('tknAcsServers')
logger.debug(f'Logger loaded in {__name__}')

# Loading database
database= context.loadDatabase()



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

    if tokens:
        logger.warning(f'While deleting user {user}:\n')
    for (token, sender) in tokens:
        logger.warning(f'\tRemoving {token} requested by {sender}')
        database.deleteToken(
            userEmail=userEmail,
            token=token,
        )

    database.delUser(
        userEmail=userEmail,
    )
    logger.debug(f'User {userEmail} removed from database')


def listUsersInDb():
    """Lists all users of the database.
    """
    return database.getUsers()


def newSelfSignedCert(
    contextStr:str,
    public_exponent:int=65537, key_size:int=2048,
    days:int=365):
    """Generates a self-signed certificate for a context.
    The context must have a host, a ssl_keyfile and a ssl_certfile.

    Args:
        contextStr (str): context (WEB_API/SMTP_SERVER)
        public_exponent (int): RSA exponent. Defaults to 65537.
        key_size (int): RSA key size. Defaults to 2048.
        days (int): validity in days from now. Defaults to 365.
    """

    logger.debug('Collecting context')
    certContext = context.__getattribute__(contextStr)

    logger.debug('Generating keypair')
    key = rsa.generate_private_key(
        public_exponent=public_exponent,
        key_size=key_size,
    )

    logger.debug('Populating certificate & self-signing')
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, certContext['host']),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'TokenAccess'),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, contextStr),
    ])
    cert = x509.CertificateBuilder(
    ).subject_name(     subject
    ).issuer_name(      issuer
    ).public_key(       key.public_key()
    ).serial_number(    x509.random_serial_number()
    ).not_valid_before( datetime.utcnow()
    ).not_valid_after(  datetime.utcnow() + timedelta(days=days)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName('localhost'),
            x509.IPAddress(ipaddress.IPv4Address('127.0.0.1')),
            ]),
        critical=False
    ).sign(
        private_key=key,
        algorithm=hashes.SHA256()
    )

    cert.public_bytes(
        encoding=serialization.Encoding.PEM
    )

    logger.debug('Checking existing certificate')
    print(f'{str(cert)} generated.')
    if exists(certContext['ssl_keyfile']) \
    or exists(certContext['ssl_certfile']):
        if input('{ssl_keyfile} or {ssl_certfile} already exists, '
            'overwrite it? (yes/no)'.format(
                ssl_keyfile=certContext['ssl_keyfile'],
                ssl_certfile=certContext['ssl_certfile'],
            )
        )!='yes':
            raise UserWarning('No certificate changes done')

    logger.debug('Exporting private key')
    with open(certContext['ssl_keyfile'], mode='wb') as fd:
        fd.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
        )

    logger.debug('Exporting public certificate')
    with open(certContext['ssl_certfile'], mode='wb') as fd:
        fd.write(
            cert.public_bytes(encoding=serialization.Encoding.PEM)
        )

    print('Please relaunch the server to update certificates.')
    return cert



# Gentle intro when loading this lib...

print("""\
Hello admin!\n\n{intro}\nIt includes:
 - {funcs}""".format(
    intro=__doc__,
    funcs="\n - ".join([ method + str(signature(globals()[method])) + ':\n\t' + str(globals()[method].__doc__).splitlines()[0]
        for method in globals()
            if not method.startswith('_') 
            and callable(globals()[method])
            and globals()[method].__module__ == __name__]),
)
)
