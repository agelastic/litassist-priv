"""
Tests for universal thinking_effort parameter handling.

Tests the conversion of universal thinking_effort parameter to
model-specific thinking/reasoning parameters.
"""

import pytest
from unittest.mock import patch, MagicMock
from litassist.llm import (
    convert_thinking_effort,
    get_model_parameters,
    LLMClientFactory,
)


class TestThinkingEffortConversion:
    """Test thinking effort parameter conversion for different model families."""
    
    def test_openai_reasoning_conversion(self):
        """Test OpenAI o1/o3 model reasoning_effort conversion."""
        # Test direct mapping for low/medium/high
        assert convert_thinking_effort("low", "openai_reasoning") == {"reasoning_effort": "low"}
        assert convert_thinking_effort("medium", "openai_reasoning") == {"reasoning_effort": "medium"}
        assert convert_thinking_effort("high", "openai_reasoning") == {"reasoning_effort": "high"}
        
        # Test max maps to high
        assert convert_thinking_effort("max", "openai_reasoning") == {"reasoning_effort": "high"}
        
        # Test none returns empty
        assert convert_thinking_effort("none", "openai_reasoning") == {}
        
        # Test default fallback
        assert convert_thinking_effort("invalid", "openai_reasoning") == {"reasoning_effort": "medium"}
    
    def test_anthropic_thinking_conversion(self):
        """Test Anthropic Claude thinking object conversion."""
        # Test none returns empty
        assert convert_thinking_effort("none", "anthropic") == {}
        
        # Test low budget
        result = convert_thinking_effort("low", "anthropic")
        assert result == {
            "thinking": {
                "thinking": "enabled",
                "budget_tokens": 1024
            }
        }
        
        # Test medium budget
        result = convert_thinking_effort("medium", "anthropic")
        assert result["thinking"]["budget_tokens"] == 8192
        
        # Test high budget
        result = convert_thinking_effort("high", "anthropic")
        assert result["thinking"]["budget_tokens"] == 16384
        
        # Test max budget
        result = convert_thinking_effort("max", "anthropic")
        assert result["thinking"]["budget_tokens"] == 32768
    
    def test_google_thinking_config_conversion(self):
        """Test Google Gemini thinking_config conversion."""
        # Test none disables thinking
        assert convert_thinking_effort("none", "google") == {
            "thinking_config": {"thinking_budget": 0}
        }
        
        # Test low budget
        result = convert_thinking_effort("low", "google")
        assert result == {
            "thinking_config": {
                "include_thoughts": True,
                "thinking_budget": -1  # Let model control for low budget
            }
        }
        
        # Test medium budget
        result = convert_thinking_effort("medium", "google")
        assert result["thinking_config"]["thinking_budget"] == -1
        assert result["thinking_config"]["include_thoughts"] is True
        
        # Test high budget
        result = convert_thinking_effort("high", "google")
        assert result["thinking_config"]["thinking_budget"] == -1
        
        # Test max budget
        result = convert_thinking_effort("max", "google")
        assert result["thinking_config"]["thinking_budget"] == -1
    
    def test_unknown_model_family(self):
        """Test that unknown model families return empty dict."""
        assert convert_thinking_effort("high", "unknown") == {}
        assert convert_thinking_effort("medium", "random") == {}


class TestModelParameterFiltering:
    """Test that thinking_effort is properly filtered for different models."""
    
    def test_openai_o3_pro_thinking_effort(self):
        """Test o3-pro properly transforms thinking_effort to reasoning_effort."""
        params = {
            "thinking_effort": "high",
            "temperature": 0.5,  # Should be filtered
            "max_tokens": 1000,
        }
        
        filtered = get_model_parameters("openai/o3-pro", params)
        
        # Should have reasoning_effort, not thinking_effort
        assert "reasoning_effort" in filtered
        assert filtered["reasoning_effort"] == "high"
        assert "thinking_effort" not in filtered
        
        # Should transform max_tokens
        assert "max_completion_tokens" in filtered
        assert filtered["max_completion_tokens"] == 1000
        
        # Should not have temperature
        assert "temperature" not in filtered
    
    def test_anthropic_claude_thinking_effort(self):
        """Test Claude properly transforms thinking_effort to thinking object."""
        params = {
            "thinking_effort": "medium",
            "temperature": 0.3,
            "max_tokens": 2000,
        }
        
        filtered = get_model_parameters("anthropic/claude-opus-4.1", params)
        
        # Should have thinking object
        assert "thinking" in filtered
        assert filtered["thinking"]["thinking"] == "enabled"
        assert filtered["thinking"]["budget_tokens"] == 8192
        assert "thinking_effort" not in filtered
        
        # Should keep other params
        assert filtered["temperature"] == 0.3
        assert filtered["max_tokens"] == 2000
    
    def test_google_gemini_thinking_effort(self):
        """Test Gemini properly transforms thinking_effort to thinking_config."""
        params = {
            "thinking_effort": "low",
            "temperature": 0.1,
            "max_tokens": 1500,
        }
        
        filtered = get_model_parameters("google/gemini-2.5-pro", params)
        
        # Should have thinking_config
        assert "thinking_config" in filtered
        assert filtered["thinking_config"]["include_thoughts"] is True
        assert filtered["thinking_config"]["thinking_budget"] == -1
        assert "thinking_effort" not in filtered
        
        # Should keep other params
        assert filtered["temperature"] == 0.1
        assert filtered["max_tokens"] == 1500
    
    def test_model_without_thinking_support(self):
        """Test that models without thinking support ignore thinking_effort."""
        params = {
            "thinking_effort": "high",
            "temperature": 0.7,
            "max_tokens": 1000,
        }
        
        # GPT-4 standard doesn't support thinking
        filtered = get_model_parameters("openai/gpt-4", params)
        
        # Should not have any thinking-related params
        assert "thinking_effort" not in filtered
        assert "reasoning_effort" not in filtered
        assert "thinking" not in filtered
        assert "thinking_config" not in filtered
        
        # Should keep supported params
        assert filtered["temperature"] == 0.7
        assert filtered["max_tokens"] == 1000


class TestLLMClientFactoryThinkingEffort:
    """Test that LLMClientFactory properly handles thinking_effort in configs."""
    
    @patch("litassist.llm.CONFIG")
    def test_strategy_command_thinking_effort(self, mock_config):
        """Test strategy command uses thinking_effort."""
        mock_config.use_token_limits = False
        
        client = LLMClientFactory.for_command("strategy")
        
        # Check that thinking_effort is in default params
        assert "thinking_effort" in client.default_params
        assert client.default_params["thinking_effort"] == "high"
    
    @patch("litassist.llm.CONFIG")
    def test_lookup_command_thinking_effort(self, mock_config):
        """Test lookup command uses thinking_effort for Gemini."""
        mock_config.use_token_limits = False
        
        client = LLMClientFactory.for_command("lookup")
        
        # Check that thinking_effort is in default params
        assert "thinking_effort" in client.default_params
        assert client.default_params["thinking_effort"] == "low"
    
    @patch("litassist.llm.CONFIG")
    def test_brainstorm_orthodox_thinking_effort(self, mock_config):
        """Test brainstorm-orthodox uses thinking_effort for Claude."""
        mock_config.use_token_limits = False
        
        client = LLMClientFactory.for_command("brainstorm", "orthodox")
        
        # Check that thinking_effort is in default params
        assert "thinking_effort" in client.default_params
        assert client.default_params["thinking_effort"] == "medium"
    
    @patch("litassist.llm.CONFIG")  
    def test_override_thinking_effort(self, mock_config):
        """Test that thinking_effort can be overridden."""
        mock_config.use_token_limits = False
        
        client = LLMClientFactory.for_command("strategy", thinking_effort="low")
        
        # Check override worked
        assert client.default_params["thinking_effort"] == "low"


class TestBackwardCompatibility:
    """Test that existing reasoning_effort configs still work."""
    
    def test_reasoning_effort_still_works(self):
        """Test that direct reasoning_effort parameter still works for o3-pro."""
        params = {
            "reasoning_effort": "high",  # Using old parameter name directly
            "max_tokens": 1000,
        }
        
        filtered = get_model_parameters("openai/o3-pro", params)
        
        # Should keep reasoning_effort as-is since it's in allowed list
        assert "reasoning_effort" in filtered
        assert filtered["reasoning_effort"] == "high"
    
    def test_both_parameters_prefer_thinking_effort(self):
        """Test that thinking_effort takes precedence if both are present."""
        params = {
            "thinking_effort": "low",  # Universal parameter
            "reasoning_effort": "high",  # Direct parameter
            "max_tokens": 1000,
        }
        
        filtered = get_model_parameters("openai/o3-pro", params)
        
        # thinking_effort conversion should override direct parameter
        assert "reasoning_effort" in filtered
        assert filtered["reasoning_effort"] == "low"  # From thinking_effort, not direct


if __name__ == "__main__":
    pytest.main([__file__, "-v"])