#!/usr/bin/env python3
#- *- coding:utf-8 -*-
"""This module contains functionalities for Token Access database use

MysqlDB and Sqlite3DB classes implementing the folowing methods:
  > addUser: adds a user to the database
  > delUser: removes a user in the database
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
__author__='Charles Dubos'
__license__='GNUv3'
__credits__='Charles Dubos'
__version__="0.1.0"
__maintainer__='Charles Dubos'
__email__='charles.dubos@telecom-paris.fr'
__status__='Development'



# Built-in

from os import environ
from abc import ABC, abstractmethod
import sqlite3
from logging import getLogger
from xml.dom.minidom import parse as domParser



# Other libs

import mysql.connector



# Module directives

## Load logger
logger=getLogger('tknAcsServers')
logger.debug(f'Logger loaded in {__name__}')



# Classes

class ParseXML:
    def __init__(self,xmlFile:str):
        """Parses an XML file starting with a <command> data container.

        Args:
            xmlFile (str): xml filename to parse 
        """
        self._dom=domParser(file=xmlFile).getElementsByTagName('command')[0]
    
    def extract(self,path:str) -> str:
        """Get the element of the parsed XML file.

        Args:
            path (str): Path to the wanted content separed with '/' 

        Returns:
            str: content of the precised path.
        """
        pathList = path.split(sep="/")
        dom = self._dom
        for domLevel in pathList:
            dom = dom.getElementsByTagName(domLevel)[0]
        return dom.firstChild.nodeValue


## SQL database abstract class
class _SQLDB(ABC):
    _sqlCmd = None
    _type = None

    def __init__(self, **dbContext):
        self._type = dbContext['db_type']

        SQL_CMD_FILE = f'{environ.get("TKNACS_PATH")}/lib/{self._type.lower()}Cmd.xml'
        logger.debug(f"{self._type}: Getting commands from file {SQL_CMD_FILE}")
        self._sqlCmd = ParseXML(SQL_CMD_FILE)

        for key in dbContext:
            self.__setattr__(key, dbContext[key])

    
    def _execSql(self, command:str, values:tuple=()):
        logger.debug(f"{self._type}: executing command {command} with values {values}")
        self.cursor.execute(command, values)


    def _getOneSql(self, command:str, values:tuple) -> tuple:
        logger.info(f"{self._type}: Requesting one result in DB.")
        self._execSql(command=command, values=values)
        return self.cursor.fetchone()

    
    def _getAllSql(self, command:str, values:tuple=()) -> tuple:
        logger.info(f"{self._type}: Requesting all results in DB.")
        self._execSql(command=command, values=values)
        return self.cursor.fetchall()


    def _setSql(self, command:str, values:tuple):
        logger.warning(f"{self._type}: Modifications request in DB")
        self._execSql(command=command, values=values)
        self.connector.commit()


    def _createTables(self):
        logger.debug(f'{self._type}: Creating the tables if not existing.')
        self._execSql(self._sqlCmd.extract(("create/tokenData_table")), ())
        self._execSql(self._sqlCmd.extract("create/msgToken_table"), ())


    def addUser(self, userEmail:str):
        """Add a user to database in table tokenData (table that manages psk and
        count).

        Args:
            userEmail (str): user email address in minimal format
        """
        self._setSql(
            self._sqlCmd.extract("set/tokenData"),
            (userEmail,)
        )

    
    def delUser(self, userEmail:str):
        """Del a user in database in table tokenData (table that manages psk and
        count)

        Args:
            userEmail (str): user email address in minimal format
        """
        self._setSql(
            self._sqlCmd.extract("delete/tokenData"),
            (userEmail,)
        )

    
    def getUsers(self):
        """Lists all users
        Returns:
            List: Users in database
        """
        return [ user[0] for user in self._getAllSql(
            command=self._sqlCmd.extract("get/tokenData_user").splitlines()[1],
        ) ]


    def isInDatabase(self, userEmail:str) -> bool:
        """Check if user email is in database

        Args:
            userEmail (str): user email address in minimal format

        Returns:
            bool: Presence of userEmail in tokendata table
        """
        return (self._getOneSql(
                self._sqlCmd.extract("get/tokenData_user"),
                (userEmail,)
            ) is not None
        )


    def updatePsk(self, userEmail:str, psk:str, count:int):
        """Updates psk in tokenData table for HOTP

        Args:
            userEmail (str): user email address in minimal format
            psk (str): pre-shared key
            count (int): counter for HOTP
        """
        self._setSql(
            self._sqlCmd.extract("reset/tokenData_psk-count"),
            (psk,count,userEmail)
        )

    
    def getHotpData(self, userEmail:str) -> tuple:
        """requests pre-shared key and counter for a specified user

        Args:
            userEmail (str): user email address in minimal format

        Returns:
            tuple: psk,count
        """
        return self._getOneSql(
            self._sqlCmd.extract("get/tokenData_psk-count"),
            (userEmail,)
        )


    def getAllTokensUser(self, userEmail:str,) -> tuple:
        """Return all tokens of a specified user.

        Args:
            userEmail (str): user email address in minimal format

        Returns:
            tuple: tuple of 2-uples (token, associated sender)
        """
        return self._getAllSql(
            self._sqlCmd.extract("get/msgToken_token-sender"),
            (userEmail,)
        )
    

    def getSenderTokensUser(self, userEmail:str, sender:str) -> tuple:
        """Return all tokens for a user and a sender

        Args:
            userEmail (str): user email address in minimal format
            sender (str): sender email address

        Returns:
            tuple: tuple of 1-uple (token)
        """
        return self._getAllSql(
            self._sqlCmd.extract("get/msgToken_token"),
            (userEmail,sender)
        )
    

    def setSenderTokenUser(self, userEmail:str, sender:str, token:str, counter:int):
        """creates a token for a user and a sender and increment the counter.

        Args:
            userEmail (str): user email address in minimal format
            sender (str): sender email address
            token (str): 6-digits token
            counter (int): counter for the token (before counter increment)
        """
        self._setSql(
            self._sqlCmd.extract("set/msgToken"),
            (sender, userEmail, token)
        )
        self._setSql(
            self._sqlCmd.extract("reset/tokendata_count"),
            (counter + 1, userEmail)
        )


    def isTokenValid(self, userEmail:str, sender:str, token:str) -> bool:
        """checks if a given token has been attributed for a user by a sender

        Args:
            userEmail (str): user email address in minimal format
            sender (str): sender email 
            token (str): requested 6-digits token

        Returns:
            bool: validity of the token
        """
        return (self._getOneSql(
            self._sqlCmd.extract("get/msgToken_all"),
            (sender, userEmail, token)
            ) is not None
        )
    

    def deleteToken(self, userEmail:str, token:str):
        """Delete an obsolete token

        Args:
            userEmail (str): user email address in minimal format
            token (str): corresponding token
        """
        self._setSql(
            self._sqlCmd.extract("delete/msgToken"),
            (userEmail,token)
        )


    def __del__(self):
        try:
            self.connector.close()
        except:
            pass


## SQLITE3 database class connector & cursor
class Sqlite3DB(_SQLDB):
    def __init__(self, sqlite3_path:str, **dbContext):
        """Creates a sqlite3 database connector & cursor.

        Args:
            sqlite3_path (str): SQLite3 DB pathName
        """
        logger.debug(f'Loading DB from {sqlite3_path}')
        super().__init__(**dbContext)

        self.connector=sqlite3.connect(database=sqlite3_path)
        self.cursor=self.connector.cursor()
        self._createTables()


## MYSQL database class connector & cursor
class MysqlDB(_SQLDB):
    def __init__(self, mysql_db:str, mysql_host:str, mysql_user:str, mysql_pass:str, **dbContext):
        """Creates a MySQL database connector & cursor.

        Args:
            mysql_db (str): MySQL DB name
            mysql_host (str): MySQL DB host
            mysql_user (str): MySQL DB user
            mysql_pass (str): MySQL DB user's pass
        """
        logger.debug(f'Loading {mysql_db} DB from {mysql_host}')
        super().__init__(**dbContext)

        self.connector = mysql.connector.connect(
            host=mysql_host,
            user=mysql_user,
            password=mysql_pass,
        )

        self.cursor = self.connector.cursor()
        self.cursor.execute("CREATE DATABASE IF NOT EXISTS %s" % mysql_db)

        self.cursor.execute("USE %s" % mysql_db)
        self._createTables()
