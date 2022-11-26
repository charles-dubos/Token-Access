"""Test module for TokenAccess:
   ----------------------------
Impements unit tests for:
- lib.utils
- lib.cryptoFunc
- lib.dbManage
- [TODO]lib.policy
"""

import unittest
from os import environ, remove
from os.path import dirname, abspath, exists
from configparser import RawConfigParser


environ['TKNACS_PATH'] = dirname(abspath(__file__))
environ['TKNACS_CONF'] = environ["TKNACS_PATH"] + "/tokenAccess.conf"


# PROJECT PERIMETER
## Creation of testing environment
from lib.utils import CONFIG, LOGGER, EmailAddress, loggingReload
loggingReload(
    filename=CONFIG.get('WEB_API', 'logging')[:-4]+'_test.log',
    mode='w',
    logLevel="DEBUG"
)


# Tests for utils lib
#from lib.utils import LOGGER
#print(LOGGER.handlers, LOGGER)
LOGGER.critical("-= BEGINING TESTS =-")

class tests_1_utils(unittest.TestCase):

    def test_1_logger(self):
        """Verification of logging levels
        """
        LOGGER.debug("Test DEBUG level")
        LOGGER.info("Test INFO level")
        LOGGER.warning("Test WARNING level")
        LOGGER.error("Test ERROR level")
        LOGGER.critical("Test CRITICAL level")

    def test_2_confLoad(self):
        """Verification of configuration loading
        """
        mainPath=environ.get('TKNACS_PATH')
        self.assertTrue(exists(mainPath))
        confFile=environ.get('TKNACS_CONF')
        self.assertTrue(exists(confFile))
        self.assertIsNotNone(confFile)
        self.assertIn(CONFIG.get("DATABASE", "type"), ("sqlite3", "mysql"))

    def test_3_EmailParser(self):
        """Verification of the email parsing function
        """
        email1 = EmailAddress()
        email2 = EmailAddress()
        email1.parser("toto@test.com")
        email2.parser("testing it <toto+testDextension@test.com>")
        self.assertEqual(email1.user, email2.user)
        self.assertEqual(email1.domain, email2.domain)
        self.assertEqual(email2.name, "testing it ")
        self.assertListEqual(email2.extensions, ["testDextension"])

        self.assertRaises(SyntaxError, email2.parser, 'FalseAddressError')
        self.assertRaises(SyntaxError, email2.parser, 'bad constructed address <test@toto.com')
        self.assertRaises(SyntaxError, email2.parser, 'test@toto.com>')


# Tests for cryptoFunc lib
import lib.cryptoFunc as cryptoFunc

class tests_2_crypto(unittest.TestCase):

    def test_1_hash(self):
        """Verifications on the hash function
        """
        hash1 = cryptoFunc.HashText("plainText")
        hash2 = cryptoFunc.HashText("plainText2")

        self.assertEqual(type(hash1.getHash()), str)

        self.assertNotEqual(hash1.getHash(), hash2.getHash())
        self.assertTrue(hash1.isSame(hash1.getHash()))
        self.assertFalse(hash1.isSame(hash2.getHash()))


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


# Tests for dbManage lib
import lib.dbManage as dbManage

class tests_3_database(unittest.TestCase):
    # Simple SQLite3 databbase
    dbName_sqlite3 = "TKNACS_test.db"

    # Simple SQL database
    dbName_mySQL = 'TKNACS_test'

    # Minimal SQLite3 database (no domain specified)
    dbNameNoDomain = "TKNACS_testNoDomain.db"

    def __init__(self, *args, **kwargs):
        super(tests_3_database, self).__init__(*args, **kwargs)
        if exists(self.dbName_sqlite3):
            remove(self.dbName_sqlite3)
        if exists(self.dbNameNoDomain):
            remove(self.dbNameNoDomain)

    def setUp(self):
        self.dbTest_sqlite3 = dbManage.sqliteDB(dbName=self.dbName_sqlite3, defaultDomain="domain1.loc")
        self.dbTestNoDomain = dbManage.sqliteDB(dbName=self.dbNameNoDomain)
        self.dbTest_mysql = dbManage.mysqlDB(dbName=self.dbName_mySQL, defaultDomain="domain1.loc")


    def test_1_connection(self):
        """Verifications of the database plugins (connector/cursor definitions)
        """
        self.assertIsNotNone(self.dbTest_sqlite3.connector)
        self.assertIsNotNone(self.dbTest_sqlite3.cursor)

        self.assertIsNotNone(self.dbTest_mysql.connector)
        self.assertIsNotNone(self.dbTest_mysql.cursor)

        self.assertIsNotNone(self.dbTestNoDomain.connector)
        self.assertIsNotNone(self.dbTestNoDomain.cursor)


    def test_2_emptyDataBase(self):
        """Verifications on empty database
        """
        self.assertFalse(self.dbTest_sqlite3.isInDatabase("user"))
        self.assertIsNone(self.dbTest_sqlite3.getPassword("user"))

        self.assertFalse(self.dbTest_mysql.isInDatabase("user"))
        self.assertIsNone(self.dbTest_mysql.getPassword("user"))


    def test_3_userData_sqlite3(self):
        """Verifications for user creation in sqlite3 database & password
        """
        self.dbTest_sqlite3.addUser(user="user", password="password")
        self.assertTrue(self.dbTest_sqlite3.isInDatabase("user"))
        self.assertFalse(self.dbTest_sqlite3.isInDatabase("user", "DOMAIN2"))
        self.assertEqual(self.dbTest_sqlite3.getPassword("user"), "password")

        self.dbTest_sqlite3.addUser(user="user", domain="DOMAIN2", password="password2")
        self.assertTrue(self.dbTest_sqlite3.isInDatabase("user", "DOMAIN2"))
        self.assertEqual(self.dbTest_sqlite3.getPassword("user", domain="DOMAIN2"), "password2")

        self.dbTest_sqlite3.changePassword(user="user", password='password2')
        self.assertEqual(self.dbTest_sqlite3.getPassword("user"), "password2")

    def test_3_userData_mysql(self):
        """Verifications for user creation in mysql database & password
        """
        self.dbTest_mysql.addUser(user="user", password="password")
        self.assertEqual(self.dbTest_mysql.getPassword("user"), "password")

        self.dbTest_mysql.addUser(user="user", domain="DOMAIN2", password="password2")
        self.assertEqual(self.dbTest_mysql.getPassword("user", domain="DOMAIN2"), "password2")

        self.dbTest_mysql.changePassword(user="user", password='password2')
        self.assertEqual(self.dbTest_mysql.getPassword("user"), "password2")

    def test_3_userData_noDomain(self):
        """Verifications for user creation in database with no domain specified
        """
        self.dbTestNoDomain.addUser(user="user", domain="DOMAIN1", password="password")
        self.assertRaises(TypeError, self.dbTestNoDomain.isInDatabase, "password")


    def test_4_HOTPAdding(self):
        """Tests the recording of HOTP data (PSK & counter)
        """
        self.dbTest_sqlite3.addUser(user="tokenUser", password="password")

        # Populate PSK
        self.assertIsNone(self.dbTest_sqlite3.getHotpData(user="tokenUser")[0])
        self.dbTest_sqlite3.updatePsk(user="tokenUser", psk="PreSharedKey", count=0)
        psk,count = self.dbTest_sqlite3.getHotpData(user="tokenUser")
        self.assertEqual(psk, "PreSharedKey")
        self.assertEqual(count, 0)

    
    def test_token(self):
        """Verification of token recording & requesting
        """
        self.dbTest_sqlite3.addUser(user="tokenUser2", password="password2")

        # Create new token
        self.dbTest_sqlite3.setSenderTokenUser(user="tokenUser2", sender="sender@domain2.loc", token="123456", counter=0)
        self.assertTrue(self.dbTest_sqlite3.isTokenValid(user="tokenUser2", sender="sender@domain2.loc", token="123456"))
        self.assertFalse(self.dbTest_sqlite3.isTokenValid(user="tokenUser2", sender="sender@domain2.loc", token="123455"))

        self.dbTest_sqlite3.setSenderTokenUser(user="tokenUser2", sender="sender@domain2.loc", token="654321", counter=0)
        self.assertEqual(len(self.dbTest_sqlite3.getAllTokensUser(user="tokenUser2")),2)
        self.assertEqual(len(self.dbTest_sqlite3.getSenderTokensUser(user="tokenUser2", sender="sender@domain2.loc")),2)

        # Token deletion
        self.dbTest_sqlite3.deleteToken(user="tokenUser2", token="123456")
        self.assertFalse(self.dbTest_sqlite3.isTokenValid(user="tokenUser2", sender="sender@domain2.loc", token="123456"))
        self.assertTrue(self.dbTest_sqlite3.isTokenValid(user="tokenUser2", sender="sender@domain2.loc", token="654321"))

    
    def __del__(self, *args, **kwargs):
        remove(self.dbName_sqlite3)
        remove(self.dbNameNoDomain)

        self.dbTest_mysql.cursor.execute(f"DROP DATABASE {self.dbName_mySQL}")
        self.dbTest_mysql.connector.commit()


if __name__ == "__main__":

    unittest.main(exit=False)
