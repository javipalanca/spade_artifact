# -*- coding: utf-8 -*-

"""Top-level package for spade-artifact."""

__author__ = """Javi Palanca"""
__email__ = "jpalanca@gmail.com"
__version__ = "0.3.1"

from .artifact import Artifact
from .agent import ArtifactMixin
from .artifact_ext import (
    operation,
    OperableArtifact,
    ArtifactActuatorMixin,
    AgentDirectoryMixin,
    DirectoryArtifact,
)

__all__ = [
    'Artifact',
    'ArtifactMixin',
    'operation',
    'OperableArtifact',
    'ArtifactActuatorMixin',
    'AgentDirectoryMixin',
    'DirectoryArtifact',
]

