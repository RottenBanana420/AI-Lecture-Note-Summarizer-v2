"""Model Abstraction Layer Tests.

This test suite validates the model abstraction layer design to ensure:
1. No tight coupling between SummarizationService and specific model implementations
2. All models implement the required interface correctly
3. Models can be swapped via configuration without code changes
4. Summarization is decoupled from PDF processing and retrieval components

CRITICAL: These tests are IMMUTABLE and designed to fail initially. Implementation
must adapt to satisfy these tests. DO NOT modify tests to make them pass.

Test Categories:
- TestCouplingDetection: Detect tight coupling to specific models
- TestInterfaceCompliance: Verify all models implement required interface
- TestFactoryPattern: Verify factory pattern implementation
- TestConfigurationManagement: Verify configuration handling
- TestComponentDecoupling: Verify decoupling from other system components
"""

import pytest
import ast
import importlib
import inspect
from pathlib import Path
from typing import Type, List
from unittest.mock import Mock, patch


# ============================================================================
# Category A: Tight Coupling Detection Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.summarization
class TestCouplingDetection:
    """Tests to detect tight coupling between service and specific models.
    
    These tests MUST FAIL if the service is tightly coupled to any specific
    model implementation. They verify that models can be swapped without
    changing the service code.
    """
    
    def test_service_not_coupled_to_specific_model(self):
        """SummarizationService must not import specific model classes.
        
        GIVEN: The SummarizationService module
        WHEN: Analyzing its imports
        THEN: It must not directly import concrete model classes
        
        This test parses the AST to detect direct imports of model classes.
        """
        service_file = Path(__file__).parent.parent.parent / "app" / "services" / "summarization_service.py"
        
        assert service_file.exists(), f"Service file not found: {service_file}"
        
        with open(service_file, 'r') as f:
            tree = ast.parse(f.read())
        
        # List of forbidden model class names
        forbidden_imports = [
            'FlanT5Model', 'BARTModel', 'T5Model', 'PegasusModel',
            'flan_t5_model', 'bart_model', 't5_model', 'pegasus_model'
        ]
        
        # Check all imports
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not any(forbidden in alias.name for forbidden in forbidden_imports), (
                            f"SummarizationService must not directly import {alias.name}. "
                            f"Use ModelFactory or dependency injection instead."
                        )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        full_import = f"{module}.{alias.name}"
                        assert not any(forbidden in full_import for forbidden in forbidden_imports), (
                            f"SummarizationService must not directly import {full_import}. "
                            f"Use ModelFactory or dependency injection instead."
                        )
    
    def test_no_hardcoded_model_names(self):
        """Service must not contain hardcoded model names.
        
        GIVEN: The SummarizationService module
        WHEN: Analyzing string literals in the code
        THEN: It must not contain hardcoded model identifiers
        
        This prevents tight coupling through string literals.
        """
        service_file = Path(__file__).parent.parent.parent / "app" / "services" / "summarization_service.py"
        
        with open(service_file, 'r') as f:
            content = f.read()
        
        # Model identifiers that should not be hardcoded
        forbidden_strings = [
            'facebook/bart-large-cnn',
            'google/flan-t5-base',
            'google/flan-t5-large',
            't5-base',
            't5-small',
            'google/pegasus-cnn_dailymail'
        ]
        
        for forbidden in forbidden_strings:
            assert forbidden not in content, (
                f"Service must not contain hardcoded model identifier '{forbidden}'. "
                f"Use configuration or ModelRegistry instead."
            )
    
    def test_model_swapping_without_code_changes(self):
        """Models must be swappable via configuration only.
        
        GIVEN: A SummarizationService instance
        WHEN: Different model configurations are provided
        THEN: Different models should be instantiated without code changes
        
        This test will be implemented once the factory is created.
        """
        # This test will verify that we can swap models by changing config
        # For now, it should fail because the abstraction doesn't exist yet
        
        try:
            from app.services.summarization.model_factory import ModelFactory
            from app.services.summarization.model_config import ModelConfig
            
            # Try to create different models via factory
            config1 = ModelConfig(model_name="flan-t5-base")
            model1 = ModelFactory.create_model("flan-t5-base", config1)
            
            config2 = ModelConfig(model_name="bart-large-cnn")
            model2 = ModelFactory.create_model("bart-large-cnn", config2)
            
            # Models should be different instances
            assert model1 is not model2
            assert type(model1).__name__ != type(model2).__name__
            
        except ImportError as e:
            pytest.fail(
                f"ModelFactory or ModelConfig not implemented yet: {e}. "
                f"This test will pass once the abstraction layer is created."
            )


# ============================================================================
# Category B: Interface Compliance Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.summarization
class TestInterfaceCompliance:
    """Tests to verify all models implement the required interface.
    
    These tests ensure that all model implementations follow the same
    contract defined by BaseSummarizationModel.
    """
    
    def test_base_model_exists(self):
        """BaseSummarizationModel abstract base class must exist.
        
        GIVEN: The summarization module
        WHEN: Attempting to import BaseSummarizationModel
        THEN: Import should succeed and class should be abstract
        """
        try:
            from app.services.summarization.base_model import BaseSummarizationModel
            from abc import ABC
            
            # Verify it's an abstract base class
            assert issubclass(BaseSummarizationModel, ABC), (
                "BaseSummarizationModel must inherit from ABC"
            )
            
            # Verify it has required abstract methods
            abstract_methods = [
                'summarize',
                'validate_input',
                'get_model_info'
            ]
            
            for method_name in abstract_methods:
                assert hasattr(BaseSummarizationModel, method_name), (
                    f"BaseSummarizationModel must define abstract method '{method_name}'"
                )
                
        except ImportError as e:
            pytest.fail(
                f"BaseSummarizationModel not implemented yet: {e}. "
                f"Create app/services/summarization/base_model.py"
            )
    
    def test_all_models_implement_base_interface(self):
        """All concrete models must extend BaseSummarizationModel.
        
        GIVEN: Concrete model implementations
        WHEN: Checking their inheritance
        THEN: All must extend BaseSummarizationModel
        """
        try:
            from app.services.summarization.base_model import BaseSummarizationModel
            
            # Try to import concrete models
            model_modules = [
                'app.services.summarization.models.flan_t5_model',
                'app.services.summarization.models.bart_model',
            ]
            
            for module_path in model_modules:
                try:
                    module = importlib.import_module(module_path)
                    
                    # Find model classes in the module
                    model_classes = [
                        obj for name, obj in inspect.getmembers(module)
                        if inspect.isclass(obj) 
                        and obj.__module__ == module_path
                        and name.endswith('Model')
                        and name != 'BaseSummarizationModel'
                    ]
                    
                    assert len(model_classes) > 0, (
                        f"No model classes found in {module_path}"
                    )
                    
                    for model_class in model_classes:
                        assert issubclass(model_class, BaseSummarizationModel), (
                            f"{model_class.__name__} must extend BaseSummarizationModel"
                        )
                        
                except ImportError:
                    # Model not implemented yet - expected to fail initially
                    pass
                    
        except ImportError as e:
            pytest.fail(f"BaseSummarizationModel not found: {e}")
    
    def test_all_models_have_required_methods(self):
        """All models must implement required methods.
        
        GIVEN: A concrete model instance
        WHEN: Checking for required methods
        THEN: All required methods must be present and callable
        """
        try:
            from app.services.summarization.base_model import BaseSummarizationModel
            
            required_methods = ['summarize', 'validate_input', 'get_model_info']
            required_properties = ['model_name', 'model_version', 'max_input_length']
            
            # Try to import and check FlanT5Model as example
            try:
                from app.services.summarization.models.flan_t5_model import FlanT5Model
                
                # Check methods
                for method_name in required_methods:
                    assert hasattr(FlanT5Model, method_name), (
                        f"FlanT5Model must implement method '{method_name}'"
                    )
                    method = getattr(FlanT5Model, method_name)
                    assert callable(method), (
                        f"FlanT5Model.{method_name} must be callable"
                    )
                
                # Check properties (these might be defined in __init__ or as properties)
                # We'll verify this when we can instantiate the model
                
            except ImportError:
                pytest.skip("FlanT5Model not implemented yet")
                
        except ImportError as e:
            pytest.fail(f"BaseSummarizationModel not found: {e}")
    
    def test_model_metadata_consistency(self):
        """All models must provide consistent metadata.
        
        GIVEN: Different model instances
        WHEN: Calling get_model_info()
        THEN: All must return dict with required keys
        """
        try:
            from app.services.summarization.models.flan_t5_model import FlanT5Model
            
            # This will fail until models are implemented
            model = FlanT5Model()
            info = model.get_model_info()
            
            required_keys = ['model_name', 'model_version', 'max_input_length', 'model_type']
            
            assert isinstance(info, dict), "get_model_info() must return a dictionary"
            
            for key in required_keys:
                assert key in info, (
                    f"Model info must contain '{key}' key"
                )
                
        except ImportError:
            pytest.skip("Model implementations not available yet")
        except Exception as e:
            pytest.fail(f"Model instantiation or get_model_info() failed: {e}")


# ============================================================================
# Category C: Factory Pattern Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.summarization
class TestFactoryPattern:
    """Tests for the ModelFactory implementation.
    
    These tests verify that the factory pattern is correctly implemented
    and can create models dynamically.
    """
    
    def test_factory_exists(self):
        """ModelFactory class must exist.
        
        GIVEN: The summarization module
        WHEN: Attempting to import ModelFactory
        THEN: Import should succeed
        """
        try:
            from app.services.summarization.model_factory import ModelFactory
            
            assert ModelFactory is not None
            
        except ImportError as e:
            pytest.fail(
                f"ModelFactory not implemented yet: {e}. "
                f"Create app/services/summarization/model_factory.py"
            )
    
    def test_factory_creates_correct_model(self):
        """Factory must instantiate the correct model class.
        
        GIVEN: A model name
        WHEN: Calling ModelFactory.create_model()
        THEN: Correct model instance should be returned
        """
        try:
            from app.services.summarization.model_factory import ModelFactory
            from app.services.summarization.base_model import BaseSummarizationModel
            
            # Try to create a Flan-T5 model
            model = ModelFactory.create_model("flan-t5-base")
            
            assert model is not None, "Factory must return a model instance"
            assert isinstance(model, BaseSummarizationModel), (
                "Factory must return instance of BaseSummarizationModel"
            )
            
            # Verify it's the correct model type
            model_info = model.get_model_info()
            assert 'flan-t5' in model_info['model_name'].lower(), (
                f"Expected Flan-T5 model, got {model_info['model_name']}"
            )
            
        except ImportError:
            pytest.skip("ModelFactory or models not implemented yet")
        except Exception as e:
            pytest.fail(f"Factory failed to create model: {e}")
    
    def test_factory_handles_unknown_model(self):
        """Factory must raise clear error for unknown models.
        
        GIVEN: An unknown model name
        WHEN: Calling ModelFactory.create_model()
        THEN: Should raise ValueError with clear message
        """
        try:
            from app.services.summarization.model_factory import ModelFactory
            
            with pytest.raises(ValueError, match="Unknown model|not supported|not found"):
                ModelFactory.create_model("unknown-model-xyz")
                
        except ImportError:
            pytest.skip("ModelFactory not implemented yet")
    
    def test_factory_respects_configuration(self):
        """Factory must apply configuration to created models.
        
        GIVEN: A model configuration
        WHEN: Creating a model with custom config
        THEN: Model should use the provided configuration
        """
        try:
            from app.services.summarization.model_factory import ModelFactory
            from app.services.summarization.model_config import ModelConfig
            
            custom_config = ModelConfig(
                model_name="flan-t5-base",
                max_length=200,
                min_length=50,
                num_beams=4
            )
            
            model = ModelFactory.create_model("flan-t5-base", config=custom_config)
            
            # Verify configuration was applied
            # This assumes models expose their config
            assert hasattr(model, 'config'), "Model must expose its configuration"
            assert model.config.max_length == 200, "Custom max_length not applied"
            assert model.config.min_length == 50, "Custom min_length not applied"
            assert model.config.num_beams == 4, "Custom num_beams not applied"
            
        except ImportError:
            pytest.skip("ModelFactory or ModelConfig not implemented yet")
        except Exception as e:
            pytest.fail(f"Configuration not properly applied: {e}")
    
    def test_factory_lists_available_models(self):
        """Factory must provide list of available models.
        
        GIVEN: The ModelFactory
        WHEN: Calling list_available_models()
        THEN: Should return list of supported model names
        """
        try:
            from app.services.summarization.model_factory import ModelFactory
            
            available_models = ModelFactory.list_available_models()
            
            assert isinstance(available_models, list), (
                "list_available_models() must return a list"
            )
            assert len(available_models) > 0, (
                "At least one model must be registered"
            )
            assert "flan-t5-base" in available_models, (
                "flan-t5-base should be available as default model"
            )
            
        except ImportError:
            pytest.skip("ModelFactory not implemented yet")
        except AttributeError:
            pytest.fail("ModelFactory must implement list_available_models() method")


# ============================================================================
# Category D: Configuration Management Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.summarization
class TestConfigurationManagement:
    """Tests for configuration schema and validation.
    
    These tests verify that model configurations are properly validated
    and can be managed consistently.
    """
    
    def test_model_config_exists(self):
        """ModelConfig class must exist.
        
        GIVEN: The summarization module
        WHEN: Attempting to import ModelConfig
        THEN: Import should succeed
        """
        try:
            from app.services.summarization.model_config import ModelConfig
            
            assert ModelConfig is not None
            
        except ImportError as e:
            pytest.fail(
                f"ModelConfig not implemented yet: {e}. "
                f"Create app/services/summarization/model_config.py"
            )
    
    def test_config_schema_validation(self):
        """ModelConfig must validate parameters.
        
        GIVEN: Invalid configuration parameters
        WHEN: Creating a ModelConfig instance
        THEN: Should raise validation error
        """
        try:
            from app.services.summarization.model_config import ModelConfig
            from pydantic import ValidationError
            
            # Test invalid max_length (negative)
            with pytest.raises(ValidationError):
                ModelConfig(model_name="flan-t5-base", max_length=-100)
            
            # Test invalid min_length (greater than max_length)
            with pytest.raises(ValidationError):
                ModelConfig(model_name="flan-t5-base", max_length=50, min_length=100)
            
            # Test invalid num_beams (negative)
            with pytest.raises(ValidationError):
                ModelConfig(model_name="flan-t5-base", num_beams=-1)
            
            # Test invalid temperature (out of range)
            with pytest.raises(ValidationError):
                ModelConfig(model_name="flan-t5-base", temperature=2.5)
                
        except ImportError:
            pytest.skip("ModelConfig not implemented yet")
    
    def test_default_configs_valid(self):
        """Default configurations for all models must be valid.
        
        GIVEN: The ModelRegistry with default configs
        WHEN: Retrieving default configurations
        THEN: All must be valid ModelConfig instances
        """
        try:
            from app.services.summarization.model_config import ModelRegistry, ModelConfig
            
            # Get default configs for known models
            model_names = ["flan-t5-base", "bart-large-cnn"]
            
            for model_name in model_names:
                try:
                    config = ModelRegistry.get_default_config(model_name)
                    
                    assert isinstance(config, ModelConfig), (
                        f"Default config for {model_name} must be ModelConfig instance"
                    )
                    assert config.model_name == model_name, (
                        f"Config model_name mismatch for {model_name}"
                    )
                    
                except KeyError:
                    # Model not registered yet - acceptable during development
                    pass
                    
        except ImportError:
            pytest.skip("ModelRegistry not implemented yet")
        except AttributeError:
            pytest.fail("ModelRegistry must implement get_default_config() method")
    
    def test_config_override_mechanism(self):
        """Configuration must be overridable at runtime.
        
        GIVEN: A default configuration
        WHEN: Overriding specific parameters
        THEN: Only specified parameters should change
        """
        try:
            from app.services.summarization.model_config import ModelConfig
            
            # Create base config
            base_config = ModelConfig(
                model_name="flan-t5-base",
                max_length=150,
                min_length=30,
                num_beams=4
            )
            
            # Override specific parameters
            overridden_config = base_config.model_copy(update={"max_length": 200})
            
            assert overridden_config.max_length == 200, "max_length not overridden"
            assert overridden_config.min_length == 30, "min_length should remain unchanged"
            assert overridden_config.num_beams == 4, "num_beams should remain unchanged"
            
        except ImportError:
            pytest.skip("ModelConfig not implemented yet")


# ============================================================================
# Category E: Component Decoupling Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.summarization
class TestComponentDecoupling:
    """Tests to verify summarization is decoupled from other components.
    
    These tests ensure that the summarization module doesn't depend on
    PDF processing, retrieval, or database components.
    """
    
    def test_summarization_independent_of_pdf_processing(self):
        """Summarization must not import PDF processing modules.
        
        GIVEN: All summarization module files
        WHEN: Analyzing their imports
        THEN: None should import PDF processing modules
        """
        summarization_dir = Path(__file__).parent.parent.parent / "app" / "services" / "summarization"
        
        if not summarization_dir.exists():
            pytest.skip("Summarization directory not created yet")
        
        forbidden_imports = [
            'pdf_extractor', 'pdf_normalizer', 'pdf_cleaner', 'pdf_segmenter',
            'PDFExtractor', 'PDFNormalizer', 'PDFCleaner', 'PDFSegmenter'
        ]
        
        python_files = list(summarization_dir.rglob("*.py"))
        
        for py_file in python_files:
            if py_file.name == '__init__.py':
                continue
                
            with open(py_file, 'r') as f:
                content = f.read()
                tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            assert not any(forbidden in alias.name for forbidden in forbidden_imports), (
                                f"{py_file.name} must not import {alias.name}. "
                                f"Summarization must be independent of PDF processing."
                            )
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            full_import = f"{module}.{alias.name}"
                            assert not any(forbidden in full_import for forbidden in forbidden_imports), (
                                f"{py_file.name} must not import {full_import}. "
                                f"Summarization must be independent of PDF processing."
                            )
    
    def test_summarization_independent_of_retrieval(self):
        """Summarization must not import retrieval modules.
        
        GIVEN: All summarization module files
        WHEN: Analyzing their imports
        THEN: None should import retrieval or search modules
        """
        summarization_dir = Path(__file__).parent.parent.parent / "app" / "services" / "summarization"
        
        if not summarization_dir.exists():
            pytest.skip("Summarization directory not created yet")
        
        forbidden_imports = [
            'retrieval', 'search', 'vector_store', 'embedding'
        ]
        
        python_files = list(summarization_dir.rglob("*.py"))
        
        for py_file in python_files:
            if py_file.name == '__init__.py':
                continue
                
            with open(py_file, 'r') as f:
                content = f.read()
            
            for forbidden in forbidden_imports:
                assert forbidden not in content.lower() or 'embedding' in py_file.name.lower(), (
                    f"{py_file.name} should not reference '{forbidden}'. "
                    f"Summarization must be independent of retrieval."
                )
    
    def test_summarization_uses_only_text_input(self):
        """Summarization must only depend on text input, not Document models.
        
        GIVEN: The BaseSummarizationModel interface
        WHEN: Checking the summarize() method signature
        THEN: It should accept text (str) not Document objects
        """
        try:
            from app.services.summarization.base_model import BaseSummarizationModel
            import inspect
            
            # Get the summarize method signature
            summarize_method = getattr(BaseSummarizationModel, 'summarize')
            sig = inspect.signature(summarize_method)
            
            # Check parameters (excluding self)
            params = [p for name, p in sig.parameters.items() if name != 'self']
            
            assert len(params) >= 1, "summarize() must accept at least one parameter (text)"
            
            # First parameter should be text
            first_param = params[0]
            
            # Check if type hint exists and is str
            if first_param.annotation != inspect.Parameter.empty:
                # Get the string representation of the annotation
                annotation_str = str(first_param.annotation)
                assert 'str' in annotation_str.lower(), (
                    f"First parameter of summarize() must be str, got {first_param.annotation}"
                )
                assert 'Document' not in annotation_str, (
                    "summarize() must not accept Document objects directly"
                )
                
        except ImportError:
            pytest.skip("BaseSummarizationModel not implemented yet")
        except AttributeError:
            pytest.fail("BaseSummarizationModel must define summarize() method")
