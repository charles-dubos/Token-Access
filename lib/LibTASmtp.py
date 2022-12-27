#!/usr/bin/env python3
#- *- coding:utf-8 -*-
"""This module contains functionalities for Token Access server
"""
__author__='Charles Dubos'
__license__='GNUv3'
__credits__='Charles Dubos'
__version__="0.1.0"
__maintainer__='Charles Dubos'
__email__='charles.dubos@telecom-paris.fr'
__status__='Development'


# Built-in

from logging import getLogger
from os.path import exists
import asyncio, ssl



# Other libs
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP
from aiosmtpd.handlers import Proxy
from requests import get as getRequest



# Owned libs

from lib.LibTAServer import *



# Module directives

## Constants
ALLOWED_BEHAVIORS = {
    'RELAY': 'TransparentRelay', # relays the email as is
    # 'SUBJECT_TAGGED_RELAY': SubjectTagRelay, # relays the email with adding a tag in subject
    # 'FIELD_TAGGED_RELAY': FieldTagRelay, # relays the email with adding a tag in tags
    'REQUEST': 'RequestToken', # request a token for user
    'REFUSE553': 'ResponseRefuse', # response with an automatic message requesting a token
    'REFUSE': 'BasicRefuse', # Refuses the email with error 550
    # 'DROP': DropRefuse, # silently drops the email
}
## RFC 5321-compliant responses codes
OK='250 OK'
OKNOTOKEN='251-Message relayed with no token\r\n'\
    '251 Next time, please request a HOTP token'
ERRUNAVAILABLE='550 Mailbox not found'
ERRNOTOKEN='553-Policy does not allow direct access to Mailbox\r\n'\
    '553 Please request a valid HOTP token'
ERRBADTOKEN='553-Invalid token\r\n'\
    '553 Please request a valid HOTP token'

## Load logger
logger=getLogger('tknAcsServers')
logger.debug(f'Logger loaded in {__name__}')

## Load database
database=context.loadDatabase()



# Classes

class TknAcsRelay(Proxy):
    validity = None

    async def handle_RCPT(
        self,
        server,
        session,
        envelope,
        address,
        rcpt_options):
        try:
            logger.debug(f'Recieving msg to {address}')
            rcptAddress=EmailAddress().parser(
                address=address)
            hotp = None if not rcptAddress.extensions \
                    else rcptAddress.extensions[0]

            logger.debug(f"User: {rcptAddress.getEmailAddr()}")
            logger.debug(f"HOTP: {type(hotp)}")

            # Checks that users belongs to the server
            assert database.isInDatabase(userEmail=rcptAddress.getEmailAddr()),\
                ERRUNAVAILABLE
            
            # Checks that there is this token for this user and this sender
            if hotp:
                self.validity = database.isTokenValid(
                    userEmail=rcptAddress.getEmailAddr(),
                    sender=envelope.mail_from,
                    token=hotp
                )
                
                if self.validity:
                    logger.info('Purging {userEmail} from used {token}'.format(
                        userEmail=rcptAddress.getEmailAddr(),
                        token=hotp,
                    ))
                    database.deleteToken(
                        userEmail=rcptAddress.getEmailAddr(),
                        token=hotp,
                    )
            else:
                self.validity = False

        except Exception as e:
            logger.debug(repr(e))
            return e
        envelope.rcpt_tos.append(address)
        return OK

    async def handle_DATA(
        self,
        server,
        session,
        envelope):
        if self._hostname == 'None':
            # Remove consummed TOKEN
            print('Message from %s' % envelope.mail_from)
            print('Message options %s' % str(envelope.mail_options))
            print('Message for %s' % envelope.rcpt_tos)
            print('Message data:\n')
            for ln in envelope.content.decode('utf8', errors='replace').splitlines():
                print(f'> {ln}'.strip())
            print()
            print('End of message')

            return '250 Message accepted for delivery'
        else:
            await super().handle_DATA(
                server=server,
                session=session,
                envelope=envelope,
            )


class TransparentRelay(TknAcsRelay):
    """This handler class relays the message.
    It only logs that the message has no token, and respond with a 251 error
    code instead of 250.
    """
    
    async def handle_DATA(
        self,
        server,
        session,
        envelope):
        supResp = await super().handle_DATA(
            server=server,
            session=session,
            envelope=envelope)

        if not self.validity:
            logger.info(f'Msg from {envelope.mail_from} '
                f'to {envelope.rcpt_tos} accepted with no token')
        
        return supResp if self.validity else OKNOTOKEN


class ResponseRefuse(TknAcsRelay):
    """This handler class refuses the message if bad or no token with an 
    explicit response.
    """
    async def handle_RCPT(
        self,
        server,
        session,
        envelope,
        address,
        rcpt_options):

        supResp = await super().handle_RCPT(
            server=server,
            session=session,
            envelope=envelope,
            address=address,
            rcpt_options=rcpt_options)

        if self.validity:
            return supResp
        else:
            logger.info(f'553: Refusing message from {envelope.mail_from}'
                f' to {envelope.rcpt_tos}')
            return ERRNOTOKEN if self.validity is None else ERRBADTOKEN


class BasicRefuse(TknAcsRelay):
    """This handler class refuses the message with a 550 unavailable response.
    """
    async def handle_RCPT(
        self,
        server,
        session,
        envelope,
        address,
        rcpt_options):

        supResp = await super().handle_RCPT(
            server=server,
            session=session,
            envelope=envelope,
            address=address,
            rcpt_options=rcpt_options)

        if self.validity:
            return supResp
        else:
            logger.info(f'550:Refusing message from {envelope.mail_from} '
                f'to {envelope.rcpt_tos}')
            return ERRUNAVAILABLE


class RequestToken(TknAcsRelay):
    """This handle class automatically requests a token for the incoming message
    if no token in email recipient. 
    """
    async def handle_RCPT(
        self,
        server,
        session,
        envelope,
        address,
        rcpt_options):

        supResp = await super().handle_RCPT(
            server=server,
            session=session,
            envelope=envelope,
            address=address,
            rcpt_options=rcpt_options)
        
        recipient = EmailAddress().parser(address=envelope.rcpt_tos[0])

        if self.validity:
            return supResp
        elif self.validity == None \
            or len(recipient.extensions)!=0:
            logger.info(f'550:Refusing message from {envelope.mail_from} '
                f'to {recipient.getEmailAddr()}')
            return ERRUNAVAILABLE
        else:
            logger.debug('Request token to WebAPI')
            try:
                token = getRequest(
                    url= 'http{ssl}://{host}{port}/requestToken'.format(
                        ssl='s' if exists(context.WEB_API['ssl_certfile']) else '',
                        host=context.WEB_API['host'],
                        port=(':{}'.format(context.WEB_API['port']))\
                            if context.WEB_API['port'] else '',
                    ),
                    params = {
                        'sender':envelope.mail_from,
                        'recipient':address,
                    },
                    verify=context.WEB_API['ssl_certfile']\
                        if exists(context.WEB_API['ssl_certfile']) else False,
                ).json()['token']
                logger.debug(f'Got {token}')
                newAddress = EmailAddress().parser(address=address)
                newAddress.extensions.insert(0, token)
                envelope.rcpt_tos = [
                    newAddress.getEmailAddr(withExt=True)
                ]
                logger.debug(f'New address generated: {newAddress.getEmailAddr(withExt=True)}')
                logger.info('Purging {userEmail} from used {token}'.format(
                    userEmail=newAddress.getEmailAddr(withExt=False),
                    token=token,
                ))
                database.deleteToken(
                    userEmail=newAddress.getEmailAddr(withExt=False),
                    token=token,
                )
                return OKNOTOKEN
            except:
                return ERRBADTOKEN


# Functions

def launchSmtpServer(
    host:str,
    port:str,
    mda_host:str,
    mda_port:str,
    ssl_certfile=None,
    ssl_keyfile=None,
    ssl_mode=None,
    behavior='REQUEST_TOKEN',
    **kwargs):
    port = int(port)

    logger.debug(f'Using handler {behavior}')

    ctrlKwargs = {
        'handler':  (globals()[ALLOWED_BEHAVIORS[behavior]])(
            remote_hostname=mda_host, 
            remote_port=mda_port,
        ),
        'hostname': host,
        'port':     port,
    }

    ActiveController = Controller
    if ssl_mode in ['SSL', 'STARTTLS']:
        assert exists(ssl_certfile) and exists(ssl_keyfile), \
            'No SSL keys find'
        logger.debug('SSL Context identified for SMTP')

        sslContext = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        sslContext.load_cert_chain(
            keyfile=ssl_keyfile,
            certfile=ssl_certfile,
        )
    
    if ssl_mode == 'STARTTLS':
        logger.debug('Enabling STARTTLS required')
        class ControllerTls(Controller):
            def factory(self):
                return SMTP(
                    self.handler,
                    require_starttls=True,
                    tls_context=sslContext
                )
        ActiveController=ControllerTls
        
    elif ssl_mode == 'SSL':
        logger.debug('Enabling SSL for SMTPS')
        ctrlKwargs.update({
            'ssl_context':      sslContext,
        })


    TAController = ActiveController(**ctrlKwargs)

    try:
        TAController.start()
        while input(
            f"SMTP server Listening on {host}:{port}, QUIT to stop it.\n"
            ).lower() != "quit":
            pass
    finally:
        TAController.stop()

