"""
Contact Discovery Module

Services for discovering finance contacts and generating email addresses.
"""

from .discovery import ContactDiscoveryService
from .email import (
    EmailDiscoveryService,
    EmailPatternGenerator,
    EmailValidator,
    LocalEmailValidator,
)

__all__ = [
    "ContactDiscoveryService",
    "EmailDiscoveryService",
    "EmailPatternGenerator",
    "EmailValidator",
    "LocalEmailValidator",
]

