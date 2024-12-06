import os, sys
from typing import Optional, Callable, Dict, Any, List, Tuple
from rich.console import Console
from rich.markdown import Markdown
import subprocess
import re
import io
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache, cached_property
import logging
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass, field
from llm.base import LLM, Role
from llm._llmserver import LLMServer, GPT35_TURBO
from opentelemetry import trace, metrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('codebrew.log', maxBytes=1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

console = Console()

@dataclass
class ExecutionResult:
    output: str = ""
    error: str = ""
    return_code: int = 0
    execution_time: float = 0.0

@dataclass
class CodeBrewConfig:
    max_retries: int = 3
    keep_history: bool = True
    verbose: bool = False
    timeout: float = 30.0
    max_output_length: int = 10000
    cache_size: int = 100
    globals: Dict[str, Any] = field(default_factory=dict)

class CodeBrew:
    def __init__(
            self,
            llm: LLM,
            config: Optional[CodeBrewConfig] = None,
            input_func: Callable = input,
            print_func: Callable = print
            ) -> None:
        """Initialize CodeBrew with improved configuration and error handling."""
        self.config = config or CodeBrewConfig()
        self.llm = llm
        self.input = input_func
        self.print = print_func
        self.temp_buffer = io.StringIO()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._install_required_packages()
        self.result_cache = {}
        # Initialize monitoring
        self.tracer = trace.get_tracer(__name__)
        self.meter = metrics.get_meter(__name__)
        
        # Set up metrics
        self.execution_time = self.meter.create_histogram(
            name="codebrew_execution_time",
            description="Time taken to execute commands"
        )

    def _install_required_packages(self) -> None:
        """Install required packages with error handling and logging."""
        required_packages = ['rich', 'python-json-logger']
        try:
            self.pip_install(*required_packages)
            logger.info(f"Successfully installed packages: {', '.join(required_packages)}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install packages: {e}")
            raise RuntimeError(f"Package installation failed: {e}")

    @lru_cache(maxsize=100)
    def filter_code(self, txt: str) -> Optional[str]:
        """Extract Python code from markdown with caching."""
        pattern = r"```python(.*?)```"
        matches = re.findall(pattern, txt, re.DOTALL)
        return matches[0].strip() if matches else None

    def pip_install(self, *packages: str) -> subprocess.CompletedProcess:
        """Install Python packages with improved error handling."""
        cmd = [sys.executable, "-m", "pip", "install", *packages]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Package installation failed: {e.stderr}")
            raise

    def fake_print(self, *args, **kwargs) -> None:
        """Capture print output with buffer management."""
        if len(self.temp_buffer.getvalue()) > self.config.max_output_length:
            logger.warning("Output buffer exceeded maximum length")
            self.temp_buffer = io.StringIO()
        print(*args, **kwargs, file=self.temp_buffer)

    async def execute_script(self, script: str) -> ExecutionResult:
        """Execute Python script with timeout and resource management."""
        result = ExecutionResult()
        globals_copy = self.config.globals.copy()
        globals_copy['print'] = self.fake_print
        globals_copy['input'] = self.input

        try:
            start_time = asyncio.get_event_loop().time()
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    exec,
                    script,
                    globals_copy
                ),
                timeout=self.config.timeout
            )
            result.execution_time = asyncio.get_event_loop().time() - start_time
            result.output = self.temp_buffer.getvalue()
            self.temp_buffer = io.StringIO()

        except asyncio.TimeoutError:
            result.error = f"Execution timed out after {self.config.timeout} seconds"
            result.return_code = 124
            logger.warning(f"Script execution timed out: {script[:100]}...")

        except Exception as e:
            result.error = str(e)
            result.return_code = 1
            logger.error(f"Script execution failed: {e}")

        return result

    async def run(self, prompt: str) -> str:
        """Run CodeBrew with improved error handling and async execution."""
        self.config.globals['input'] = self.input
        message_history = self.llm.messages.copy() if self.config.keep_history else []
        self.llm.addMessage(Role.user, prompt)
        
        retries_left = self.config.max_retries
        while retries_left > 0:
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.llm.run
                )
                self.llm.addMessage(Role.assistant, response)

                if self.config.verbose:
                    console.print(Markdown(response))

                script = self.filter_code(response)
                if not script:
                    return response

                result = await self.execute_script(script)
                
                if result.output:
                    self.llm.addMessage(Role.user, f"LAST SCRIPT OUTPUT:\n{result.output}")
                    if result.output.strip().endswith("CONTINUE"):
                        continue
                    return result.output.strip()

                if result.error:
                    self.llm.addMessage(Role.user, f"Error: {result.error}")
                    if retries_left > 1:
                        logger.info(f"Retrying execution, {retries_left-1} attempts left")
                        retries_left -= 1
                        continue
                    return f"Failed after {self.config.max_retries} attempts: {result.error}"

                return response

            except KeyboardInterrupt:
                logger.info("Execution interrupted by user")
                break

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                retries_left -= 1
                if retries_left == 0:
                    return f"Fatal error: {str(e)}"

        if not self.config.keep_history:
            self.llm.messages = message_history

        return "Execution failed"

    def cleanup(self) -> None:
        """Clean up resources."""
        self.executor.shutdown(wait=True)
        self.temp_buffer.close()

    @cached_property
    def llm_client(self):
        """Lazy initialization of LLM client."""
        return self._create_llm_client()

async def main():
    """Async main function with improved error handling."""
    try:
        llm = LLMServer(
            model=GPT35_TURBO,
            server_url="http://localhost:8000"
        )
        config = CodeBrewConfig(verbose=True)
        codebrew = CodeBrew(llm=llm, config=config)

        while True:
            try:
                prompt = input("Enter your prompt (or 'exit' to quit): ")
                if prompt.lower() == 'exit':
                    break
                result = await codebrew.run(prompt)
                print(result)
            except KeyboardInterrupt:
                logger.info("User interrupted the program")
                break
            except Exception as e:
                logger.error(f"Error processing prompt: {e}")
                print(f"Error: {e}")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        codebrew.cleanup()

if __name__ == "__main__":
    asyncio.run(main())