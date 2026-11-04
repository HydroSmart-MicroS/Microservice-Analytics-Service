from pathlib import Path
from app.shared.infrastructure.persistence.postgresql.migration_runner import migrate
migrate(Path(__file__).parent / 'migrations')
