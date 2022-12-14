#!/usr/bin/env python3
#- *- coding:utf-8 -*-
"""This module contains functionalities for Token Access policy

Its goal is to manage policy for email token management.
It is only an empty shell for the moment to illustrate the possibilities 
of the project.
"""
__author__='Charles Dubos'
__license__='GNUv3'
__credits__='Charles Dubos'
__version__="0.1.0"
__maintainer__='Charles Dubos'
__email__='charles.dubos@telecom-paris.fr'
__status__='Development'



# Functions

def policy(sender:str, recipent: str, *args, **kwargs):
    """Function that agglomerates all the possible rules for a mail token request.
    This includes:
    - innerPolicy: rules implemented to all user of the domain
    - userPolicy: rules set for the specified user
    - [TODO] organizational policy: policy organizational-specific

    Returns:
        boolean: Result of the agreement process
    """

    def _innerPolicy(*args, **kwargs):
        """Represents the agreement process for the SMTP server side, depending 
        mainly on the sender and its domain name.
        
        It includes (not exhaustibly):
        - The sender domain trust
        - The sender trust
        - ...

        Returns:
            boolean: Result of agreement process.
        """

        return True

    def _outerPolicy(*args, **kwargs):
        """Represents the agreement process configured by the user.
        It can be based on (not exhaustibly):
        - The presence of the sender in the user contact list
        - The level of trust of the user
        - The wishes of the user to get some kind of messages from this sender (ads)
        - ...

        Returns:
            boolean: Result of agreement process.
        """
        # if not userDatabase.isInDatabase():
        #     return False

        return True

    return  _innerPolicy(*args, **kwargs) and  _outerPolicy(*args, **kwargs)
