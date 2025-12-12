from abc import ABC, abstractmethod
from typing import Any

class MessagePubSub(ABC):
    """
    Python equivalent of Java MessagePubSub interface
    Defines the contract for pub/sub message handling
    """
    
    @abstractmethod
    async def receive_user_contract_details(self, message: Any):
        """
        Equivalent to Java @Input("recevieUserContractDetails")
        Handles incoming user contract details messages
        """
        pass

class MessagePubSubImpl(MessagePubSub):
    """
    Implementation of MessagePubSub interface
    """
    
    def __init__(self):
        pass
    
    async def receive_user_contract_details(self, message: Any):
        """
        Implementation of user contract details message reception
        """
        # Handle the incoming message
        print(f"Received user contract details: {message}")
        # Process the message as needed
        pass
