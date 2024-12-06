import pytest
import asyncio
from unittest.mock import Mock, patch
from main import CodeBrew, CodeBrewConfig
from llm.base import Role

pytestmark = pytest.mark.asyncio

class TestCodeBrew:
    """Test suite for CodeBrew class."""

    @pytest.mark.unit
    async def test_initialization(self, mock_llm, codebrew_config):
        """Test CodeBrew initialization."""
        brew = CodeBrew(llm=mock_llm, config=codebrew_config)
        assert brew.llm == mock_llm
        assert brew.config == codebrew_config
        assert brew.temp_buffer is not None
        brew.cleanup()

    @pytest.mark.unit
    async def test_filter_code(self, codebrew):
        """Test code extraction from markdown."""
        markdown = """Here's a Python function:
        ```python
        def test():
            print("Hello")
        ```
        """
        code = codebrew.filter_code(markdown)
        assert code is not None
        assert "def test():" in code
        assert "print(\"Hello\")" in code

    @pytest.mark.unit
    async def test_filter_code_no_code(self, codebrew):
        """Test code extraction with no code block."""
        markdown = "Just some text without code"
        code = codebrew.filter_code(markdown)
        assert code is None

    @pytest.mark.unit
    async def test_fake_print(self, codebrew):
        """Test print capture functionality."""
        test_text = "Test output"
        codebrew.fake_print(test_text)
        assert test_text in codebrew.temp_buffer.getvalue()

    @pytest.mark.unit
    async def test_fake_print_buffer_limit(self, codebrew):
        """Test print buffer limit handling."""
        long_text = "x" * (codebrew.config.max_output_length + 100)
        codebrew.fake_print(long_text)
        assert len(codebrew.temp_buffer.getvalue()) <= codebrew.config.max_output_length

    @pytest.mark.integration
    async def test_execute_script_success(self, codebrew):
        """Test successful script execution."""
        script = "print('Hello, World!')"
        result = await codebrew.execute_script(script)
        assert result.output.strip() == "Hello, World!"
        assert result.error == ""
        assert result.return_code == 0
        assert result.execution_time >= 0

    @pytest.mark.integration
    async def test_execute_script_error(self, codebrew):
        """Test script execution with error."""
        script = "print(undefined_variable)"
        result = await codebrew.execute_script(script)
        assert result.error != ""
        assert result.return_code != 0

    @pytest.mark.integration
    async def test_execute_script_timeout(self, codebrew):
        """Test script execution timeout."""
        script = "import time; time.sleep(10)"
        result = await codebrew.execute_script(script)
        assert "timeout" in result.error.lower()
        assert result.return_code == 124

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_run_with_code_generation(self, codebrew, test_prompt):
        """Test complete code generation and execution flow."""
        result = await codebrew.run(test_prompt)
        assert "Hello, World!" in result

    @pytest.mark.unit
    async def test_run_with_no_code(self, codebrew):
        """Test run with response containing no code."""
        result = await codebrew.run("Hello")
        assert "Hello" in result
        assert "World" not in result

    @pytest.mark.integration
    async def test_run_with_retries(self, codebrew):
        """Test retry mechanism."""
        with patch.object(codebrew.llm, 'run', side_effect=[
            "```python\nraise Exception('Test error')\n```",
            "```python\nprint('Success after retry')\n```"
        ]):
            result = await codebrew.run("Test retry")
            assert "Success after retry" in result

    @pytest.mark.integration
    async def test_run_with_continue(self, codebrew):
        """Test continuation mechanism."""
        with patch.object(codebrew.llm, 'run', side_effect=[
            "```python\nprint('Part 1 CONTINUE')\n```",
            "```python\nprint('Part 2')\n```"
        ]):
            result = await codebrew.run("Test continue")
            assert "Part 2" in result

    @pytest.mark.unit
    async def test_cleanup(self, codebrew):
        """Test resource cleanup."""
        codebrew.cleanup()
        assert codebrew.executor._shutdown
        with pytest.raises(ValueError):
            codebrew.temp_buffer.write("test")

    @pytest.mark.integration
    async def test_message_history(self, codebrew, test_prompt):
        """Test message history management."""
        await codebrew.run(test_prompt)
        assert len(codebrew.llm.messages) > 0
        assert any(msg.role == Role.user for msg in codebrew.llm.messages)
        assert any(msg.role == Role.assistant for msg in codebrew.llm.messages)

    @pytest.mark.integration
    async def test_concurrent_execution(self, codebrew):
        """Test concurrent script execution."""
        scripts = [
            "print('Test 1')",
            "print('Test 2')",
            "print('Test 3')"
        ]
        tasks = [codebrew.execute_script(script) for script in scripts]
        results = await asyncio.gather(*tasks)
        assert all(result.return_code == 0 for result in results)
        assert len(results) == 3

    @pytest.mark.unit
    async def test_input_handling(self, codebrew):
        """Test input handling in scripts."""
        mock_input = Mock(return_value="test input")
        codebrew.input = mock_input
        script = "result = input('prompt: ')\nprint(f'Got: {result}')"
        result = await codebrew.execute_script(script)
        assert "Got: test input" in result.output
        mock_input.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_memory_usage(self, codebrew):
        """Test memory usage during execution."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Run memory-intensive operation
        large_data = "x" * 1000000
        script = f"data = '{large_data}'\nprint(len(data))"
        await codebrew.execute_script(script)
        
        # Check memory was cleaned up
        final_memory = process.memory_info().rss
        memory_diff = final_memory - initial_memory
        assert memory_diff < 5 * 1024 * 1024  # Less than 5MB difference 