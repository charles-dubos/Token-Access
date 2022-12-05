"""Web API for Token Access:
   -------------------------

This API simulates a management canal to :
- Request a HOTP token to send a message to a recipient managed by this system
- (Re-)generate a HOTP seed

Raises:
    FileNotFoundError: DB not acessible
    HTTPException: (406) Token request not allowed
    HTTPException: (418) Bad formatted email address
"""

from fastapi import FastAPI, HTTPException, Form


# Load logger
from logging import getLogger
logger=getLogger('tknAcsAPI')


# CONFIGURATION
from lib.LibTAServer import *


# Inner dependances

from lib.LibTACrypto import getHotp, PreSharedKey

import lib.LibTADatabase as dbManage
from lib.LibTAPolicy import policy


# Loading database
logger.debug('Opening {} database:'.format( context.DATABASE['db_type'] ))
if context.DATABASE['db_type'] in ["sqlite3", "mysql"]:
    database = getattr(
        dbManage,
        context.DATABASE['db_type'] + "DB"
    )(**context.DATABASE)
else:
    raise FileNotFoundError


# Running API
app = FastAPI()

def auth(func):
    print("TODO: AUTH decorator")
    return func


# API functions
@app.get("/")
async def root():
    return {"message": "Welcome to Token access: a HOTP email validator.\
        See '/docs' for API documentation"}


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
        if not database.isInDatabase(userEmail=recipientAddr.getEmailAddr()):
            raise PermissionError

        if not policy(sender, recipient):
            raise PermissionError

        preSharedKey, count = database.getHotpData(
            userEmail=recipientAddr.getEmailAddr(), 
        )

        hotp = getHotp(
            preSharedKey=preSharedKey,
            count=count,
            **{**context.hash, **context.hotp},
        )
        
        ## Adding the record to token database
        database.setSenderTokenUser(
            userEmail=recipientAddr.getEmailAddr(), 
            sender=sender, 
            count= count,
            token=hotp,
        )

        return {
            "token": hotp,
            "allowed_for": {
                "from": sender,
                "to": recipient,
                }
            }
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


@app.post("/{username}/generateHotpSeed")
@auth
async def generateHotpSeed(username:str, pubKey: str = Form()):
    """Regenerate seed (PSK) for Hotp generation from the user public key & returns the generated PSK seed, 
    the reinitialized counter and the server public key.
    ! The previous token generated with the elder seed become lapsed.

    Args:
        username (str): user email address.
        pubKey (str): user EC pubkey to generate ECDH PSK, given by POST form.

    Returns:
        json: formatted with {"user", "pubKey", "counter"}
    """
    
    # BEWARE: pending messages will be refused!!
    ## => Messages which have a generated token but not delivered to user mailbox
    serverPSK = PreSharedKey(
        **{**context.hash, **context.elliptic}
    )
    ## PSK generation and counter reinitiation
    serverPSK.generate(
        user=username,
        recipientPubKey=pubKey,
    )
    counter = 0

    ## Modifying the PSK in database
    database.updatePsk(
        userEmail=username,
        psk=serverPSK.PSK,
        count=counter,
    )

    return {"user": username,
        "pubKey": serverPSK.exportPubKey(),
        "counter": counter,
    }


@app.get("/{username}/getCount")
@auth
async def getCount(username:str):
    
    (_, counter) = database.getHotpData(
        userEmail=username,
    )

    return {"username": username,
        "counter": counter,
    }


@app.get("/{username}/getAllTokens")
@auth
async def getAllTokens(username:str):
    
    tokens = database.getAllTokensUser(
        userEmail=username,
    )

    return {"username": username,
        "tokens": dict((token, sender) for token, sender in tokens),
    }


