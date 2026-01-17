"""Summarization module for text summarization with model abstraction.

This module provides a flexible abstraction layer for text summarization,
supporting multiple models through a unified interface.
"""

from app.services.summarization.base_model import BaseSummarizationModel
from app.services.summarization.model_factory import ModelFactory
from app.services.summarization.model_config import ModelConfig, ModelRegistry

__all__ = [
    'BaseSummarizationModel',
    'ModelFactory',
    'ModelConfig',
    'ModelRegistry',
]
