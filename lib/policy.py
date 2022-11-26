"""Policy implementation:
   ----------------------
A module that implement the class for token policy management.

Returns:
    bool: policy allowing or not
"""

class Policy:
    """Class that agglomerates all the possible rules for a mail token request.
    This includes:
    - innerPolicy: rules implemented to all user of the domain
    - userPolicy: rules set for the specified user
    - [TODO] organizational policy: policy organizational-specific

    NB: This class should not be instantiated. It gives all its results when called.

    Returns:
        boolean: Result of the agreement process
    """
    _sender=None
    _recipent = None

    def __init__(self, sender:str, recipent: str, *args, **kwargs):
        """Global policy to set the server behavior in case of token request.
        *args and **kwargs represents the necessary arguments that could be added for the policy to be more efficient.

        Args:
            sender (str): sender email address
            recipent (str): recipient email address

        Returns:
            boolean: Result of the agreement process
        """
        self._sender=sender
        self._recipent=recipent
        return self._innerPolicy() and self._userPolicy()
    
    def _innerPolicy(self):
        """Represents the agreement process for the SMTP server side, depending mainly on the sender and its domain name.
        It includes (not exhaustibly):
        - The sender domain trust
        - The sender trust
        - ...

        Returns:
            boolean: Result of agreement process.
        """

        return True

    def _userPolicy(self):
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
