"""persona-forge — controlled persona generation with cross-session behavioural consistency validation."""

from .consistency import validate_consistency
from .core import generate_persona
from .models import BehaviouralTrait, ConsistencyReport, Persona, PersonaSeed, SessionSnapshot

__version__ = "0.1.0"
__all__ = [
    "generate_persona",
    "validate_consistency",
    "BehaviouralTrait",
    "ConsistencyReport",
    "Persona",
    "PersonaSeed",
    "SessionSnapshot",
]
