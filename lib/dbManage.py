import sqlite3, mysql.connector
import unittest, os, logging
from abc import ABC, abstractmethod

from libs.utils import loadConfFile, parseXML

# CONFIGURATION
logging.basicConfig(
	filename=os.environ.get('TKNACS_LOG'),
	encoding='utf-8',
	format='%(levelname)s:%(asctime)s\t%(message)s', 
	level=logging.DEBUG
)

CONF=loadConfFile('DATABASE')
RDBMS=CONF.get('type')
logging.debug(f'Database type: {RDBMS}')


# Structure de la DB:
## tokenData[User, PSK, count] => Contient les données de création de token par utilisateur
## userData[User, domain, Password] => Contient les données de base des utilisateurs
## msgToken[sender, recipient, token] => Contient les données propres aux tokens générés

# Commandes SQL:
SQL_COMMANDS = f"%TKNACS_PATH/{RDBMS}Cmd.xml"
logging.debug(f"Getting commands from file {SQL_COMMANDS}")
sqlCommand=parseXML(SQL_COMMANDS)


class SQLDB(ABC):
    def __init__(self, dbName, outterDb=None, defaultDomain=None):
        self.dbName=dbName
        self.USER_DB_CONNECTOR=outterDb
        self.DOMAIN=defaultDomain

    
    def _execSql(self, command:str, values:tuple):
        self.cursor.execute(command, values)


    def _getOneSql(self, command:str, values:tuple):
        self._execSql(command=command, values=values)
        return self.cursor.fetchone()

    
    def _getAllSql(self, command:str, values:tuple):
        self._execSql(command=command, values=values)
        return self.cursor.fetchall()


    def _setSql(self, command:str, values:tuple):
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
        logging.debug('Creating the tables if not existing.')
        self._execSql(sqlCommand("create/tokenData_table"))

        # Table à part car pas obligatoire => authent via Postfix/dovecot?
        if self.USER_DB_CONNECTOR is None:
            self._execSql(sqlCommand("create/userData_table"), ())
        else:
            logging.info(f'{self.USER_DB_CONNECTOR}: not using own user database.')

        self._execSql(sqlCommand("create/msgToken_table"), ())


    def addUser(self, user: str, password:str, domain:str=None):
        domain = self._domain(domain=domain)
        self._execSql(
            sqlCommand("set/tokenData"),
            (user,domain)
        )
        self._setSql(
            sqlCommand("set/userData"),
            (user, domain, password)
        )


    def isInDatabase(self, user:str, domain:str=None):
        domain = self._domain(domain=domain)
        return (self._getOneSql(
                sqlCommand("get/tokenData_user"),
                (user,domain)
            ) is not None
        )


    def changePassword(self, user:str, password:str, domain:str=None):
        domain = self._domain(domain=domain)
        self._setSql(
            sqlCommand("reset/userData_password"),
            (password,user,domain)
        )


    def getPassword(self, user:str, domain:str=None):
        domain = self._domain(domain=domain)
        password = self._getOneSql(
            sqlCommand("get/userData_password"),
            (user,domain)
        )
        return None if password is None else password[0] 


    def updatePsk(self, user:str, psk:str, count:int, domain:str=None):
        domain = self._domain(domain=domain)
        self._setSql(
            sqlCommand("reset/tokenData_psk-count"),
            (psk,count,user, domain)
        )

    
    def getHotpData(self, user:str, domain:str=None):
        domain = self._domain(domain=domain)
        return self._getOneSql(
            sqlCommand("get/tokenData_psk-count"),
            (user, domain)
        )


    def getAllTokensUser(self, user:str, domain:str=None):
        domain = self._domain(domain=domain)
        return self._getAllSql(
            sqlCommand("get/msgToken_token-sender"),
            (user,domain)
        )
    

    def getSenderTokensUser(self, user:str, sender:str, domain:str=None):
        domain = self._domain(domain=domain)
        return self._getAllSql(
            sqlCommand("get/msgToken_token"),
            (user,domain,sender)
        )
    

    def setSenderTokenUser(self, user:str, sender:str, token:str, domain:str=None):
        domain = self._domain(domain=domain)
        self._setSql(
            sqlCommand("set/msgToken"),
            (sender, user, domain, token)
        )


    def isTokenValid(self, user:str, sender:str, token:str, domain:str=None):
        domain = self._domain(domain=domain)
        return (self._getOneSql(
            sqlCommand("get/msgToken_all"),
            (sender, user, domain, token)
            ) is not None
        )
    

    def deleteToken(self, user:str, token:str, domain:str=None):
        domain = self._domain(domain=domain)
        return self._getAllSql(
            sqlCommand("delete/msgToken"),
            (user,domain,token)
        )


    def __del__(self):
        self.connector.close()


class sqliteDB(SQLDB):
    def __init__(self, dbName, outterDb=None, defaultDomain=None):
        super().__init__(dbName=dbName, outterDb=outterDb, defaultDomain=defaultDomain)
        self.connector=sqlite3.connect(dbName)
        self.cursor=self.connector.cursor()
        self._createTables()


class mysqDB(SQLDB):
    def __init__(self, dbName, outterDb=None, defaultDomain=None):
        super().__init__(dbName=dbName, outterDb=outterDb, defaultDomain=defaultDomain)
        self.connector=mysql.connector.connect(
            host=CONF.get('hostDB'),
            user=CONF.get('userDB'),
            password=CONF.get('passDB')
        )

        self.cursor=self.connector.cursor()
        self.cursor.execute("CREATE DATABASE IF NOT EXISTS %s" % dbName)

        self.cursor.execute("USE %s" % dbName)
        self._createTables()


    def _execSql(self, command:str, values:tuple):
        super()._execSql(command.replace('?', '%s')
            .replace('AUTOINCREMENT','AUTO_INCREMENT'), values)
