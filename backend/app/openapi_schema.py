"""OpenAPI Schema Generation and Documentation."""

from typing import Dict, Any
from app.main import app

def get_openapi_schema() -> Dict[str, Any]:
    """Get the OpenAPI schema for the application."""
    return app.openapi()


def generate_api_docs() -> None:
    """Generate API documentation."""
    schema = get_openapi_schema()

    # Print endpoints
    print("# EchoMind API Endpoints\n")

    if "paths" in schema:
        for path, methods in schema["paths"].items():
            for method, details in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    summary = details.get("summary", "")
                    description = details.get("description", "")
                    print(f"### {method.upper()} {path}")
                    if summary:
                        print(f"**Summary**: {summary}")
                    if description:
                        print(f"**Description**: {description}")

                    # Parameters
                    if "parameters" in details:
                        print("**Parameters**:")
                        for param in details["parameters"]:
                            name = param.get("name", "")
                            required = param.get("required", False)
                            print(f"  - `{name}` {'(required)' if required else '(optional)'}")

                    # Request body
                    if "requestBody" in details:
                        print("**Request Body**: JSON")

                    # Response
                    if "responses" in details:
                        print("**Responses**:")
                        for code, response in details["responses"].items():
                            print(f"  - {code}: {response.get('description', '')}")

                    print()


if __name__ == "__main__":
    generate_api_docs()
