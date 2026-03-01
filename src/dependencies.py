
from .session_pubsub import OCPIPubSub

pubsub_manager = OCPIPubSub()

def get_pubsub() -> OCPIPubSub:
    return pubsub_manager


