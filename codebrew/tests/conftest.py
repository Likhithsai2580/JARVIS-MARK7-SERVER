import os
import sys
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import app
from main import CodeBrew, CodeBrewConfig
from llm.base import LLM, Role
from llm._llmserver import LLMServer, GPT35_TURBO

# Load test environment variables
load_dotenv(".env.test", override=True)

# Mock LLM for testing
class MockLLM(LLM):
    def __init__(self, responses=None):
        super().__init__()
        self.responses = responses or {
            "Hello": "Hello! How can I help you?",
            "Write a Python function": """```python
def example_function():
    print("Hello, World!")

```""",
        }
        self.messages = []
        self.calls = []

    def run(self):
        last_message = self.messages[-1].content if self.messages else ""
        self.calls.append(last_message)
        for key, response in self.responses.items():
            if key in last_message:
                return response
        return "I don't understand that request."

    def addMessage(self, role: Role, content: str):
        self.messages.append(type('Message', (), {'role': role, 'content': content}))

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def mock_llm() -> MockLLM:
    """Create a mock LLM instance."""
    return MockLLM()

@pytest.fixture(scope="function")
def codebrew_config() -> CodeBrewConfig:
    """Create a test configuration for CodeBrew."""
    return CodeBrewConfig(
        max_retries=2,
        keep_history=True,
        verbose=False,
        timeout=5.0,
        max_output_length=1000,
        cache_size=10
    )

@pytest.fixture(scope="function")
def codebrew(mock_llm: MockLLM, codebrew_config: CodeBrewConfig) -> CodeBrew:
    """Create a CodeBrew instance with mock LLM."""
    brew = CodeBrew(llm=mock_llm, config=codebrew_config)
    yield brew
    brew.cleanup()

@pytest.fixture(scope="session")
def test_client() -> Generator:
    """Create a TestClient instance."""
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope="session")
async def async_client() -> AsyncGenerator:
    """Create an AsyncClient instance."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture(scope="function")
def api_key() -> str:
    """Generate a test API key."""
    return "test_api_key_12345"

@pytest.fixture(scope="function")
def test_prompt() -> str:
    """Create a test prompt."""
    return "Write a Python function"

@pytest.fixture(scope="function")
def mock_env(monkeypatch):
    """Set up test environment variables."""
    env_vars = {
        "HOST": "localhost",
        "PORT": "8000",
        "INSTANCE_ID": "0",
        "MAX_INSTANCES": "5",
        "CACHE_TTL": "60",
        "MAX_CACHE_SIZE": "100",
        "ENVIRONMENT": "test"
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars

@pytest.fixture(scope="function")
def captured_output(capsys):
    """Capture stdout/stderr for testing."""
    return capsys

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up after each test."""
    yield
    # Clean up any test files or resources
    if os.path.exists("codebrew.log"):
        os.remove("codebrew.log")
    if os.path.exists("error.log"):
        os.remove("error.log")

# Custom markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    markers = [
        "unit: Unit tests",
        "integration: Integration tests",
        "api: API endpoint tests",
        "llm: LLM integration tests",
        "async: Asynchronous tests",
        "slow: Tests that take longer to run"
    ]
    for marker in markers:
        config.addinivalue_line("markers", marker)

# Skip slow tests by default
def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run tests marked as slow"
    )

def pytest_collection_modifyitems(config, items):
    """Skip slow tests unless --run-slow is specified."""
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="Need --run-slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow) 