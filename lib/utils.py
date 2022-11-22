from configparser import ConfigParser
from os.path import exists
from os import environ, popen
from xml.dom.minidom import parse as domParser
import logging

DEFAULT_CONFIG="""
[WEB_API]
; Enter domains name managed by the HOTP service separated with ,
domains=
logging=$TKNACS_PATH/file.log
log_level=WARNING

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
LOG_FORMAT = '%(levelname)s:%(asctime)s\t%(message)s'

class EmailAddress:
    extensions=[]
    
    def __init__(self, name:str=None, user:str=None, extensions:list=[], domain:str=None):
        """Parses e-mail adresses into user/extension/domain.

        Args:
            name (str, optional): Displayed name. Defaults to None.
            user (str, optional): email address user. Defaults to None.
            extensions (list, optional): email adress extensions. Defaults to empty list.
            domain (str, optional): email adress domain. Defaults to None.
        """
        self.name=name
        self.user=user
        self.extensions=extensions
        self.domain=domain
    
    def merger(self):
        """Returns string-formatted e-mail address.
        (NB: No check are done during merging)

        Raises:
            TypeError: user and domain must be defined 

        Returns:
            str: e-mail address
        """
        if user is None or domain is None:
            raise TypeError("user and domain cannot be 'None'")
        
        output = self.user
        for extension in extensions:
            output = output + "+" + extension
        output = self.domain

        if name is not None:
            output = name + "<" + output + ">"

        return output


    def parser(self,address: str):
        """Parses an email address given the folowing formats: 
        - user[+extension[s]]@domain.
        - name<user+extensions@domain>.

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
        
        if address.count('<') != 0 or address.count('>') != 0:
            if address.count('<') != 1 or address.count('>') != 1:
                raise SyntaxError
            if address.find('>', address.find('<')) == -1:
                raise SyntaxError
            self.name = address[:address.find('<')]
            address = address[address.find('<')+1:
                address.find('>', address.find('<'))]

        splitAddress = address.split('@')
        if len(splitAddress) != 2:
            raise SyntaxError
        splitUsername = splitAddress[0].split('+')
        
        self.user = splitUsername[0]
        self.extensions = splitUsername[1:]
        self.domain = splitAddress[1]
        return self


class Config:

    def __init__(self, filename:str):
        """Create a config file object

        Args:
            file (str): path of conf file
        """

        if not exists(filename):
            with open(filename,"w") as file:
                    file.write(DEFAULT_CONFIG)

        self._config=ConfigParser(comment_prefixes=";")
        self._config.read(filename)

    
    def get(self, category:str, item:str):
        return (self._config[category])[item]


class parseXML:
    def __init__(self,xmlFile:str):
        """Parses an XML file starting with a <command> data container.

        Args:
            xmlFile (str): xml filename to parse 
        """
        self._dom=domParser(file=xmlFile).getElementsByTagName('command')[0]
    
    def extract(self,path:str):
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


def loggingReload(filename:str, logLevel:str, mode = 'a'):
    """Redirects the LOGGER with a new filename and an new logLevel 

    Args:
        filename (str): output log filename
        logLevel (str): log level
        mode (str, optional): (a)ppend or (w)rite. Defaults to 'a'.
    """
    global LOGGER
    LOGLEVELS={
                "":         logging.NOTSET,
                "DEBUG":    logging.DEBUG,
                "INFO":     logging.INFO,
                "WARNING":     logging.WARNING,
                "ERROR":    logging.ERROR,
                "CRITICAL": logging.CRITICAL,
    }

    LOGGER.setLevel(LOGLEVELS[logLevel])
    newHandler = logging.FileHandler(filename=filename, encoding='utf-8', mode=mode)
    newHandler.setLevel(LOGLEVELS[logLevel])
    newHandler.setFormatter(
        logging.Formatter(LOG_FORMAT)
    )
    LOGGER.handlers[0]=newHandler


# Configuration loading
CONFIG = Config(environ.get("TKNACS_CONF"))

# Logging
with popen('printf "' + CONFIG.get(category='WEB_API', item='logging') + '"') as loggingPath:
    logging.basicConfig(
        filename=loggingPath.read(), 
        level=CONFIG.get(category='WEB_API', item='log_level'),
        encoding='utf-8',
        format=LOG_FORMAT
    )
    LOGGER = logging.getLogger()
