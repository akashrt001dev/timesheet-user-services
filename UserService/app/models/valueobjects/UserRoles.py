from enum import Enum

class UserRoles(str, Enum):
    APPROVER = "Approver"
    REVIEWER = "Reviewer"
    FINANCE_REVIWER_APPROVER = "Finance Reviewer / Approver"

    def getConditionFields(self) -> str:
        return self.value
