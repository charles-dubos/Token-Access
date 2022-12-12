"""Test module for TokenAccess:
   ----------------------------
Impements unit tests for:
- lib.LibTAServer
- lib.LibTACrypto
- lib.LibTADatabase
- [TODO]lib.LibTAPolicy
"""
__author__='Charles Dubos'
__license__='GNUv3'
__credits__='Charles Dubos'
__version__="0.1.0"
__maintainer__='Charles Dubos'
__email__='charles.dubos@telecom-paris.fr'
__status__='Development'


# Built-in
import unittest
from os import environ, remove
from os.path import dirname, abspath, exists, expandvars
import logging.config


# Owned libs
from lib.LibTAServer import *
import lib.LibTACrypto as cryptoFunc


# Module directives
## Creation of environment var for project & configuration loading
environ['TKNACS_PATH'] = dirname(abspath(__file__))
context.loadConfig(CONFIG_FILE)
context.DATABASE['sqlite3_path']='/tmp/tknAcsTest.db'
context.DATABASE['mysql_db']='tknAcsTest'
context.GLOBAL['logging']='TknAcsTest.log'
context.GLOBAL['log_level']='DEBUG'
USERTEST="toto@example.com"
SENDERTEST="sender@other.com"

## Creating specially-configured logger
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
            'level':context.GLOBAL['log_level'],
            'propagate':True
        }
    }
})
logger = logging.getLogger('tknAcsServers')
logger.debug(f'Logger loaded in {__name__}')


# Tests classes

class tests_1_LibTAServer(unittest.TestCase):

    def test_1_logger(self):
        """Verification of logging levels
        """
        logger.debug("Test DEBUG level")
        logger.info("Test INFO level")
        logger.warning("Test WARNING level")
        logger.error("Test ERROR level")
        logger.critical("Test CRITICAL level")

    def test_2_confLoad(self):
        """Verification of configuration loading
        """
        self.assertTrue(
            exists(environ.get('TKNACS_PATH'))
        )
        self.assertTrue(exists(expandvars(CONFIG_FILE)))
        self.assertIsNotNone(context)
        self.assertIn(
            context.DATABASE['db_type'],
            ("sqlite3", "mysql")
        )

    def test_3_EmailParser(self):
        """Verification of the email parsing function
        """
        email1 = EmailAddress()
        email2 = EmailAddress()
        email1.parser("toto@test.com")
        email2.parser("testing it<toto+testDextension@test.com>")
        self.assertEqual(email1.user, email2.user)
        self.assertEqual(email1.domain, email2.domain)
        self.assertEqual(email2.displayedName, "testing it")
        self.assertListEqual(email2.extensions, ["testDextension"])
        self.assertEqual(email2.getEmailAddr(), "toto@test.com")
        self.assertEqual(email2.getFullAddr(enableExt=True), "testing it<toto+testDextension@test.com>")

        self.assertRaises(SyntaxError, email2.parser, 'FalseAddressError')
        self.assertRaises(SyntaxError, email2.parser, 'bad constructed address <test@toto.com')
        self.assertRaises(SyntaxError, email2.parser, 'test@toto.com>')


class tests_2_crypto(unittest.TestCase):

    def test_1_hash(self):
        """Verifications on the hash function
        """
        hash1 = cryptoFunc.HashText(
            plaintext="plaintext",
            **context.hash
        )
        hash2 = cryptoFunc.HashText(
            plaintext="plaintext2",
            **context.hash)

        self.assertEqual(type(hash1.getHash()), bytes)

        self.assertNotEqual(hash1.getHash(), hash2.getHash())
        self.assertTrue(hash1.isSame(hash1.getHash().decode()))
        self.assertFalse(hash1.isSame(hash2.getHash().decode()))


    def test_2_ECDH_exchange(self):
        """Checks the generation of a shared secret with ECDH
        """
        alicePSK = cryptoFunc.PreSharedKey()
        serverPSK = cryptoFunc.PreSharedKey()
        user="alice"
        serverPSK.generate(
            user=user,
            recipientPubKey=alicePSK.exportPubKey()
        )
        alicePSK.generate(
            user=user,
            recipientPubKey=serverPSK.exportPubKey()
        )
        self.assertNotEqual(serverPSK.exportPubKey(), alicePSK.exportPubKey())
        self.assertEqual(serverPSK.PSK, alicePSK.PSK)


    def test_3_HOTP(self):
        """Verifies the HOTP generation
        """
        alicePSK = cryptoFunc.PreSharedKey()
        serverPSK = cryptoFunc.PreSharedKey()
        user="alice"
        serverPSK.generate(
            user=user,
            recipientPubKey=alicePSK.exportPubKey()
        )

        firstHotps = [ cryptoFunc.getHotp(serverPSK.PSK,count) for count in range(10)]
        for count in range(9):
            self.assertTrue(len(firstHotps[count])==6)
            self.assertNotIn(firstHotps[count], firstHotps[count+1:])


class tests_3_database(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(tests_3_database, self).__init__(*args, **kwargs)
        if exists(context.DATABASE['sqlite3_path']):
            remove(context.DATABASE['sqlite3_path'])


    def setUp(self):
        context.DATABASE['db_type']='sqlite3'
        self.dbTest_sqlite3 = dbManage.Sqlite3DB(**context.DATABASE,)

        context.DATABASE['db_type']='mysql'
        self.dbTest_mysql = dbManage.MysqlDB(**context.DATABASE,)


    def test_1_connection(self):
        """Verifications of the database plugins (connector/cursor definitions)
        """
        self.assertIsNotNone(self.dbTest_sqlite3.connector)
        self.assertIsNotNone(self.dbTest_sqlite3.cursor)

        self.assertIsNotNone(self.dbTest_mysql.connector)
        self.assertIsNotNone(self.dbTest_mysql.cursor)


    def test_2_emptyDataBase(self):
        """Verifications on empty database
        """
        self.assertFalse(self.dbTest_sqlite3.isInDatabase(USERTEST))
        self.assertFalse(self.dbTest_mysql.isInDatabase(USERTEST))


    def test_3_userData_sqlite3(self):
        """Verifications for user creation in sqlite3 database & password
        """
        self.dbTest_sqlite3.addUser(USERTEST)
        self.assertTrue(self.dbTest_sqlite3.isInDatabase(USERTEST))

        self.dbTest_sqlite3.delUser(USERTEST)
        self.assertFalse(self.dbTest_sqlite3.isInDatabase(USERTEST))


    def test_3_userData_mysql(self):
        """Verifications for user creation in mysql database & password
        """
        self.dbTest_mysql.addUser(USERTEST)
        self.assertTrue(self.dbTest_mysql.isInDatabase(USERTEST))
        self.dbTest_mysql.delUser(USERTEST)
        self.assertFalse(self.dbTest_mysql.isInDatabase(USERTEST))


    def test_4_HOTPAdding(self):
        """Tests the recording of HOTP data (PSK & counter)
        """
        self.dbTest_sqlite3.addUser(USERTEST)

        # Populate PSK
        self.assertIsNone(self.dbTest_sqlite3.getHotpData(USERTEST)[0])
        self.dbTest_sqlite3.updatePsk(userEmail=USERTEST, psk="PreSharedKey", count=0)
        psk,count = self.dbTest_sqlite3.getHotpData(userEmail=USERTEST)
        self.assertEqual(psk, "PreSharedKey")
        self.assertEqual(count, 0)

    
    def test_token(self):
        """Verification of token recording & requesting
        """
        self.dbTest_sqlite3.addUser(USERTEST)

        # Create new token
        self.dbTest_sqlite3.setSenderTokenUser(
            userEmail=USERTEST,
            sender=SENDERTEST,
            token="123456",
            counter=0)
        self.assertTrue(self.dbTest_sqlite3.isTokenValid(
            userEmail=USERTEST,
            sender=SENDERTEST,
            token="123456"))
        self.assertFalse(self.dbTest_sqlite3.isTokenValid(
            userEmail=USERTEST,
            sender=SENDERTEST,
            token="123455"))

        self.dbTest_sqlite3.setSenderTokenUser(
            userEmail=USERTEST,
            sender=SENDERTEST,
            token="654321",
            counter=0)
        self.assertEqual(len(self.dbTest_sqlite3.getAllTokensUser(USERTEST)),2)
        self.assertEqual(len(self.dbTest_sqlite3.getSenderTokensUser(
            userEmail=USERTEST,
            sender=SENDERTEST)) ,2)

        # Token deletion
        self.dbTest_sqlite3.deleteToken(
            userEmail=USERTEST,
            token="123456")
        self.assertFalse(self.dbTest_sqlite3.isTokenValid(
            userEmail=USERTEST,
            sender=SENDERTEST,
            token="123456"))
        self.assertTrue(self.dbTest_sqlite3.isTokenValid(
            userEmail=USERTEST,
            sender=SENDERTEST,
            token="654321"))

    
    def __del__(self, *args, **kwargs):
        remove(context.DATABASE['sqlite3_path'])

        self.dbTest_mysql.cursor.execute(
            f"DROP DATABASE {context.DATABASE['mysql_db']}")
        self.dbTest_mysql.connector.commit()


if __name__ == "__main__":

    unittest.main(exit=False)
