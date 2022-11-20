from cryptography.hazmat.primitives.twofactor import hotp
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import twofactor, hashes, serialization
from importlib import import_module
import base64

from lib.utils import loadConfFile


# CONFIGURATION LOADING
CONF=loadConfFile('CRYPTO')

ECDH=CONF.get('ECDH').lower()
mod = import_module('cryptography.hazmat.primitives.asymmetric.'+ECDH)
ECPrivateKey=getattr(mod, ECDH.capitalize()+"PrivateKey")
ECPublicKey=getattr(mod, ECDH.capitalize()+"PublicKey")

hashFunc = getattr(hashes, CONF.get('HashFunction') )
HOTPLen = CONF.getint('HashLength')
BASE = CONF.get('ExportEncoding')

encoder = getattr(base64, BASE+'encode')
decoder = getattr(base64, BASE+'decode')


# PSK structure for ECDH
class PreSharedKey:
    PSK=None

    def __init__(self,baseEncode=encoder):
        self._pvtKey=ECPrivateKey.generate()
        self.baseEncode=baseEncode

    def exportPubKey(self):
        return self.baseEncode(
            self._pvtKey.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        ).decode('ascii')

    def generate(self, user:str, recipientPubKey: str, baseDecode=decoder):
        bytesPubKey = ECPublicKey.from_public_bytes(
                baseDecode(recipientPubKey.encode('ascii'))
            )
            
        sharedKey = self._pvtKey.exchange(bytesPubKey)
        derivedPSK = HKDF(
            algorithm=hashFunc(),
            length=20,
            salt=None,
            info=bytes(f'{user}', 'UTF-8'),
        ).derive(sharedKey)

        self.PSK = self.baseEncode(derivedPSK).decode('ascii')
        return self.PSK 
        

# Hash structure for hashing
class HashText:
    def __init__(self, plainText:str, baseEncode=encoder):
        self.plainText=plainText.encode('utf-8')
        self.baseEncode=baseEncode
    
    def getHash(self):
        digest = hashes.Hash( algorithm=hashFunc() )
        digest.update(self.plainText)
        hashBytes = digest.finalize()
        return self.baseEncode(hashBytes).decode('ascii')
    
    def isSame(self, hashStr:str):
        return (self.getHash() == hashStr)
    

# HOTP function
def getHotp(preSharedKey: str, count: int, baseDecode=decoder):
    """Compute HOTP with the given arguments

    Args:
        preSharedKey (str): encoded pre-shared key
        count (int): Counter

    Returns:
        str: Return the HOTP 6-digits value
    """
    bytesPSK = baseDecode(preSharedKey)
    myHOTP = hotp.HOTP(
        key=bytesPSK,
        length=6,
        algorithm=hashFunc()
    )
    return myHOTP.generate(counter=count)
