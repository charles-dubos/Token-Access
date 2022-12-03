"""Unicorn server launcher:
   ------------------------
This python script launches the web API as configured in the conf file. 
"""

import uvicorn


# PROJECT PERIMETER
## Creation of environment var for project
from os import environ
from os.path import dirname, abspath
environ['TKNACS_PATH'] = dirname(abspath(__file__))
environ['TKNACS_CONF'] = environ["TKNACS_PATH"] + "/tokenAccess.conf"



from lib.utils import CONFIG

if __name__=="__main__":
    try:
        uvicorn.run(
            "TknAcsWebAPI:app",
            host=CONFIG.get("WEB_API", "host"),
            port=int(CONFIG.get("WEB_API", "port")),
            reload=False,
            ssl_keyfile=CONFIG.get("WEB_API", "ssl_keyfile"),
            ssl_certfile=CONFIG.get("WEB_API", "ssl_certfile"),
        )
    except Exception as e:
        e.print()        
