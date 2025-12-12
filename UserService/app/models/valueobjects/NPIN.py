from pydantic import BaseModel, Field
try:
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover
    ConfigDict = None  # type: ignore
from typing import Optional

class NPIN(BaseModel):
    # Accept inbound alias names without breaking internal storage names
    if ConfigDict:
        model_config = ConfigDict(populate_by_name=True)  # type: ignore
    else:
        class Config:
            allow_population_by_field_name = True

    # Inbound accepts 'npin' (alias), internal field remains 'nPIN'
    nPIN: Optional[str] = Field(None, alias="npin")
    # Inbound accepts 'missing' and 'notApplicable'; internal keeps 'is*' names
    isMissing: Optional[bool] = Field(None, alias="missing")
    isNotApplicable: Optional[bool] = Field(None, alias="notApplicable")
