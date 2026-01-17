"""Model configuration and registry for summarization models.

This module provides configuration management for summarization models,
including validation, default configurations, and a registry for
managing available models.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class ModelConfig(BaseModel):
    """Configuration for a summarization model.
    
    This class defines all parameters that can be configured for a
    summarization model, with validation to ensure parameters are valid.
    
    Attributes:
        model_name: Name of the model (e.g., 'flan-t5-base')
        model_version: Version of the model (optional)
        max_length: Maximum summary length in tokens
        min_length: Minimum summary length in tokens
        num_beams: Number of beams for generation (higher = better quality, slower)
        length_penalty: Length penalty for generation
        temperature: Sampling temperature (0.0 = deterministic)
        do_sample: Whether to use sampling instead of greedy decoding
        top_k: Top-k sampling parameter
        top_p: Top-p (nucleus) sampling parameter
    """
    
    model_config = ConfigDict(frozen=False)  # Allow updates via model_copy
    
    model_name: str = Field(..., description="Name of the summarization model")
    model_version: Optional[str] = Field(None, description="Version of the model")
    max_length: int = Field(150, ge=10, le=1024, description="Maximum summary length in tokens")
    min_length: int = Field(30, ge=1, le=512, description="Minimum summary length in tokens")
    num_beams: int = Field(4, ge=1, le=16, description="Number of beams for generation")
    length_penalty: float = Field(2.0, ge=0.0, le=10.0, description="Length penalty for generation")
    temperature: float = Field(1.0, ge=0.0, le=2.0, description="Sampling temperature")
    do_sample: bool = Field(False, description="Whether to use sampling")
    top_k: int = Field(50, ge=0, le=100, description="Top-k sampling parameter")
    top_p: float = Field(0.95, ge=0.0, le=1.0, description="Top-p (nucleus) sampling parameter")
    
    @field_validator('min_length')
    @classmethod
    def validate_min_length(cls, v: int, info) -> int:
        """Validate that min_length is less than max_length.
        
        Args:
            v: The min_length value
            info: Validation info containing other field values
            
        Returns:
            Validated min_length
            
        Raises:
            ValueError: If min_length >= max_length
        """
        # Note: max_length might not be set yet during validation
        # We'll do a comprehensive check in model_validator
        return v
    
    @model_validator(mode='after')
    def validate_length_relationship(self) -> 'ModelConfig':
        """Validate that min_length < max_length.
        
        Returns:
            Self after validation
            
        Raises:
            ValueError: If min_length >= max_length
        """
        if self.min_length >= self.max_length:
            raise ValueError(
                f"min_length ({self.min_length}) must be less than "
                f"max_length ({self.max_length})"
            )
        return self


class ModelRegistry:
    """Registry for managing available summarization models.
    
    This class maintains a registry of available models and their
    default configurations. It provides methods to:
    - Register new models
    - Retrieve default configurations
    - List available models
    """
    
    # Default configurations for supported models
    _default_configs: Dict[str, ModelConfig] = {
        "flan-t5-base": ModelConfig(
            model_name="flan-t5-base",
            model_version="google/flan-t5-base",
            max_length=150,
            min_length=30,
            num_beams=4,
            length_penalty=2.0,
            temperature=1.0,
            do_sample=False,
        ),
        "flan-t5-large": ModelConfig(
            model_name="flan-t5-large",
            model_version="google/flan-t5-large",
            max_length=200,
            min_length=40,
            num_beams=6,
            length_penalty=2.0,
            temperature=1.0,
            do_sample=False,
        ),
        "bart-large-cnn": ModelConfig(
            model_name="bart-large-cnn",
            model_version="facebook/bart-large-cnn",
            max_length=142,  # BART's default
            min_length=56,
            num_beams=4,
            length_penalty=2.0,
            temperature=1.0,
            do_sample=False,
        ),
        "t5-base": ModelConfig(
            model_name="t5-base",
            model_version="t5-base",
            max_length=150,
            min_length=30,
            num_beams=4,
            length_penalty=2.0,
            temperature=1.0,
            do_sample=False,
        ),
    }
    
    @classmethod
    def get_default_config(cls, model_name: str) -> ModelConfig:
        """Get the default configuration for a model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Default ModelConfig for the model
            
        Raises:
            KeyError: If model is not registered
        """
        if model_name not in cls._default_configs:
            raise KeyError(
                f"Model '{model_name}' not found in registry. "
                f"Available models: {list(cls._default_configs.keys())}"
            )
        
        # Return a copy to prevent modification of defaults
        return cls._default_configs[model_name].model_copy()
    
    @classmethod
    def register_model(cls, model_name: str, config: ModelConfig) -> None:
        """Register a new model with default configuration.
        
        Args:
            model_name: Name of the model
            config: Default configuration for the model
        """
        cls._default_configs[model_name] = config
    
    @classmethod
    def list_models(cls) -> list[str]:
        """List all registered models.
        
        Returns:
            List of registered model names
        """
        return list(cls._default_configs.keys())
    
    @classmethod
    def is_registered(cls, model_name: str) -> bool:
        """Check if a model is registered.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if model is registered, False otherwise
        """
        return model_name in cls._default_configs
