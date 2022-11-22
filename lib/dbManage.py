import sqlite3, mysql.connector
import unittest, os
from abc import ABC, abstractmethod

from lib.utils import CONFIG, LOGGER, parseXML

# CONFIGURATION


# Structure de DB:
## tokenData[User, PSK, count] => Contient les données de création de token par utilisateur
## userData[User, domain, Password] => Contient les données de base des utilisateurs
## msgToken[sender, recipient, token] => Contient les données propres aux tokens générés


class SQLDB(ABC):
    _sqlCmd = None
    _type = None

    def __init__(self, dbName, outterDb=None, defaultDomain=None):

        with os.popen('printf "$TKNACS_PATH"') as mainPath:
            SQL_CMD_FILE = f"{mainPath.read()}/lib/{self._type.lower()}Cmd.xml"
        LOGGER.debug(f"{self._type}: Getting commands from file {SQL_CMD_FILE}")
        self._sqlCmd = parseXML(SQL_CMD_FILE)

        self.dbName=dbName
        self.USER_DB_CONNECTOR=outterDb
        self.DOMAIN=defaultDomain

    
    def _execSql(self, command:str, values:tuple):
        LOGGER.debug(f"{self._type}: executing command {command} with values {values}")
        self.cursor.execute(command, values)


    def _getOneSql(self, command:str, values:tuple):
        LOGGER.info(f"{self._type}: Requesting one result in DB")
        self._execSql(command=command, values=values)
        return self.cursor.fetchone()

    
    def _getAllSql(self, command:str, values:tuple):
        LOGGER.info(f"{self._type}: Requesting all results in DB")
        self._execSql(command=command, values=values)
        return self.cursor.fetchall()


    def _setSql(self, command:str, values:tuple):
        LOGGER.warning(f"{self._type}: Modifications request in DB")
        self._execSql(command=command, values=values)
        self.connector.commit()


    def _domain(self,domain):
        if domain is not None:
            return domain
        elif self.DOMAIN is not None:
            return self.DOMAIN
        else:
            raise TypeError("'NoneType' domain")


    def _createTables(self):
        LOGGER.debug(f'{self._type}: Creating the tables if not existing.')
        self._execSql(self._sqlCmd.extract(("create/tokenData_table")), ())

        # Table à part car pas obligatoire => authent via Postfix/dovecot?
        if self.USER_DB_CONNECTOR is None:
            self._execSql(self._sqlCmd.extract("create/userData_table"), ())
        else:
            LOGGER.info(f'{self.USER_DB_CONNECTOR}: not using own user database.')

        self._execSql(self._sqlCmd.extract("create/msgToken_table"), ())


    def addUser(self, user: str, password:str, domain:str=None):
        domain = self._domain(domain=domain)
        self._execSql(
            self._sqlCmd.extract("set/tokenData"),
            (user,domain)
        )
        self._setSql(
            self._sqlCmd.extract("set/userData"),
            (user, domain, password)
        )


    def isInDatabase(self, user:str, domain:str=None):
        domain = self._domain(domain=domain)
        return (self._getOneSql(
                self._sqlCmd.extract("get/tokenData_user"),
                (user,domain)
            ) is not None
        )


    def changePassword(self, user:str, password:str, domain:str=None):
        domain = self._domain(domain=domain)
        self._setSql(
            self._sqlCmd.extract("reset/userData_password"),
            (password,user,domain)
        )


    def getPassword(self, user:str, domain:str=None):
        domain = self._domain(domain=domain)
        password = self._getOneSql(
            self._sqlCmd.extract("get/userData_password"),
            (user,domain)
        )
        return None if password is None else password[0] 


    def updatePsk(self, user:str, psk:str, count:int, domain:str=None):
        domain = self._domain(domain=domain)
        self._setSql(
            self._sqlCmd.extract("reset/tokenData_psk-count"),
            (psk,count,user, domain)
        )

    
    def getHotpData(self, user:str, domain:str=None):
        domain = self._domain(domain=domain)
        return self._getOneSql(
            self._sqlCmd.extract("get/tokenData_psk-count"),
            (user, domain)
        )


    def getAllTokensUser(self, user:str, domain:str=None):
        domain = self._domain(domain=domain)
        return self._getAllSql(
            self._sqlCmd.extract("get/msgToken_token-sender"),
            (user,domain)
        )
    

    def getSenderTokensUser(self, user:str, sender:str, domain:str=None):
        domain = self._domain(domain=domain)
        return self._getAllSql(
            self._sqlCmd.extract("get/msgToken_token"),
            (user,domain,sender)
        )
    

    def setSenderTokenUser(self, user:str, sender:str, token:str, domain:str=None):
        domain = self._domain(domain=domain)
        self._setSql(
            self._sqlCmd.extract("set/msgToken"),
            (sender, user, domain, token)
        )


    def isTokenValid(self, user:str, sender:str, token:str, domain:str=None):
        domain = self._domain(domain=domain)
        return (self._getOneSql(
            self._sqlCmd.extract("get/msgToken_all"),
            (sender, user, domain, token)
            ) is not None
        )
    

    def deleteToken(self, user:str, token:str, domain:str=None):
        domain = self._domain(domain=domain)
        return self._getAllSql(
            self._sqlCmd.extract("delete/msgToken"),
            (user,domain,token)
        )


    def __del__(self):
        self.connector.close()


class sqliteDB(SQLDB):
    def __init__(self, dbName, outterDb=None, defaultDomain=None):
        self._type = "SQLite3"
        super().__init__(dbName=dbName, outterDb=outterDb, defaultDomain=defaultDomain)

        self.connector=sqlite3.connect(dbName)
        self.cursor=self.connector.cursor()
        self._createTables()


class mysqlDB(SQLDB):
    def __init__(self, dbName, outterDb=None, defaultDomain=None):
        self._type = "mySQL"
        super().__init__(dbName=dbName, outterDb=outterDb, defaultDomain=defaultDomain)

        self.connector = mysql.connector.connect(
            host=CONFIG.get('DATABASE','hostDB'),
            user=CONFIG.get('DATABASE','userDB'),
            password=CONFIG.get('DATABASE','passDB')
        )

        self.cursor = self.connector.cursor()
        self.cursor.execute("CREATE DATABASE IF NOT EXISTS %s" % dbName)

        self.cursor.execute("USE %s" % dbName)
        self._createTables()
