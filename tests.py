import unittest

import lib.cryptoFunc as cryptoFunc

class cryptoTests(unittest.TestCase):

    def test_hash(self):
        hash1 = HashText("plainText")
        hash2 = HashText("plainText2")

        self.assertEqual(type(hash1.getHash()), str)

        self.assertNotEqual(hash1.getHash(), hash2.getHash())
        self.assertTrue(hash1.isSame(hash1.getHash()))
        self.assertFalse(hash1.isSame(hash2.getHash()))


    def test_psk(self):
        # ECDH exchange test
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


    def test_hotp(self):
        alicePSK = cryptoFunc.PreSharedKey()
        serverPSK = cryptoFunc.PreSharedKey()
        user="alice"
        serverPSK.generate(
            user=user,
            recipientPubKey=alicePSK.exportPubKey()
        )

        firstHotps = [ getHotp(serverPSK.PSK,count) for count in range(10)]
        for count in range(9):
            self.assertTrue(len(firstHotps[count])==6)
            self.assertNotIn(firstHotps[count], firstHotps[count:])




# class dbTests(unittest.TestCase):
#     dbName = "test.db"
#     dbTest = None
#     dbName_mySQL = 'test'

#     dbNameNoDomain = "testNoDomain.db"
#     dbTestNoDomain = None


#     def __init__(self, *args, **kwargs):
#         super(dbTests, self).__init__(*args, **kwargs)
#         if os.path.exists(self.dbName):
#             os.remove(self.dbName)
#         if os.path.exists(self.dbNameNoDomain):
#             os.remove(self.dbNameNoDomain)


#     def setUp(self):
#         self.dbTest_sqlite = sqliteDB(dbName=self.dbName, defaultDomain="DOMAIN1")
#         self.dbTestNoDomain = sqliteDB(dbName=self.dbNameNoDomain)
#         self.dbTest_mysql = mysqDB(dbName=self.dbName_mySQL)


#     def test_connected(self):
#         self.assertIsNotNone(self.dbTest_sqlite.connector)
#         self.assertIsNotNone(self.dbTest_sqlite.cursor)

#         self.assertIsNotNone(self.dbTest_mysql.connector)
#         self.assertIsNotNone(self.dbTest_mysql.cursor)

#         self.assertIsNotNone(self.dbTestNoDomain.connector)
#         self.assertIsNotNone(self.dbTestNoDomain.cursor)


#     def test_dataBase(self):
#         # Test for user creation
#         self.assertFalse(self.dbTest_sqlite.isInDatabase("user"))
#         self.assertIsNone(self.dbTest_sqlite.getPassword("user"))

#         self.assertFalse(self.dbTest_mysql.isInDatabase("user"))
#         self.assertIsNone(self.dbTest_mysql.getPassword("user"))


#     def test_userData(self):
#         self.dbTest_sqlite.addUser(user="user", password="password")
#         self.assertTrue(self.dbTest_sqlite.isInDatabase("user"))
#         self.assertFalse(self.dbTest_sqlite.isInDatabase("user", "DOMAIN2"))
#         self.assertEqual(self.dbTest_sqlite.getPassword("user"), "password")

#         self.dbTest_mysql.addUser(user="user", password="password")
#         self.assertEqual(self.dbTest_mysql.getPassword("user"), "password")

#         self.dbTest_sqlite.addUser(user="user", domain="DOMAIN2", password="password2")
#         self.assertTrue(self.dbTest_sqlite.isInDatabase("user", "DOMAIN2"))
#         self.assertEqual(self.dbTest_sqlite.getPassword("user", domain="DOMAIN2"), "password2")

#         self.dbTest_mysql.addUser(user="user", domain="DOMAIN2", password="password2")
#         self.assertEqual(self.dbTest_mysql.getPassword("user", domain="DOMAIN2"), "password2")

#         self.dbTestNoDomain.addUser(user="user", domain="DOMAIN1", password="password")
#         self.assertRaises(TypeError, self.dbTestNoDomain.isInDatabase, "password")

#         # testing Password
#         self.dbTest_sqlite.changePassword(user="user", password='password2')
#         self.assertEqual(self.dbTest_sqlite.getPassword("user"), "password2")

#         self.dbTest_mysql.changePassword(user="user", password='password2')
#         self.assertEqual(self.dbTest_mysql.getPassword("user"), "password2")


#     def test_hotp(self):
#         self.dbTest_sqlite.addUser(user="tokenUser", password="password")

#         # Populate PSK
#         self.assertIsNone(self.dbTest_sqlite.getHotpData(user="tokenUser")[0])
#         self.dbTest_sqlite.updatePsk(user="tokenUser", psk="PreSharedKey", count=0)
#         psk,count = self.dbTest_sqlite.getHotpData(user="tokenUser")
#         self.assertEqual(psk, "PreSharedKey")
#         self.assertEqual(count, 0)

    
#     def test_token(self):
#         self.dbTest_sqlite.addUser(user="tokenUser2", password="password2")

#         # Create new token
#         self.dbTest_sqlite.setSenderTokenUser(user="tokenUser2", sender="sender@domain2.loc", token="123456")
#         self.assertTrue(self.dbTest_sqlite.isTokenValid(user="tokenUser2", sender="sender@domain2.loc", token="123456"))
#         self.assertFalse(self.dbTest_sqlite.isTokenValid(user="tokenUser2", sender="sender@domain2.loc", token="123455"))

#         self.dbTest_sqlite.setSenderTokenUser(user="tokenUser2", sender="sender@domain2.loc", token="654321")
#         self.assertEqual(len(self.dbTest_sqlite.getAllTokensUser(user="tokenUser2")),2)
#         self.assertEqual(len(self.dbTest_sqlite.getSenderTokensUser(user="tokenUser2", sender="sender@domain2.loc")),2)

#         # Token deletion
#         self.dbTest_sqlite.deleteToken(user="tokenUser2", token="123456")
#         self.assertFalse(self.dbTest_sqlite.isTokenValid(user="tokenUser2", sender="sender@domain2.loc", token="123456"))
#         self.assertTrue(self.dbTest_sqlite.isTokenValid(user="tokenUser2", sender="sender@domain2.loc", token="654321"))

    
#     def __del__(self, *args, **kwargs):
#         os.remove(self.dbName)
#         os.remove(self.dbNameNoDomain)



if __name__ == "__main__":
    sqliteDB(dbName=CONF.get('SQLdatabase'), defaultDomain="DOMAIN1")    

    unittest.main()


if __name__ == "__main__":
    unittest.main()
