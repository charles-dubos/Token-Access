"""Unicorn server launcher:
   ------------------------
This python script launches the web API configured in the conf file. 
"""

import uvicorn


# PROJECT PERIMETER
## Creation of environment var for project
from os import environ
from os.path import dirname, abspath
environ['TKNACS_PATH'] = dirname(abspath(__file__))


from lib.LibTAServer import *
context.loadFromConfig(CONFIG_FILE)


import logging.config
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers':False,
    'formatters':{
        'default_formatter':{
            'format':'%(levelname)s:%(asctime)s\t%(message)s',
        },
    },
    'handlers':{
        "file_handler":{
            'class':'logging.FileHandler',
            'filename':context.GLOBAL['logging'],
            'encoding':'utf-8',
            'formatter':'default_formatter',
        },
    },
    'loggers':{
        'tknAcsAPI':{
            'handlers':['file_handler'],
            'level':context.GLOBAL['log_level'],
            'propagate':True
        }
    }
})
logger = logging.getLogger('tknAcsAPI')

if __name__=="__main__":
    logger.debug('Launching API server')
    uvicorn.run(
        "lib.LibTAWebAPI:app",
        host=context.WEB_API['host'],
        port=int(context.WEB_API['port']),
        reload=False,
        ssl_keyfile=context.WEB_API["ssl_keyfile"],
        ssl_certfile=context.WEB_API["ssl_certfile"],
    )
