from fastapi import FastAPI, HTTPException, Form
import os, logging

# PROJECT PERIMETER
## Creation of environment var for project
os.environ['TKNACS_PATH'] = os.path.dirname(os.path.abspath(__file__))
with os.popen('printf "$TKNACS_PATH/tokenAccess.conf"') as confPath:
    os.environ['TKNACS_CONF'] = confPath.read()


# CONFIGURATION
## Loading conf file

from lib.utils import CONFIG, LOGGER, EmailAddress


## WebAPI variables

DOMAINS = CONFIG.get('WEB_API','domains').split(',')
DBTYPE = CONFIG.get('DATABASE','type')
DATABASE = CONFIG.get('DATABASE','SQLdatabase')


# Inner dependances

import lib.cryptoFunc as cryptoFunc
import lib.dbManage as dbManage
from lib.policy import Policy

# LAUNCH API

LOGGER.debug(f'Opening {DBTYPE} database: {DATABASE}')
if DBTYPE == "sqlite3":
    database = dbManage.sqliteDB(dbName=DATABASE,defaultDomain=DOMAINS[0])
elif DBTYPE == "mysql":
    database = dbManage.mysqlDB(dbName=DATABASE, defaultDomain=DOMAINS[0])
else:
    raise FileNotFoundError


app = FastAPI()


# API functions

@app.get("/")
async def root():
    return {"message": "Welcome to HOTP email validator. See '/docs' for API documentation"}


@app.get("/requestToken/")
async def requestToken(sender: str, recipient: str):
    """Requests a HOTP token for external sender to recipient (user).

    Args:
        sender (str): email address of sender
        recipient (str): email adress of recipient

    Raises:
        ValueError (HTTP/418): Bad email address
        PermissionError (HTTP/406): Recorded inner policy not allowing this connection 

    Returns:
        json: formatted with {"token","allowed_for": {"from", "to"}}
    """
    try:
        recipientAddr = EmailAddress().parser(recipient)
        if not database.isInDatabase(user=recipientAddr.user, domain=recipientAddr.domain):
            raise PermissionError

        if not Policy(sender, recipient):
            raise PermissionError

        preSharedKey, count = database.getHotpData(
            user=recipientAddr.user, 
            domain=recipientAddr.domain
        )

        hotp = cryptoFunc.getHotp(
            preSharedKey=preSharedKey,
            count=count)
        
        ## Adding the record to token database and count increment
        database.setSenderTokenUser(
            user=recipientAddr.user, 
            domain=recipientAddr.domain,
            sender=sender, 
            token=hotp
        )
        database.updatePsk(
            user=recipientAddr.user, 
            domain=recipientAddr.domain,
            psk=preSharedKey,
            count=(count + 1)
        )

        return {
            "token": hotp,
        "allowed_for": {"from": sender, "to": recipient}}
    except ValueError:
        raise HTTPException(
            status_code=418,
            detail="Bad email address"
        )
    except PermissionError:
        raise HTTPException(
            status_code=406,
            detail="Policy not allowing this connection."
        ) 


@app.post("/regenerateHotpSeed")
async def regenerateHotpSeed(username: str = Form(), password: str = Form(), pubKey: str = Form()):
    """Regenerate seed (PSK) for Hotp generation from the user public key & returns the generated PSK seed, 
    the reinitialized counter and the server public key.
    ! The previous token generated with the elder seed become lapsed.

    Args:
        username (str): user auth & email address, given by POST form.
        password (str): user auth password, given by POST form.
        pubKey (str): user EC pubkey to generate ECDH PSK, given by POST form.

    Raises:
        HTTPException (HTTP/400): Bad user authentication

    Returns:
        json: formatted with {"user", "pubKey", "counter", "psk"}
    """
    userAddr = EmailAddress().parser(address=username)

    if not database.isInDatabase(user=userAddr.user, domain=userAddr.domain):
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password"
        )
    savedPassword = database.getPassword(user=userAddr.user, domain=userAddr.domain)
    if not cryptoFunc.HashText(plainText=password).isSame(hashStr=savedPassword):
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password"
        )
    
    
    # BEWARE: pending messages will be refused!!
    ## => Messages which have a generated token but not delivered to user mailbox
    serverPSK = cryptoFunc.PreSharedKey()
    ## PSK generation and counter reinitiation
    serverPSK.generate(
        user=username,
        recipientPubKey=pubKey,
    )
    counter = 0

    ## Modifying the PSK in database
    database.updatePsk(
        user=userAddr.user,
        domain=userAddr.domain,
        psk=serverPSK.PSK,
        count=counter
    )

    return {"user": username, "pubKey": serverPSK.exportPubKey(), "counter": counter, "psk": serverPSK.PSK}
