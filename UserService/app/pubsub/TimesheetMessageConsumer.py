import logging
from typing import Callable, Dict, Any, List, Optional
from app.pubsub.EmailMessageSupplier import EmailMessageSupplier
from app.repositories.UserRepository import UserRepository
from app.clients.EntityClient import EntityClient
from app.services.UserService import UserService
from app.models.aggregates.root.User import User
from app.models.DTO.EntityDTO import EntityDTO
from app.core.constants import AppConstants
from app.core.EmailNotification import EmailNotification

class TimesheetMessageConsumer:
    """
    Python equivalent of Java TimesheetMessageConsumer
    Handles timesheet-related message consumption
    """
    
    def __init__(
        self,
        emailMessageSupplier: EmailMessageSupplier,
        userRepository: UserRepository,
        entityClient: EntityClient,
        userService: UserService
    ):
        self.emailMessageSupplier = emailMessageSupplier
        self.userRepository = userRepository
        self.entityClient = entityClient
        self.userService = userService
        self.logger = logging.getLogger(self.__class__.__name__)
        self.LOG = logging.getLogger(__name__)
    
    def activityConsumer(self) -> Callable[[Dict[str, Any]], None]:
        """
        Equivalent to Java @Bean activityConsumer() method
        """
        async def consume_activity(activityMap: Dict[str, Any]) -> None:
            try:
                userId = str(activityMap.get("toUser"))
                
                user = await self.userRepository.findById(userId)
                
                if user:
                    activityUser = user
                    
                    await self._addUserDetailsInTemplateMap(activityMap, activityUser)
                    
                    if "workFlowUserId" in activityMap:
                        workFlowUser = await self.userRepository.findById(str(activityMap.get("workFlowUserId")))
                        
                        if workFlowUser:
                            activityMap["workFlowUserFirstName"] = workFlowUser.name.firstName
                            activityMap["workFlowUserLastName"] = workFlowUser.name.lastName
                            activityMap["workFlowUserFullName"] = workFlowUser.name.getFullName()
                            
                            if workFlowUser.name.suffix and workFlowUser.name.suffix.suffix:
                                activityMap["workFlowUserSuffix"] = workFlowUser.name.suffix.suffix
                            
                            if workFlowUser.title and workFlowUser.title.title:
                                activityMap["workFlowUserTitle"] = workFlowUser.title.title
                    
                    emailNotification = EmailNotification()
                    
                    EMAIL_SUBJECT = str(activityMap.get("emailSubject"))
                    
                    toAddress = None
                    cc = None
                    
                    toUser = None
                    toCCUser = None
                    
                    if "toAddress" in activityMap:
                        toUser = await self.userRepository.findById(str(activityMap.get("toAddress")))
                    
                    if "ccAddress" in activityMap:
                        toCCUser = await self.userRepository.findById(str(activityMap.get("ccAddress")))
                    
                    toAddressType = str(activityMap.get("toAddressType"))
                    
                    if toAddressType == AppConstants.SINGLE:
                        if toUser:
                            toAddress = [toUser.email.officialEmail]
                        
                        if toCCUser:
                            cc = [toCCUser.email.officialEmail]
                    
                    elif toAddressType == AppConstants.MULTIPLE:
                        timesheetStatus = str(activityMap.get("timesheetStatus"))
                        
                        if timesheetStatus == AppConstants.PAYMENT:
                            invoiceApprovalBy = activityMap.get("invoiceApprovalBy")
                            workflowUserTitles = activityMap.get("workflowUserTitles")
                            
                            if invoiceApprovalBy == "TITLE" and workflowUserTitles is not None:
                                # Handle title-based approval with titles
                                pass
                            
                            if invoiceApprovalBy == "TITLE" and workflowUserTitles is None:
                                # Handle title-based approval without titles
                                pass
                            
                            if invoiceApprovalBy == "USER":
                                # Handle user-based approval
                                pass
                        
                        if timesheetStatus == AppConstants.PAYMENT_COMPLETED:
                            if toUser:
                                # Handle payment completed logic
                                pass
                            
                            ccUserIds = None
                            # Additional logic for ccUserIds
                    
                    else:
                        toAddress = [activityUser.email.officialEmail]
                    
                    if "notificationTo" in activityMap:
                        notificationTo = str(activityMap.get("notificationTo"))
                        toAddress = notificationTo.replace("[", "").replace("]", "").split(",")
                        activityMap["notificationTo"] = notificationTo.replace("[", "").replace("]", "")
                        cc = [activityUser.email.officialEmail]
                    
                    if "businessEntityEmail" in activityMap:
                        businessEntityEmail = str(activityMap.get("businessEntityEmail"))
                        if cc:
                            cc.append(businessEntityEmail)
                        else:
                            cc = [businessEntityEmail]
                    
                    templateName = str(activityMap.get("templateName"))
                    
                    await emailNotification.sendMail(
                        self.emailMessageSupplier,
                        AppConstants.PRODUCER_BINDING_NAME,
                        toAddress,
                        EMAIL_SUBJECT,
                        activityMap,
                        cc,
                        None,
                        templateName,
                        activityUser.tenant.tenantId
                    )
                    
            except Exception as exception:
                self.LOG.error(f"Error processing activity message: {exception}")
        
        return consume_activity
    
    async def _addUserDetailsInTemplateMap(self, templateMap: Dict[str, Any], user: User):
        """
        Equivalent to Java addUserDetailsInTemplateMap method
        """
        entity = await self.entityClient.getEntityById(user.tenant.tenantId)
        
        departments = []
        
        if user.sites and user.sites.sites:
            for site in user.sites.sites:
                if site.departmentList and site.departmentList.departments:
                    for department in site.departmentList.departments:
                        departments.append(department.departmentName.name)
        
        if entity.entityName and entity.entityName.entityName:
            templateMap["entityName"] = entity.entityName.entityName
        
        templateMap["departments"] = departments
        
        if entity.logo and entity.logo.file:
            templateMap["logo"] = entity.logo.file.fileURL
        else:
            templateMap["logo"] = ""
        
        if entity.subdomain:
            domainURL = await self.userService.domainUrlCreation(entity.subdomain)
            templateMap["domainURL"] = domainURL
        else:
            templateMap["domainURL"] = ""
        
        if entity.disclaimer and entity.disclaimer.paymentNote:
            templateMap["paymentDisclaimer"] = str(entity.disclaimer.paymentNote)
        
        templateMap["fullName"] = user.name.getFullName()
        templateMap["firstName"] = user.name.firstName
        templateMap["lastName"] = user.name.lastName
        templateMap["middleName"] = user.name.middleName
        templateMap["userName"] = user.ssoId.id
        
        if user.name.suffix and user.name.suffix.suffix:
            templateMap["suffix"] = user.name.suffix.suffix
        else:
            templateMap["suffix"] = ""
        
        if user.title and user.title.title:
            templateMap["title"] = user.title.title
    
    async def _getEmailsByUserIds(self, ccUserIds: List[str]) -> List[str]:
        """
        Equivalent to Java getEmaildsByUserIds method
        """
        userIds = [userId.strip() for userId in ccUserIds]
        emailIds = []
        
        for userId in userIds:
            user = await self.userRepository.findById(userId)
            if user:
                emailIds.append(user.email.officialEmail)
        
        return emailIds
    
    async def _getAllAccountsPayableByEntity(self, entityId: str) -> List[str]:
        """
        Equivalent to Java getAllAccountsPayableByEntity method
        """
        return await self.userService.getAllAccountsPayableByEntity(entityId)
    
    def scheduleReportConsumer(self) -> Callable[[Dict[str, Any]], None]:
        """
        Equivalent to Java @Bean scheduleReportConsumer() method
        """
        async def consume_schedule_report(scheduleReportMap: Dict[str, Any]) -> None:
            try:
                userId = str(scheduleReportMap.get("toUser"))
                
                user = await self.userRepository.findById(userId)
                
                if user:
                    scheduledUser = user
                    
                    await self._addUserDetailsInTemplateMap(scheduleReportMap, scheduledUser)
                    
                    templateName = str(scheduleReportMap.get("templateName"))
                    
                    emailNotification = EmailNotification()
                    
                    reportType = str(scheduleReportMap.get("reportType"))
                    EMAIL_SUBJECT = reportType.replace("_", " ") + " Scheduled Report"
                    
                    toAddress = [scheduledUser.email.officialEmail]
                    
                    ccUsers = str(scheduleReportMap.get("ccUsers")).replace("[", "").replace("]", "").split(",")
                    
                    cc = None
                    
                    if ccUsers and len(ccUsers) > 0:
                        ccEmailIds = await self._getEmailsByUserIds(ccUsers)
                        cc = ccEmailIds
                    
                    await emailNotification.sendMail(
                        self.emailMessageSupplier,
                        AppConstants.PRODUCER_BINDING_NAME,
                        toAddress,
                        EMAIL_SUBJECT,
                        scheduleReportMap,
                        cc,
                        None,
                        templateName,
                        scheduledUser.tenant.tenantId
                    )
                    
            except Exception as exception:
                self.LOG.error(f"Error processing schedule report message: {exception}")
        
        return consume_schedule_report
    
    # Public methods to process messages
    async def process_activity_message(self, activityMap: Dict[str, Any]):
        consumer = self.activityConsumer()
        await consumer(activityMap)
    
    async def process_schedule_report_message(self, scheduleReportMap: Dict[str, Any]):
        consumer = self.scheduleReportConsumer()
        await consumer(scheduleReportMap)
    
    async def start_consuming(self):
        """
        Start consuming timesheet messages from RabbitMQ
        """
        try:
            from ..core.RabbitMQConfig import rabbitmq_config
            
            await rabbitmq_config.connect()
            
            # Get the timesheet activity queue
            activity_queue = await rabbitmq_config.channel.get_queue("timesheet_activity_queue")
            
            # Get the timesheet schedule queue  
            schedule_queue = await rabbitmq_config.channel.get_queue("timesheet_schedule_queue")
            
            # Define message processors
            async def process_activity_msg(message):
                try:
                    async with message.process():
                        import json
                        data = json.loads(message.body.decode())
                        await self.process_activity_message(data)
                except Exception as e:
                    self.logger.error(f"Error processing activity message: {str(e)}")
            
            async def process_schedule_msg(message):
                try:
                    async with message.process():
                        import json
                        data = json.loads(message.body.decode())
                        await self.process_schedule_report_message(data)
                except Exception as e:
                    self.logger.error(f"Error processing schedule message: {str(e)}")
            
            # Start consuming from both queues
            await activity_queue.consume(process_activity_msg)
            await schedule_queue.consume(process_schedule_msg)
            
            self.logger.info("Started consuming timesheet messages from activity and schedule queues")
            
        except Exception as e:
            self.logger.error(f"Failed to start timesheet message consumer: {str(e)}")
            raise
