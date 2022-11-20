from configparser import ConfigParser
from os.path import exists
from os import environ
from xml.dom.minidom import parse as domParser


DEFAULT_CONFIG="""
[WEB_API]
; Enter domains name managed by the HOTP service separated with ,
domains=
logging=%TKNACS_PATH/file.log

[DATABASE]
; You can choose to use sqlite3 or mysql for database: 
type=sqlite3
; - SQLite3 is not recommended (no security on database), but easy to use
; - mySQL is more powerfull. You need to install a database server
;   On Debian, the installation can be done with 'apt install mariadb-server'
;   Then you have to execute 'mysql_secure_installation'
; SQLdatabase is the database file (sqlite) or name (mysql)
SQLdatabase=./tokenAccess.db
; mysql-specific configurations
hostDB=localhost
userDB=admin
passDB=Password

[CRYPTO]
; ECDH must be supported by cryptography.hazmat.primitives.assymetric (x25519 or x448):
ECDH=x25519
; Hash function must be supported by cyptography.hazmat.primitives.hashes:
HashFunction=SHA256 
HashLength=6
; ExportEncoding must be supported by base64:
ExportEncoding=b64
"""

class EmailAddress:
    extensions=[]
    
    def __init__(self, user=None, domain=None):
        self.user=user
        self.domain=domain

    def parser(self,address: str):
        """Parses an email address into user+extensions@domain.

        Args:
            address (str): e-mail address (explicit or with <>delimiters)

        Raises:
            SyntaxError: Unexploitable string syntax

        Returns:
            EmailAdress: object containing
                user: str with user name 
                extensions: list of str extensions folowing a + sign
                domain: str with domain name 
        """
        if address.find('<') != -1:
            if address.find('>', address.find('<')) != -1:
                address = address[address.find('<')+1:
                    address.find('>', address.find('<'))]
            else:
                raise SyntaxError
        
        splitAddress = address.split('@')
        if len(splitAddress) != 2:
            raise SyntaxError
        splitUsername = splitAddress[0].split('+')
        
        self.user = splitUsername[0]
        self.extensions = splitUsername[1:]
        self.domain = splitAddress[1]
        return self


def loadConfFile(category:str):
    """Load configuration of a specified category
    If the file does not exist, it recreates it with _createConfFile

    Args:
        category (str): category name in conf file

    Returns:
        Dict: dictionnary of string configurations
    """
    CONFFILE = environ.get("TKNACS_CONF")
    if not exists(CONFFILE):
        with open(CONFFILE,"w") as file:
            file.write(DEFAULT_CONFIG)

    config=ConfigParser(comment_prefixes=";")
    config.read(CONFFILE)
    return config[category]


class parseXML:
    def __init__(self,xmlFile):
        self._dom=domParser(file=xmlFile).getElementsByTagName('command')[0]
    
    def extract(self,path:str):
        pathList = path.split(sep="/")
        dom = self._dom
        for domLevel in pathList:
            dom = dom.getElementsByTagName(domLevel)[0]
        return dom.firstChild.nodeValue
