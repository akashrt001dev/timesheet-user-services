from pydantic import BaseModel
from typing import Dict, Optional, TYPE_CHECKING

from ..valueobjects.NotificationType import NotificationType

class NotificationDTO(BaseModel):
    notificationType: Optional['NotificationType']
    templateContext: Dict[str, str] = {}