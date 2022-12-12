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
from aiosmtpd.handlers import Debugging



# Owned libs

import lib.LibTADatabase as dbManage
from lib.LibTAServer import EmailAddress



# Module directives

## Load logger
logger=getLogger('tknAcsServers')
logger.debug(f'Logger loaded in {__name__}')



# Classes

class TknAcsHandler(Debugging):
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
            hotp = rcptAddress.extensions[0]
            logger.debug(f"HOTP: {str(hotp)}")
        except Exception as e:
            logger.debug(repr(e))
            return '550 not relaying to that domain'
        envelope.rcpt_tos.append(address)
        return '250 OK'

    async def handle_DATA(
        self,
        server,
        session,
        envelope):
        print('Message from %s' % envelope.mail_from)
        print('Message options %s' % str(envelope.mail_options))
        print('Message for %s' % envelope.rcpt_tos)
        print('Message data:\n')
        for ln in envelope.content.decode('utf8', errors='replace').splitlines():
            print(f'> {ln}'.strip())
        print()
        print('End of message')

        # Checks database user
        return '250 Message accepted for delivery'



# Functions

def launchSmtpServer(
    host:str,
    port:str,
    ssl_certfile=None,
    ssl_keyfile=None,
    ssl_mode=None,
    **kwargs):
    port = int(port)

    ctrlKwargs = {
        'handler':  TknAcsHandler(),
        'hostname': host,
        'port':     port,
    }

    ActiveController = Controller
    if ssl_mode in ['SSL', 'STARTTLS']:
        assert exists(ssl_certfile) and exists(ssl_keyfile), 'No SSL keys find'
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

