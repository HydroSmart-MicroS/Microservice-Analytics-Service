from dataclasses import dataclass,field

@dataclass(frozen=True)
class HealthResource:
    status: str
    service: str = "analytics"
    components: dict = field(default_factory=dict)
    checkedAt: str = ''
