from decimal import Decimal
from datetime import date
from pydantic import BaseModel, ConfigDict, Field

class TierResource(BaseModel):
    model_config = ConfigDict(extra='forbid')
    fromM3: Decimal
    toM3: Decimal | None
    waterPrice: Decimal
    sewerPrice: Decimal

class TariffResource(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(pattern='^(domestic|commercial)$')
    fixedCharge: Decimal = Field(default=Decimal(0), ge=0, le=99999.99, decimal_places=2)
    taxRate: Decimal = Field(default=Decimal(0), ge=0, le=1, decimal_places=4)
    tiers: list[TierResource] = Field(min_length=1,max_length=10)
    effectiveFrom: date | None = None
