#!/usr/bin/env python3
#- *- coding:utf-8 -*-
"""This script starts a unicorn server for Token Access API.

It uses the defined configuration file.
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
from os.path import dirname, abspath
import logging.config


# Other libs
import uvicorn


# Owned libs
from lib.LibTAServer import *


# Module directives

## Creation of environment var for project & configuration loading
environ['TKNACS_PATH'] = dirname(abspath(__file__))
context.loadConfig(CONFIG_FILE)

## Creating specially-configured logger
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers':False,
    'formatters':{
        'default_formatter':{
            'format':'%(levelname)s:  %(asctime)s  [%(process)d][%(filename)s][%(funcName)s]  %(message)s',
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
        'tknAcsServers':{
            'handlers':['file_handler'],
            'level':context.GLOBAL['log_level'],
            'propagate':True
        }
    }
})
logger = logging.getLogger('tknAcsServers')
logger.debug(f'Logger loaded in {__name__}')


# Launcher

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
