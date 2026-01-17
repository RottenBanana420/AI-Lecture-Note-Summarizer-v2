"""Base model abstraction for summarization models.

This module defines the abstract base class that all summarization models
must implement, ensuring a consistent interface across different model types.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class BaseSummarizationModel(ABC):
    """Abstract base class for all summarization models.
    
    This class defines the interface that all concrete summarization models
    must implement. It ensures consistency across different model types and
    enables easy model swapping without changing client code.
    
    All concrete models must implement:
    - summarize(): Generate summary from text
    - validate_input(): Validate input text
    - get_model_info(): Return model metadata
    
    Properties that must be defined:
    - model_name: Name of the model
    - model_version: Version of the model
    - max_input_length: Maximum input length in tokens
    """
    
    def __init__(self, config: Optional['ModelConfig'] = None):
        """Initialize the base model.
        
        Args:
            config: Model configuration (optional)
        """
        self.config = config
        self._initialized_at = datetime.utcnow()
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name of the model.
        
        Returns:
            Model name (e.g., 'flan-t5-base', 'bart-large-cnn')
        """
        pass
    
    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return the version of the model.
        
        Returns:
            Model version string
        """
        pass
    
    @property
    @abstractmethod
    def max_input_length(self) -> int:
        """Return the maximum input length in tokens.
        
        Returns:
            Maximum number of tokens the model can process
        """
        pass
    
    @abstractmethod
    def summarize(self, text: str, max_length: Optional[int] = None) -> str:
        """Generate a summary of the input text.
        
        This is the core method that all models must implement. It should:
        1. Validate the input text
        2. Generate a summary using the model
        3. Return the summary text
        
        Args:
            text: Source document text to summarize
            max_length: Optional maximum length for the summary in words
            
        Returns:
            Summary text
            
        Raises:
            ValueError: If input is invalid
            RuntimeError: If summarization fails
        """
        pass
    
    @abstractmethod
    def validate_input(self, text: str) -> None:
        """Validate input text before summarization.
        
        This method should check:
        - Text is not None or empty
        - Text length is within model limits
        - Text encoding is valid
        
        Args:
            text: Input text to validate
            
        Raises:
            ValueError: If input is invalid
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Return metadata about the model.
        
        This method should return a dictionary containing:
        - model_name: Name of the model
        - model_version: Version of the model
        - model_type: Type of model (e.g., 'abstractive', 'extractive')
        - max_input_length: Maximum input length
        - additional model-specific metadata
        
        Returns:
            Dictionary containing model metadata
        """
        pass
    
    def _common_validation(self, text: str) -> None:
        """Common validation logic for all models.
        
        This method provides basic validation that all models should perform.
        Concrete models can call this and add their own validation.
        
        Args:
            text: Input text to validate
            
        Raises:
            ValueError: If input is invalid
        """
        if text is None:
            raise ValueError("Input text cannot be None")
        
        if not isinstance(text, str):
            raise ValueError(f"Input must be a string, got {type(text).__name__}")
        
        if not text.strip():
            raise ValueError("Input text cannot be empty or whitespace-only")
