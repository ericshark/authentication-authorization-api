import os
from dns import message
from dotenv import load_dotenv

load_dotenv()
auth_strat = os.getenv("AUTH_STRATEGY")


def get_auth_backend():
    if auth_strat == "JWT":
        pass
    if auth_strat == "SESSION":
        pass

    else:
        raise ValueError(message="Wrong auth strat token")
