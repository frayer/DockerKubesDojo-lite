"""Helpers for handling Cloud Native health probes"""

from dataclasses import dataclass

@dataclass
class HealthProbes:
    """
    Data class to hold variables altering the behavior of liveness and readiness
    probes
    """
    liveness_delay: int = 0
    readiness_pass: bool = True
