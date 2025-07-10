"""
Shared utilities for test scripts to ensure consistent error handling and reporting.
"""

import json
import traceback
from datetime import datetime


class ErrorHandler:
    """Centralized error handling for test scripts"""

    @classmethod
    def format_error(cls, error, context=None):
        """
        Format an error with comprehensive details for debugging.

        Args:
            error: The exception object
            context: Additional context about where/when the error occurred

        Returns:
            dict: Comprehensive error information
        """
        error_info = {
            "message": str(error),
            "type": error.__class__.__name__,
            "timestamp": datetime.now().isoformat(),
            "traceback": traceback.format_exc(),
            "context": context or {},
        }

        # Add API response details if available (for HTTP errors)
        if hasattr(error, "response"):
            try:
                if hasattr(error.response, "json"):
                    error_info["api_response"] = error.response.json()
                else:
                    error_info["api_response"] = str(error.response)
                error_info["status_code"] = getattr(error.response, "status_code", None)
            except Exception:
                error_info["api_response"] = (
                    str(error.response) if error.response else None
                )

        # Add OpenAI/OpenRouter specific error details
        if hasattr(error, "error_code"):
            error_info["error_code"] = error.error_code
        if hasattr(error, "error_message"):
            error_info["error_message"] = error.error_message
        if hasattr(error, "error_type"):
            error_info["error_type"] = error.error_type

        # Add request details if available
        if hasattr(error, "request"):
            try:
                error_info["request_details"] = {
                    "url": getattr(error.request, "url", None),
                    "method": getattr(error.request, "method", None),
                    "headers": dict(getattr(error.request, "headers", {})),
                }
                # Remove sensitive data from headers
                if "authorization" in error_info["request_details"]["headers"]:
                    error_info["request_details"]["headers"][
                        "authorization"
                    ] = "[REDACTED]"
            except Exception:
                pass

        return error_info

    @classmethod
    def print_error_details(cls, error_info, prefix="ERROR"):
        """
        Print formatted error details to console.

        Args:
            error_info: Error information dict from format_error()
            prefix: String prefix for the error output
        """
        print(f"\n[ERROR] {prefix} DETAILS:")
        print(f"  Type: {error_info['type']}")
        print(f"  Message: {error_info['message']}")
        print(f"  Time: {error_info['timestamp']}")

        if error_info.get("context"):
            print(f"  Context: {json.dumps(error_info['context'], indent=4)}")

        if error_info.get("status_code"):
            print(f"  HTTP Status: {error_info['status_code']}")

        if error_info.get("api_response"):
            print(f"  API Response: {json.dumps(error_info['api_response'], indent=4)}")

        if error_info.get("error_code"):
            print(f"  Error Code: {error_info['error_code']}")

        if error_info.get("request_details"):
            print(f"  Request: {json.dumps(error_info['request_details'], indent=4)}")

        print("  Full Traceback:")
        # Print traceback with indentation
        for line in error_info["traceback"].splitlines():
            print(f"    {line}")
        print()


class EnhancedTestResult:
    """Enhanced TestResult class with comprehensive error handling"""

    def __init__(self, service, test_name):
        self.service = service
        self.test_name = test_name
        self.start_time = datetime.now()
        self.status = None
        self.latency_ms = None
        self.details = {}
        self.error = None
        self.raw_error = None

    def success(self, **details):
        self.status = "SUCCESS"
        self.latency_ms = int((datetime.now() - self.start_time).total_seconds() * 1000)
        self.details = details
        return self

    def failure(self, error, context=None):
        self.status = "FAILURE"
        self.latency_ms = int((datetime.now() - self.start_time).total_seconds() * 1000)
        self.raw_error = error
        self.error = ErrorHandler.format_error(error, context)

        # Print immediate error details for debugging
        ErrorHandler.print_error_details(
            self.error, f"TEST FAILURE [{self.service}:{self.test_name}]"
        )

        return self

    def to_dict(self):
        result = {
            "service": self.service,
            "test": self.test_name,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "timestamp": self.start_time.isoformat(),
        }
        if self.details:
            result["details"] = self.details
        if self.error:
            result["error"] = self.error
        return result


def print_result(result):
    """
    Enhanced result printing with detailed error information.

    Args:
        result: TestResult object or EnhancedTestResult object
    """
    res = result.to_dict() if hasattr(result, "to_dict") else result

    # Determine color based on status (for terminals that support ANSI colors)
    color_start = "\033[92m" if res["status"] == "SUCCESS" else "\033[91m"
    color_end = "\033[0m"

    print(
        f"{color_start}[{res['status']}]{color_end} {res['service']} - {res['test']} ({res['latency_ms']}ms)"
    )

    if "details" in res:
        for k, v in res["details"].items():
            if (
                k in ["sample_output", "response"]
                and isinstance(v, str)
                and len(v) > 100
            ):
                print(f"  {k}: {v[:100]}...")
            elif k == "quality_checks" and isinstance(v, dict):
                print(f"  {k}:")
                for check_name, check_result in v.items():
                    check_symbol = "[Y]" if check_result else "[N]"
                    check_color = "\033[92m" if check_result else "\033[91m"
                    print(f"    {check_color}{check_symbol}{color_end} {check_name}")
            else:
                print(f"  {k}: {v}")

    # Enhanced error printing - basic summary only since detailed error was already printed
    if "error" in res:
        error_info = res["error"]
        if isinstance(error_info, dict):
            print(
                f"  Error Summary: {error_info.get('type', 'Unknown')} - {error_info.get('message', 'No message')}"
            )
            if error_info.get("status_code"):
                print(f"  HTTP Status: {error_info['status_code']}")
        else:
            print(f"  Error: {error_info}")

    print()  # Add empty line for readability
