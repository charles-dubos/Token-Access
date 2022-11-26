"""Database management:
   --------------------
Mysql and sqlite3 database management module, containing:
- mysqlDB and sqliteDB classes implementing the folowing methods:
  > addUser: adds a user to the database
  > isInDatabase: verifies if a user is present in database
  > changePassword: changes the password of the specified user
  > getPassword: get the password for specified user
  > updatePsk: set psk and counter for user
  > getHotpData: get psk and counter for user
  > getAllTokensUser: get all tokens requested for a user
  > getSenderTokensUser: get the tokens requested by a sender to a user
  > setSenderTokenUser: create a token and increment counter
  > isTokenValid: test if a token has been attributed
  > deleteToken: remove a token from database
"""


import sqlite3, mysql.connector
import unittest
from os import environ
from abc import ABC, abstractmethod

from lib.utils import CONFIG, LOGGER, ParseXML


# CONFIGURATION

class _SQLDB(ABC):
    _sqlCmd = None
    _type = None

    def __init__(self, dbName:str, outterDb=None, defaultDomain:str=None):

        SQL_CMD_FILE = f'{environ.get("TKNACS_PATH")}/lib/{self._type.lower()}Cmd.xml'
        LOGGER.debug(f"{self._type}: Getting commands from file {SQL_CMD_FILE}")
        self._sqlCmd = ParseXML(SQL_CMD_FILE)

        self.dbName=dbName
        self.USER_DB_CONNECTOR=outterDb
        self.DOMAIN=defaultDomain

    
    def _execSql(self, command:str, values:tuple):
        LOGGER.debug(f"{self._type}: executing command {command} with values {values}")
        self.cursor.execute(command, values)


    def _getOneSql(self, command:str, values:tuple) -> tuple:
        LOGGER.info(f"{self._type}: Requesting one result in DB")
        self._execSql(command=command, values=values)
        return self.cursor.fetchone()

    
    def _getAllSql(self, command:str, values:tuple) -> tuple:
        LOGGER.info(f"{self._type}: Requesting all results in DB")
        self._execSql(command=command, values=values)
        return self.cursor.fetchall()


    def _setSql(self, command:str, values:tuple):
        LOGGER.warning(f"{self._type}: Modifications request in DB")
        self._execSql(command=command, values=values)
        self.connector.commit()


    def _domain(self,domain) -> str:
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
        """Add a user to database on 2 tables:
        - In tokenData (table that manages psk and count)
        - In userData (table that manages users)

        Args:
            user (str): user name
            password (str): user password
            domain (str, optional): user domain. Defaults to None.
        """
        domain = self._domain(domain=domain)
        self._execSql(
            self._sqlCmd.extract("set/tokenData"),
            (user,domain)
        )
        self._setSql(
            self._sqlCmd.extract("set/userData"),
            (user, domain, password)
        )


    def isInDatabase(self, user:str, domain:str=None) -> bool:
        """Check if user is in database

        Args:
            user (str): user name
            domain (str, optional): user domain. Defaults to None.

        Returns:
            bool: Presence of user in tokendata table
        """
        domain = self._domain(domain=domain)
        return (self._getOneSql(
                self._sqlCmd.extract("get/tokenData_user"),
                (user,domain)
            ) is not None
        )


    def changePassword(self, user:str, password:str, domain:str=None):
        """Change the recorded password for a user

        Args:
            user (str): user name
            password (str): password (must be a hash, not plain!)
            domain (str, optional): user domain. Defaults to None.
        """
        domain = self._domain(domain=domain)
        self._setSql(
            self._sqlCmd.extract("reset/userData_password"),
            (password,user,domain)
        )


    def getPassword(self, user:str, domain:str=None) -> str:
        """Get the password set in userData database

        Args:
            user (str): user name
            domain (str, optional): user domain. Defaults to None.

        Returns:
            str: password (must be a hash, not plain!)
        """
        domain = self._domain(domain=domain)
        password = self._getOneSql(
            self._sqlCmd.extract("get/userData_password"),
            (user,domain)
        )
        return None if password is None else password[0] 


    def updatePsk(self, user:str, psk:str, count:int, domain:str=None):
        """Updates psk in tokenData table for HOTP

        Args:
            user (str): user name
            psk (str): pre-shared key
            count (int): counter for HOTP
            domain (str, optional): user domain. Defaults to None.
        """
        domain = self._domain(domain=domain)
        self._setSql(
            self._sqlCmd.extract("reset/tokenData_psk-count"),
            (psk,count,user, domain)
        )

    
    def getHotpData(self, user:str, domain:str=None) -> tuple:
        """requests pre-shared key and counter for a specified user

        Args:
            user (str): user name
            domain (str, optional): _description_. Defaults to None.

        Returns:
            str: _description_
        """
        domain = self._domain(domain=domain)
        return self._getOneSql(
            self._sqlCmd.extract("get/tokenData_psk-count"),
            (user, domain)
        )


    def getAllTokensUser(self, user:str, domain:str=None) -> tuple:
        """Return all tokens of a specified user.

        Args:
            user (str): user name
            domain (str, optional): domain user. Defaults to None.

        Returns:
            tuple: tuple of 2-uples (token, associated sender)
        """
        domain = self._domain(domain=domain)
        return self._getAllSql(
            self._sqlCmd.extract("get/msgToken_token-sender"),
            (user,domain)
        )
    

    def getSenderTokensUser(self, user:str, sender:str, domain:str=None) -> tuple:
        """Return all tokens for a user and a sender

        Args:
            user (str): user name
            sender (str): sender email address
            domain (str, optional): domain user. Defaults to None.

        Returns:
            tuple: tuple of 1-uple (token)
        """
        domain = self._domain(domain=domain)
        return self._getAllSql(
            self._sqlCmd.extract("get/msgToken_token"),
            (user,domain,sender)
        )
    

    def setSenderTokenUser(self, user:str, sender:str, token:str, counter:int, domain:str=None):
        """creates a token for a user and a sender and increment the counter.

        Args:
            user (str): user name
            sender (str): sender email address
            token (str): 6-digits token
            counter (int): counter for the token (before counter increment)
            domain (str, optional): user domain. Defaults to None.
        """
        domain = self._domain(domain=domain)
        self._setSql(
            self._sqlCmd.extract("set/msgToken"),
            (sender, user, domain, token)
        )
        self._setSql(
            self._sqlCmd.extract("reset/tokendata_count"),
            (counter + 1, user, domain)
        )


    def isTokenValid(self, user:str, sender:str, token:str, domain:str=None) -> bool:
        """checks if a given token has been attributed for a user by a sender

        Args:
            user (str): user name
            sender (str): sender email 
            token (str): requested 6-digits token
            domain (str, optional): domain name. Defaults to None.

        Returns:
            bool: validity of the token
        """
        domain = self._domain(domain=domain)
        return (self._getOneSql(
            self._sqlCmd.extract("get/msgToken_all"),
            (sender, user, domain, token)
            ) is not None
        )
    

    def deleteToken(self, user:str, token:str, domain:str=None) -> tuple:
        """Delete an obsolete token

        Args:
            user (str): user name
            token (str): corresponding token
            domain (str, optional): user domain. Defaults to None.

        Returns:
            tuple: _description_
        """
        domain = self._domain(domain=domain)
        return self._setSql(
            self._sqlCmd.extract("delete/msgToken"),
            (user,domain,token)
        )


    def __del__(self):
        self.connector.close()


class sqliteDB(_SQLDB):
    def __init__(self, dbName:str, outterDb=None, defaultDomain=None):
        """Creates a sqlite3 database connector & cursor.

        Args:
            dbName (str): sqlite3 DB pathname
            outterDb (_type_, optional): TODO: outter user database (i.e. Postfix virtual users). Defaults to None.
            defaultDomain (str, optional): Default domain name for users. Defaults to None.
        """
        self._type = "SQLite3"
        super().__init__(dbName=dbName, outterDb=outterDb, defaultDomain=defaultDomain)

        self.connector=sqlite3.connect(dbName)
        self.cursor=self.connector.cursor()
        self._createTables()


class mysqlDB(_SQLDB):
    def __init__(self, dbName, outterDb=None, defaultDomain=None):
        """Creates a mysql database connector & cursor.
        The database connection credentials must be in CONFIG file.

        Args:
            dbName (str): mysql database name
            outterDb (_type_, optional): TODO: outter user database (i.e. Postfix virtual users). Defaults to None.
            defaultDomain (str, optional): Default domain name for users. Defaults to None.
        """
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
