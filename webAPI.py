from fastapi import FastAPI, HTTPException, Form
import os, logging

# PROJECT PERIMETER
## Creation of environment var for project
os.environ['TKNACS_PATH'] = os.path.dirname(os.path.abspath(__file__))
os.environ['TKNACS_CONF'] = 'tokenAccess.conf'

# CONFIGURATION
## Loading conf file
from lib.utils import EmailAddress, loadConfFile
CONF=loadConfFile('WEB_API')

## Logging configuration
os.environ['TKNACS_LOG'] = CONF.get('logging')
logging.basicConfig(
	filename=os.environ.get('TKNACS_LOG'),
	encoding='utf-8',
	format='%(levelname)s:%(asctime)s\t%(message)s', 
	level=logging.DEBUG
)


## WebAPI variables
DOMAINS = CONF.get('domains').split(',')
DATABASE = loadConfFile('DATABASE').get('SQLdatabase')


# Inner dependances
import lib.cryptoFunc as cryptoFunc
import lib.dbManage as dbManage


# LAUNCH API
logging.debug(f'Opening database: {DATABASE}')
database = dbManage.SQLiteDB(dbName=DATABASE,defaultDomain=DOMAINS[0])

if not database.isInDatabase('alice'):
	database.addUser('alice', 'K9gGyX8OAK8aH8Myj6djqSaXI8jbj6xPk69x2xhtbpA=')
if not database.isInDatabase('charlie'):
	database.addUser('charlie', 'ud2WDBdTRZp4EV08uEWlfZJLaHfoBbCL0BCGzN80Qzw=')

app = FastAPI()


# API functions


@app.get("/")
async def root():
    return {"message": "Welcome to HOTP email validator. See '/docs' for API documentation"}


@app.get("/requestToken/")
async def read_item(emit: str, rcpt: str):
	try:
		rcptAddr = EmailAddress().parser(rcpt)
		if not database.isInDatabase(user=rcptAddr.user, domain=rcptAddr.domain):
			raise PermissionError

		preSharedKey, count = database.getHotpData(
			user=rcptAddr.user, 
			domain=rcptAddr.domain
		)

		hotp = cryptoFunc.getHotp(
			preSharedKey=preSharedKey,
			count=count)
		
		## Adding the record to token database and count increment
		database.setSenderTokenUser(
			user=rcptAddr.user, 
			domain=rcptAddr.domain,
			sender=emit, 
			token=hotp
		)
		database.updatePsk(
			user=rcptAddr.user, 
			domain=rcptAddr.domain,
			psk=preSharedKey,
			count=(count + 1)
		)

		return {
			"token": hotp,
		"allowed_for": {"from": emit, "to": rcpt}}
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
