"""Model factory for creating summarization model instances.

This module implements the Factory pattern to create summarization models
dynamically based on configuration, enabling easy model swapping without
code changes.
"""

from typing import Optional, Type, Dict
from app.services.summarization.base_model import BaseSummarizationModel
from app.services.summarization.model_config import ModelConfig, ModelRegistry


class ModelFactory:
    """Factory for creating summarization model instances.
    
    This class implements the Factory pattern to instantiate the correct
    model class based on the model name. It decouples model creation from
    model usage, allowing models to be swapped via configuration.
    
    Usage:
        # Create model with default config
        model = ModelFactory.create_model("flan-t5-base")
        
        # Create model with custom config
        config = ModelConfig(model_name="flan-t5-base", max_length=200)
        model = ModelFactory.create_model("flan-t5-base", config)
    """
    
    # Registry mapping model names to model classes
    _model_registry: Dict[str, Type[BaseSummarizationModel]] = {}
    
    @classmethod
    def register_model(cls, model_name: str, model_class: Type[BaseSummarizationModel]) -> None:
        """Register a model class with the factory.
        
        Args:
            model_name: Name to register the model under
            model_class: Model class to register (must extend BaseSummarizationModel)
            
        Raises:
            TypeError: If model_class doesn't extend BaseSummarizationModel
        """
        if not issubclass(model_class, BaseSummarizationModel):
            raise TypeError(
                f"Model class must extend BaseSummarizationModel, "
                f"got {model_class.__name__}"
            )
        
        cls._model_registry[model_name] = model_class
    
    @classmethod
    def create_model(
        cls,
        model_name: str,
        config: Optional[ModelConfig] = None
    ) -> BaseSummarizationModel:
        """Create a summarization model instance.
        
        Args:
            model_name: Name of the model to create
            config: Optional configuration for the model. If not provided,
                   default configuration from ModelRegistry will be used.
            
        Returns:
            Instance of the requested model
            
        Raises:
            ValueError: If model_name is not registered
        """
        # Normalize model name
        model_name = model_name.lower().strip()
        
        # Check if model is registered
        if model_name not in cls._model_registry:
            available = cls.list_available_models()
            raise ValueError(
                f"Unknown model '{model_name}'. "
                f"Available models: {available}. "
                f"Use ModelFactory.register_model() to register new models."
            )
        
        # Get or create configuration
        if config is None:
            try:
                config = ModelRegistry.get_default_config(model_name)
            except KeyError:
                # Model is registered in factory but not in registry
                # Create a basic config
                config = ModelConfig(model_name=model_name)
        
        # Get model class and instantiate
        model_class = cls._model_registry[model_name]
        
        try:
            model_instance = model_class(config=config)
        except Exception as e:
            raise RuntimeError(
                f"Failed to instantiate model '{model_name}': {e}"
            ) from e
        
        return model_instance
    
    @classmethod
    def list_available_models(cls) -> list[str]:
        """List all models registered with the factory.
        
        Returns:
            List of registered model names
        """
        return list(cls._model_registry.keys())
    
    @classmethod
    def is_model_available(cls, model_name: str) -> bool:
        """Check if a model is available.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if model is registered, False otherwise
        """
        return model_name.lower().strip() in cls._model_registry


# Auto-register models when they're imported
def _auto_register_models():
    """Automatically register available model implementations.
    
    This function attempts to import and register all available model
    implementations. If a model implementation is not available (e.g.,
    dependencies not installed), it will be skipped silently.
    """
    # Try to register Flan-T5 model
    try:
        from app.services.summarization.models.flan_t5_model import FlanT5Model
        ModelFactory.register_model("flan-t5-base", FlanT5Model)
        ModelFactory.register_model("flan-t5-large", FlanT5Model)
    except ImportError:
        # Flan-T5 model not available yet
        pass
    
    # Try to register BART model
    try:
        from app.services.summarization.models.bart_model import BARTModel
        ModelFactory.register_model("bart-large-cnn", BARTModel)
    except ImportError:
        # BART model not available yet
        pass
    
    # Try to register T5 model
    try:
        from app.services.summarization.models.t5_model import T5Model
        ModelFactory.register_model("t5-base", T5Model)
        ModelFactory.register_model("t5-small", T5Model)
    except ImportError:
        # T5 model not available yet
        pass


# Auto-register models on module import
_auto_register_models()
