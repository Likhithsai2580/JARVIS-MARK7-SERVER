import pytest
from unittest.mock import patch, MagicMock
from llm.base import LLM, Role
from llm._llmserver import LLMServer, GPT35_TURBO

pytestmark = pytest.mark.asyncio

class TestLLMIntegration:
    """Test suite for LLM integration."""

    @pytest.mark.llm
    async def test_mock_llm_basic(self, mock_llm):
        """Test basic mock LLM functionality."""
        mock_llm.addMessage(Role.user, "Hello")
        response = mock_llm.run()
        assert "Hello" in response
        assert len(mock_llm.calls) == 1

    @pytest.mark.llm
    async def test_mock_llm_code_generation(self, mock_llm):
        """Test code generation in mock LLM."""
        mock_llm.addMessage(Role.user, "Write a Python function")
        response = mock_llm.run()
        assert "```python" in response
        assert "def" in response
        assert "print" in response

    @pytest.mark.llm
    async def test_mock_llm_unknown_request(self, mock_llm):
        """Test mock LLM response to unknown request."""
        mock_llm.addMessage(Role.user, "Unknown request")
        response = mock_llm.run()
        assert "don't understand" in response.lower()

    @pytest.mark.llm
    async def test_mock_llm_message_history(self, mock_llm):
        """Test message history in mock LLM."""
        messages = [
            (Role.user, "Hello"),
            (Role.assistant, "Hi there!"),
            (Role.user, "How are you?")
        ]
        for role, content in messages:
            mock_llm.addMessage(role, content)
        
        assert len(mock_llm.messages) == len(messages)
        for i, (role, content) in enumerate(messages):
            assert mock_llm.messages[i].role == role
            assert mock_llm.messages[i].content == content

    @pytest.mark.llm
    @pytest.mark.slow
    async def test_llm_server_initialization(self):
        """Test LLM server initialization."""
        with patch('llm._llmserver.requests.post') as mock_post:
            mock_post.return_value.json.return_value = {"choices": [{"message": {"content": "Test response"}}]}
            mock_post.return_value.status_code = 200
            
            server = LLMServer(
                model=GPT35_TURBO,
                server_url="http://test-server"
            )
            assert server.model == GPT35_TURBO
            assert server.server_url == "http://test-server"

    @pytest.mark.llm
    @pytest.mark.integration
    async def test_llm_server_run(self):
        """Test LLM server run method."""
        with patch('llm._llmserver.requests.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "choices": [{"message": {"content": "Test response"}}]
            }
            mock_post.return_value.status_code = 200
            
            server = LLMServer(
                model=GPT35_TURBO,
                server_url="http://test-server"
            )
            server.addMessage(Role.user, "Test prompt")
            response = server.run()
            
            assert response == "Test response"
            mock_post.assert_called_once()

    @pytest.mark.llm
    async def test_llm_server_error_handling(self):
        """Test LLM server error handling."""
        with patch('llm._llmserver.requests.post') as mock_post:
            mock_post.return_value.status_code = 500
            mock_post.return_value.text = "Server error"
            
            server = LLMServer(
                model=GPT35_TURBO,
                server_url="http://test-server"
            )
            server.addMessage(Role.user, "Test prompt")
            
            with pytest.raises(Exception) as exc_info:
                server.run()
            assert "Server error" in str(exc_info.value)

    @pytest.mark.llm
    @pytest.mark.integration
    async def test_llm_server_retry_mechanism(self):
        """Test LLM server retry mechanism."""
        with patch('llm._llmserver.requests.post') as mock_post:
            # First call fails, second succeeds
            mock_post.side_effect = [
                MagicMock(status_code=500, text="Error"),
                MagicMock(
                    status_code=200,
                    json=lambda: {"choices": [{"message": {"content": "Success"}}]}
                )
            ]
            
            server = LLMServer(
                model=GPT35_TURBO,
                server_url="http://test-server"
            )
            server.addMessage(Role.user, "Test prompt")
            response = server.run()
            
            assert response == "Success"
            assert mock_post.call_count == 2

    @pytest.mark.llm
    async def test_llm_server_message_format(self):
        """Test LLM server message formatting."""
        with patch('llm._llmserver.requests.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "choices": [{"message": {"content": "Response"}}]
            }
            mock_post.return_value.status_code = 200
            
            server = LLMServer(
                model=GPT35_TURBO,
                server_url="http://test-server"
            )
            
            # Add different types of messages
            messages = [
                (Role.system, "System message"),
                (Role.user, "User message"),
                (Role.assistant, "Assistant message")
            ]
            for role, content in messages:
                server.addMessage(role, content)
            
            server.run()
            
            # Check the request payload
            call_args = mock_post.call_args[1]['json']
            assert 'messages' in call_args
            assert len(call_args['messages']) == len(messages)
            for i, (role, content) in enumerate(messages):
                assert call_args['messages'][i]['role'] == role.value
                assert call_args['messages'][i]['content'] == content

    @pytest.mark.llm
    @pytest.mark.slow
    async def test_llm_server_streaming(self):
        """Test LLM server streaming functionality."""
        with patch('llm._llmserver.requests.post') as mock_post:
            # Simulate streaming response
            mock_post.return_value.iter_lines.return_value = [
                b'data: {"choices":[{"delta":{"content":"Part 1"}}]}',
                b'data: {"choices":[{"delta":{"content":"Part 2"}}]}',
                b'data: [DONE]'
            ]
            mock_post.return_value.status_code = 200
            
            server = LLMServer(
                model=GPT35_TURBO,
                server_url="http://test-server"
            )
            server.addMessage(Role.user, "Test streaming")
            
            # Test streaming response handling
            response = server.run(stream=True)
            assert "Part 1Part 2" in response

    @pytest.mark.llm
    async def test_llm_server_timeout(self):
        """Test LLM server timeout handling."""
        with patch('llm._llmserver.requests.post') as mock_post:
            mock_post.side_effect = TimeoutError("Request timed out")
            
            server = LLMServer(
                model=GPT35_TURBO,
                server_url="http://test-server"
            )
            server.addMessage(Role.user, "Test timeout")
            
            with pytest.raises(Exception) as exc_info:
                server.run()
            assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.llm
    @pytest.mark.integration
    async def test_llm_server_concurrent_requests(self):
        """Test concurrent requests to LLM server."""
        with patch('llm._llmserver.requests.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "choices": [{"message": {"content": "Response"}}]
            }
            mock_post.return_value.status_code = 200
            
            server = LLMServer(
                model=GPT35_TURBO,
                server_url="http://test-server"
            )
            
            import asyncio
            async def make_request(prompt):
                server.addMessage(Role.user, prompt)
                return server.run()
            
            # Make concurrent requests
            prompts = [f"Prompt {i}" for i in range(5)]
            tasks = [make_request(prompt) for prompt in prompts]
            responses = await asyncio.gather(*tasks)
            
            assert len(responses) == len(prompts)
            assert mock_post.call_count == len(prompts) 