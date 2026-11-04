from dataclasses import asdict
from datetime import datetime,timezone
from ..resources.health_resource import HealthResource

def to_resource(ready: bool,components=None) -> dict:
    return asdict(HealthResource("UP" if ready else "DOWN",components=components or {'application':{'status':'UP'}},checkedAt=datetime.now(timezone.utc).isoformat()))

