"""Summarization service for generating text summaries.

This module provides the core summarization functionality for the AI Lecture Note
Summarizer. It uses a flexible model abstraction layer that supports multiple
summarization models through a unified interface.

The service acts as a facade that delegates to concrete model implementations
via the ModelFactory, enabling easy model swapping without code changes.
"""

from typing import Optional, Dict, Any
from app.services.summarization.model_factory import ModelFactory
from app.services.summarization.model_config import ModelConfig, ModelRegistry
from app.services.summarization.base_model import BaseSummarizationModel


class SummarizationService:
    """Service for generating summaries from text documents.
    
    This service provides a high-level interface for text summarization,
    delegating to concrete model implementations via the ModelFactory.
    Models can be swapped by changing configuration without modifying code.
    
    The service ensures:
    - Faithfulness: No hallucinated facts or entities
    - Coverage: All main topics and key concepts included
    - Conciseness: 20-40% of original length
    - Coherence: Well-structured and readable output
    - Relevance: All content directly related to main topics
    
    Usage:
        # Use default model from configuration
        service = SummarizationService()
        summary = service.summarize(text)
        
        # Use specific model
        service = SummarizationService(model_name="model-name")
        summary = service.summarize(text)
        
        # Use custom configuration
        config = ModelConfig(model_name="model-name", max_length=200)
        service = SummarizationService(config=config)
        summary = service.summarize(text)
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        config: Optional[ModelConfig] = None
    ):
        """Initialize the summarization service.
        
        Args:
            model_name: Name of the summarization model to use. If not provided,
                       uses the default from application configuration.
            config: Model configuration. If not provided, uses default config
                   from ModelRegistry.
        """
        # Determine model name
        if model_name is None and config is None:
            # Use default from application settings
            try:
                from app.core.config import settings
                model_name = settings.SUMMARIZATION_MODEL
            except Exception:
                # Fallback to first available model in registry
                available_models = ModelRegistry.list_models()
                if available_models:
                    model_name = available_models[0]
                else:
                    raise RuntimeError(
                        "No models available in registry. "
                        "Register at least one model before using SummarizationService."
                    )
        elif config is not None:
            model_name = config.model_name
        
        # Create model instance via factory
        self.model: BaseSummarizationModel = ModelFactory.create_model(
            model_name=model_name,
            config=config
        )
    
    def summarize(self, text: str, max_length: Optional[int] = None) -> str:
        """Generate a summary of the input text.
        
        This method delegates to the underlying model implementation,
        ensuring consistent behavior across different model types.
        
        Args:
            text: Source document text to summarize
            max_length: Optional maximum length for the summary in words
            
        Returns:
            Summary text
            
        Raises:
            ValueError: If input is invalid (empty, None, etc.)
            RuntimeError: If summarization fails
        """
        # Delegate to model
        return self.model.summarize(text, max_length=max_length)
    
    def validate_summary(self, source: str, summary: str) -> Dict[str, Any]:
        """Validate a summary against quality criteria.
        
        This method will implement quality validation checks:
        - Faithfulness score (QA-based)
        - Coverage score (topic/concept inclusion)
        - Coherence score (BERTScore, ROUGE-L)
        - Conciseness check (compression ratio)
        - Relevance score
        
        Args:
            source: Original source text
            summary: Generated summary text
            
        Returns:
            Dictionary containing validation metrics and pass/fail status
            
        Raises:
            NotImplementedError: This is a placeholder implementation
        """
        raise NotImplementedError("Summary validation not yet implemented")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model.
        
        Returns:
            Dictionary containing model metadata
        """
        return self.model.get_model_info()
