#!/usr/bin/env python3
"""
Test script to verify dynamic parameter filtering works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from litassist.llm import get_model_family, get_model_parameters, supports_system_messages


def test_model_family_detection():
    """Test that model families are correctly identified."""
    test_cases = [
        ("openai/o3-pro", "openai_reasoning"),
        ("openai/o1-pro", "openai_reasoning"),
        ("openai/o5", "openai_reasoning"),  # Future model
        ("anthropic/claude-3-sonnet", "anthropic"),
        ("anthropic/claude-4", "anthropic"),
        ("google/gemini-pro", "google"),
        ("google/palm-2", "google"),
        ("openai/gpt-4", "openai_standard"),
        ("openai/gpt-4-turbo", "openai_standard"),
        ("x-ai/grok-3", "xai"),
        ("meta/llama-2-70b", "meta"),
        ("mistral/mixtral-8x7b", "mistral"),
        ("cohere/command", "cohere"),
        ("unknown/model", "default"),
    ]
    
    print("Testing model family detection...")
    for model, expected_family in test_cases:
        actual_family = get_model_family(model)
        status = "[Y]" if actual_family == expected_family else "[N]"
        print(f"{status} {model} -> {actual_family} (expected: {expected_family})")


def test_parameter_filtering():
    """Test that parameters are correctly filtered based on model."""
    test_cases = [
        # o3-pro: only max_completion_tokens and reasoning_effort
        ("openai/o3-pro", {
            "temperature": 0.7,
            "max_tokens": 1000,
            "reasoning_effort": "low",
            "top_p": 0.9,
        }, {
            "max_completion_tokens": 1000,  # transformed from max_tokens
            "reasoning_effort": "low",
        }),
        
        # Claude: standard parameters
        ("anthropic/claude-3", {
            "temperature": 0.5,
            "max_tokens": 2000,
            "top_p": 0.8,
            "top_k": 50,
            "reasoning_effort": "high",  # should be dropped
        }, {
            "temperature": 0.5,
            "max_tokens": 2000,
            "top_p": 0.8,
            "top_k": 50,
        }),
        
        # Gemini: with transforms
        ("google/gemini-pro", {
            "temperature": 0.3,
            "max_tokens": 1500,
            "candidate_count": 3,
        }, {
            "temperature": 0.3,
            "max_output_tokens": 1500,  # transformed
            "candidate_count": 3,
        }),
        
        # Unknown model: only basic parameters
        ("custom/unknown-model", {
            "temperature": 0.5,
            "max_tokens": 1000,
            "top_p": 0.9,
            "custom_param": "value",  # should be dropped
        }, {
            "temperature": 0.5,
            "max_tokens": 1000,
            "top_p": 0.9,
        }),
    ]
    
    print("\nTesting parameter filtering...")
    for model, input_params, expected_params in test_cases:
        actual_params = get_model_parameters(model, input_params)
        match = actual_params == expected_params
        status = "[Y]" if match else "[N]"
        print(f"{status} {model}")
        if not match:
            print(f"  Expected: {expected_params}")
            print(f"  Actual:   {actual_params}")


def test_system_message_support():
    """Test system message support detection."""
    test_cases = [
        ("openai/o3-pro", False),
        ("openai/o1-pro", False),
        ("openai/o5", False),  # Future reasoning model
        ("anthropic/claude-3", True),
        ("openai/gpt-4", True),
        ("google/gemini-pro", True),
        ("x-ai/grok-3", True),
    ]
    
    print("\nTesting system message support...")
    for model, expected_support in test_cases:
        actual_support = supports_system_messages(model)
        status = "[Y]" if actual_support == expected_support else "[N]"
        support_text = "supports" if actual_support else "no support"
        print(f"{status} {model} -> {support_text}")


def test_future_proofing():
    """Test that the system handles future model variations."""
    print("\nTesting future-proofing...")
    
    # Future OpenAI reasoning models should work without code changes
    future_models = [
        "openai/o4-pro",
        "openai/o5-pro",
        "openai/o10",
    ]
    
    for model in future_models:
        family = get_model_family(model)
        params = get_model_parameters(model, {"max_tokens": 1000, "temperature": 0.7})
        system_support = supports_system_messages(model)
        
        print(f"[Y] {model}:")
        print(f"  - Family: {family}")
        print(f"  - Parameters: {params}")
        print(f"  - System messages: {'No' if not system_support else 'Yes'}")


if __name__ == "__main__":
    print("Dynamic LLM Parameter System Tests")
    print("=" * 50)
    
    test_model_family_detection()
    test_parameter_filtering()
    test_system_message_support()
    test_future_proofing()
    
    print("\n[PASS] All tests completed!")