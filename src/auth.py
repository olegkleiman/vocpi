from typing import List

# from py_ocpi.core.authentication.authenticator import Authenticator

class ClientAuthenticator: # (Authenticator):

    @classmethod
    async def get_valid_token_c(cls) -> List[str]:
        """Return a list of valid tokens c."""
        return ["my_valid_token_c"]

    @classmethod
    async def get_valid_token_a(cls) -> List[str]:
        """Return a list of valid tokens a."""
        return ["my_valid_token_a"]