#!/usr/bin/env python3
#- *- coding:utf-8 -*-
"""This script starts the Token Access SMTP server
"""
__author__='Charles Dubos'
__license__='GNUv3'
__credits__='Charles Dubos'
__version__="0.1.0"
__maintainer__='Charles Dubos'
__email__='charles.dubos@telecom-paris.fr'
__status__='Development'



# Built-in

#import ssl
from os import environ
from os.path import dirname, abspath
import logging.config



# Owned libs
from lib.LibTAServer import *
from lib.LibTASmtp import launchSmtpServer



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
        },
        'mail.log':{
            'handlers':['file_handler'],
            'level':context.GLOBAL['log_level'],
            'propagate':True
        }
    }
})
logger = logging.getLogger('tknAcsServers')
logger.debug(f'Logger loaded in {__name__}')

## Load database
database=context.loadDatabase()



# Launcher

if __name__=="__main__":

    logger.debug('Launching SMTP server...')
    launchSmtpServer(**context.SMTP_SERVER)
