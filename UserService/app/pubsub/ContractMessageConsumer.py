import logging
from typing import Callable, Dict, Any
from app.services.UserService import UserService
from app.pubsub.EmailMessageSupplier import EmailMessageSupplier
from app.repositories.UserRepository import UserRepository
from app.clients.EntityClient import EntityClient
from app.models.valueobjects.ContractLite import ContractLite

class EmailContractedServiceProviderCreation:
    """
    Helper class for contracted service provider creation emails
    """
    def __init__(
        self, 
        userService: UserService, 
        emailMessageSupplier: EmailMessageSupplier,
        entityClient: EntityClient,
        userRepository: UserRepository
    ):
        self.userService = userService
        self.emailMessageSupplier = emailMessageSupplier
        self.entityClient = entityClient
        self.userRepository = userRepository
    
    async def sendEmail(self, contract: ContractLite):
        """
        Send contracted service provider creation email
        """
        logging.info(f"Sending contracted service provider creation email for {contract.contractName.contractName}")
        # Implementation would go here
    
    async def sendNotAggregatedMultiContractEmail(self, contract: ContractLite):
        """
        Send not aggregated multi-contract email
        """
        logging.info(f"Sending not aggregated multi-contract email for {contract.contractName.contractName}")
        # Implementation would go here
    
    async def sendContractRenewalRemainderEmails(self, renewalRemainderTemplate: Dict[str, Any]):
        """
        Send contract renewal reminder emails
        """
        logging.info("Sending contract renewal reminder emails")
        # Implementation would go here

class ContractMessageConsumer:
    """
    Python equivalent of Java ContractMessageConsumer
    Handles contract-related message consumption
    """
    
    def __init__(
        self,
        userService: UserService,
        emailMessageSupplier: EmailMessageSupplier,
        userRepository: UserRepository,
        entityClient: EntityClient,
        protocol: str,
        appBaseURL: str,
        appContext: str
    ):
        self.userService = userService
        self.emailMessageSupplier = emailMessageSupplier
        self.userRepository = userRepository
        self.entityClient = entityClient
        self.protocol = protocol
        self.appBaseURL = appBaseURL
        self.appContext = appContext
        self.LOG = logging.getLogger(__name__)
    
    def contractConsumer(self) -> Callable[[ContractLite], None]:
        """
        Equivalent to Java @Bean contractConsumer() method
        """
        async def consume_contract(contract: ContractLite) -> None:
            try:
                self.LOG.info(f"Consuming message event created at {contract.contractName.contractName}")
                
                if contract:
                    emailContractedServiceProviderCreation = EmailContractedServiceProviderCreation(
                        userService=self.userService,
                        emailMessageSupplier=self.emailMessageSupplier,
                        entityClient=self.entityClient,
                        userRepository=self.userRepository
                    )
                    await emailContractedServiceProviderCreation.sendEmail(contract)
                    
            except Exception as exception:
                self.LOG.error(f"Error processing contract message: {exception}")
                # Would send error to message queue in real implementation
        
        return consume_contract
    
    def multiContractConsumer(self) -> Callable[[ContractLite], None]:
        """
        Equivalent to Java @Bean multiContractConsumer() method
        """
        async def consume_multi_contract(contract: ContractLite) -> None:
            try:
                self.LOG.info(f"Consuming message event created at {contract.contractName.contractName}")
                
                if contract:
                    emailContractedServiceProviderCreation = EmailContractedServiceProviderCreation(
                        userService=self.userService,
                        emailMessageSupplier=self.emailMessageSupplier,
                        entityClient=self.entityClient,
                        userRepository=self.userRepository
                    )
                    await emailContractedServiceProviderCreation.sendNotAggregatedMultiContractEmail(contract)
                    
            except Exception as exception:
                self.LOG.error(f"Error processing multi-contract message: {exception}")
        
        return consume_multi_contract
    
    def renewedContractConsumer(self) -> Callable[[Dict[str, Any]], None]:
        """
        Equivalent to Java @Bean renewedContractConsumer() method
        """
        async def consume_renewed_contract(contract: Dict[str, Any]) -> None:
            try:
                newContractId = contract.get("newContractId")
                oldContractId = contract.get("oldContractId")
                await self.userService.updateRenewedContractInUser(oldContractId, newContractId)
                
            except Exception as exception:
                self.LOG.error(f"Error processing renewed contract message: {exception}")
        
        return consume_renewed_contract
    
    def updateOrDeleteUserByContract(self) -> Callable[[ContractLite], None]:
        """
        Equivalent to Java @Bean updateOrDeleteUserByContract() method
        """
        async def update_or_delete_user(contract: ContractLite) -> None:
            try:
                await self.userService.checkAndRemoveContractUser(contract.id)
                
            except Exception as exception:
                self.LOG.error(f"Error updating/deleting user by contract: {exception}")
        
        return update_or_delete_user
    
    def remainderContractConsumer(self) -> Callable[[Dict[str, Any]], None]:
        """
        Equivalent to Java @Bean remainderContractConsumer() method
        """
        async def consume_remainder_contract(renewalRemainderTemplate: Dict[str, Any]) -> None:
            try:
                emailContractedServiceProviderCreation = EmailContractedServiceProviderCreation(
                    userService=self.userService,
                    emailMessageSupplier=self.emailMessageSupplier,
                    entityClient=self.entityClient,
                    userRepository=self.userRepository
                )
                await emailContractedServiceProviderCreation.sendContractRenewalRemainderEmails(renewalRemainderTemplate)
                
            except Exception as exception:
                self.LOG.error(f"Error processing contract renewal reminder: {exception}")
        
        return consume_remainder_contract
    
    # Public methods to process messages
    async def process_contract_message(self, contract: ContractLite):
        consumer = self.contractConsumer()
        await consumer(contract)
    
    async def process_multi_contract_message(self, contract: ContractLite):
        consumer = self.multiContractConsumer()
        await consumer(contract)
    
    async def process_renewed_contract_message(self, contract: Dict[str, Any]):
        consumer = self.renewedContractConsumer()
        await consumer(contract)
    
    async def process_update_delete_user_message(self, contract: ContractLite):
        consumer = self.updateOrDeleteUserByContract()
        await consumer(contract)
    
    async def process_remainder_contract_message(self, renewalRemainderTemplate: Dict[str, Any]):
        consumer = self.remainderContractConsumer()
        await consumer(renewalRemainderTemplate)
