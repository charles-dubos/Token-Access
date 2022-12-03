"""SMTP relay for Token Access:
   ----------------------------

This file uses a SMTP relay server to manage the input messages and allow them only if they have a valid token. 

"""

import asyncio, ssl
import aiosmtpd
from aiosmtpd.controller import Controller


# PROJECT PERIMETER
## Creation of environment var for project
from os import environ
from os.path import dirname, abspath
environ['TKNACS_PATH'] = dirname(abspath(__file__))
environ['TKNACS_CONF'] = environ["TKNACS_PATH"] + "/tokenAccess.conf"


# CONFIGURATION
## Loading conf file
from lib.utils import CONFIG, LOGGER, EmailAddress
DOMAINS = CONFIG.get('GLOBAL','domains').split(',')
DBTYPE = CONFIG.get('DATABASE','type')
DATABASE = CONFIG.get('DATABASE','SQLdatabase')


import lib.dbManage as dbManage


class TknAcsHandler:
    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        try:
            extensions = (address.split("@", 1)[0]).split("+")
            hotp = int(extensions[1])
            print("HOTP:{%d}".format(hotp))
        except:
            return '550 not relaying to that domain'
        return '250 OK'

    async def handle_DATA(self, server, session, envelope):
        print('Message from %s' % envelope.mail_from)
        print('Message options %s' % str(envelope.mail_options))
        print('Message for %s' % envelope.rcpt_tos)
        print('Message data:\n')
        for ln in envelope.content.decode('utf8', errors='replace').splitlines():
            print(f'> {ln}'.strip())
        print()
        print('End of message')

        # Checks database user
        sender = EmailAddress(envelope.mail_from)
        recipient = EmailAddress(envelope.rcpt_tos)
        if not database.isInDatabase(
            user=recipient.user,
            domain=recipient.domain,
        ):
            return '550 not relaying to that domain'
        else:
            if database.isTokenValid(
                user=recipient.user,
                domain=recipient.domain,
                sender=sender.getEmailAddr(),
                token=recipient.extensions[0],
            ):
                return '250 Message accepted for delivery'
            else:
                return '450 Requested action not taken - The user\'s mailbox is unavailable (bad token).'
   
if __name__=="__main__":
    LOGGER.debug(f'Opening {DBTYPE} database: {DATABASE}')
    if DBTYPE == "sqlite3":
        database = dbManage.sqliteDB(dbName=DATABASE,defaultDomain=DOMAINS[0])
    elif DBTYPE == "mysql":
        database = dbManage.mysqlDB(dbName=DATABASE, defaultDomain=DOMAINS[0])
    else:
        raise FileNotFoundError

    host = CONFIG.get('SMTP_SERVER','host')
    port = int(CONFIG.get('SMTP_SERVER','port'))
    # context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    # context.load_cert_chain(
    #     keyfile=CONFIG.get("SMTP_SERVER", "ssl_keyfile"),
    #     certfile=CONFIG.get("SMTP_SERVER", "ssl_certfile"),
    # )
    # class StartTlsController(Controller):
    #     def factory(self):
    #         return SMTP(self.handler, require_starttls=True, tls_context=context)


    controller = Controller(
    # controller = StartTlsController(
        handler=TknAcsHandler(),
        hostname=host,
        # port=port,
    )

    try:
        controller.start()
        while input("EXIT to stop SMTP server: ").lower() != "exit":
            pass
    finally:
        controller.stop()
