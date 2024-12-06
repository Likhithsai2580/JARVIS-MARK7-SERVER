from typing import Dict, Any, Optional, List
import httpx
from datetime import datetime
import asyncio
import logging
from ..config import settings
from .prompts import SYSTEM_PROMPTS
from .skills import SkillRegistry

logger = logging.getLogger(__name__)

class ExecutionContext:
    """Maintains state and context during command execution"""
    def __init__(self):
        self.start_time = datetime.now()
        self.steps_executed = []
        self.resources_allocated = {}
        self.state_changes = []
        self.errors = []
        self.metrics = {
            "duration": 0,
            "memory_usage": 0,
            "api_calls": 0
        }

    def add_step(self, step: Dict[str, Any]):
        self.steps_executed.append(step)

    def add_error(self, error: Dict[str, Any]):
        self.errors.append(error)
        logger.error(f"Execution error: {error}")

    def update_metrics(self, metrics: Dict[str, Any]):
        self.metrics.update(metrics)

class Jarvis:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30)
        self.skill_registry = SkillRegistry()
        self.context = {}
        self.dns_client = DNSClient()
        self.execution_history = []
        
    async def process_command(self, command: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user commands using LLM for orchestration"""
        execution_context = ExecutionContext()
        
        try:
            # Validate and preprocess command
            validated_command = await self.validate_command(command)
            
            # First, use LLM to analyze the command and determine required skills
            analysis = await self.analyze_command(validated_command, context)
            execution_context.add_step({"type": "analysis", "result": analysis})
            
            # Validate required permissions and resources
            await self.validate_requirements(analysis)
            
            # If codebase operation is required, perform codebase analysis
            if analysis.get("codebase_context"):
                codebase_analysis = await self.analyze_codebase(analysis["codebase_context"])
                analysis["codebase_analysis"] = codebase_analysis
                execution_context.add_step({"type": "codebase_analysis", "result": codebase_analysis})
            
            # Get execution plan from LLM
            execution_plan = await self.get_execution_plan(analysis)
            execution_context.add_step({"type": "planning", "result": execution_plan})
            
            # Allocate required resources
            await self.allocate_resources(execution_plan, execution_context)
            
            # Execute each step in the plan
            results = []
            for step in execution_plan["steps"]:
                try:
                    # Validate step preconditions
                    await self.validate_step_preconditions(step, execution_context)
                    
                    # Execute step with monitoring
                    step_result = await self.execute_step_with_monitoring(step, context, execution_context)
                    results.append(step_result)
                    
                    # Validate step postconditions
                    await self.validate_step_postconditions(step, step_result, execution_context)
                    
                except Exception as e:
                    error = {"step": step, "error": str(e)}
                    execution_context.add_error(error)
                    if not await self.handle_step_error(error, execution_context):
                        raise
            
            # Use LLM to synthesize final response
            final_response = await self.synthesize_response(results, command, execution_context)
            
            # Cleanup resources
            await self.cleanup_resources(execution_context)
            
            # Store execution history
            self.execution_history.append({
                "command": command,
                "context": execution_context,
                "result": final_response
            })
            
            return final_response
            
        except Exception as e:
            error = f"Command processing failed: {str(e)}"
            execution_context.add_error({"error": error})
            await self.cleanup_resources(execution_context)
            return {"error": error, "context": execution_context}

    async def validate_command(self, command: str) -> str:
        """Validate and preprocess the command"""
        messages = [
            {"role": "system", "content": "Validate and preprocess the command for security and correctness."},
            {"role": "user", "content": command}
        ]
        response = await self.get_llm_response(messages)
        return response.get("validated_command", command)

    async def validate_requirements(self, analysis: Dict[str, Any]):
        """Validate required permissions and resources"""
        for permission in analysis.get("dependencies", {}).get("permissions", []):
            if not await self.check_permission(permission):
                raise PermissionError(f"Missing required permission: {permission}")

    async def allocate_resources(self, plan: Dict[str, Any], context: ExecutionContext):
        """Allocate required resources for execution"""
        resources = plan.get("execution_metadata", {}).get("resource_requirements", {})
        for resource, requirement in resources.items():
            allocation = await self.allocate_resource(resource, requirement)
            context.resources_allocated[resource] = allocation

    async def cleanup_resources(self, context: ExecutionContext):
        """Clean up allocated resources"""
        for resource, allocation in context.resources_allocated.items():
            await self.deallocate_resource(resource, allocation)

    async def execute_step_with_monitoring(self, step: Dict[str, Any], context: Optional[Dict[str, Any]], execution_context: ExecutionContext) -> Dict[str, Any]:
        """Execute a step with monitoring and metrics collection"""
        start_time = datetime.now()
        
        try:
            # Start monitoring
            monitor_task = asyncio.create_task(self.monitor_step_execution(step, execution_context))
            
            # Execute step
            result = await self.execute_step(step, context)
            
            # Update metrics
            duration = (datetime.now() - start_time).total_seconds()
            execution_context.update_metrics({
                "step_duration": duration,
                "step_success": True
            })
            
            # Stop monitoring
            await monitor_task
            
            return result
            
        except Exception as e:
            execution_context.update_metrics({
                "step_duration": (datetime.now() - start_time).total_seconds(),
                "step_success": False
            })
            raise

    async def monitor_step_execution(self, step: Dict[str, Any], context: ExecutionContext):
        """Monitor step execution for health and performance"""
        while True:
            try:
                # Collect metrics
                metrics = await self.collect_step_metrics(step)
                context.update_metrics(metrics)
                
                # Check health
                health = await self.check_step_health(step)
                if not health["healthy"]:
                    context.add_error({"type": "health_check", "details": health})
                
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break

    async def handle_step_error(self, error: Dict[str, Any], context: ExecutionContext) -> bool:
        """Handle step execution errors with LLM guidance"""
        messages = [
            {"role": "system", "content": "Analyze error and provide recovery strategy."},
            {"role": "user", "content": str(error)}
        ]
        
        recovery_plan = await self.get_llm_response(messages)
        
        if recovery_plan.get("can_recover"):
            await self.execute_recovery_plan(recovery_plan, context)
            return True
        return False

    async def analyze_command(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Use LLM to analyze command and determine required skills"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPTS["command_analysis"]},
            {"role": "user", "content": f"Command: {command}\nContext: {context}"}
        ]
        
        llm_response = await self.get_llm_response(messages)
        return llm_response

    async def analyze_codebase(self, codebase_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze relevant parts of the codebase using LLM"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPTS["codebase_analysis"]},
            {"role": "user", "content": f"Context: {codebase_context}"}
        ]
        
        llm_response = await self.get_llm_response(messages)
        return llm_response

    async def get_execution_plan(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to create detailed execution plan"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPTS["execution_planning"]},
            {"role": "user", "content": f"Analysis: {analysis}"}
        ]
        
        llm_response = await self.get_llm_response(messages)
        return llm_response

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a single step from the execution plan"""
        skill_name = step["skill"]
        params = step["parameters"]
        
        # Handle code-specific operations
        if step.get("code_operation"):
            return await self.execute_code_operation(step["code_operation"], params, context)
        
        if skill := self.skill_registry.get_skill(skill_name):
            # Get specialized prompt for this skill
            skill_prompt = SYSTEM_PROMPTS.get(f"skill_{skill_name}", "")
            
            # Add skill-specific LLM guidance
            messages = [
                {"role": "system", "content": skill_prompt},
                {"role": "user", "content": f"Step: {step}\nContext: {context}"}
            ]
            
            # Get LLM guidance for skill execution
            guidance = await self.get_llm_response(messages)
            
            # Execute skill with LLM guidance
            return await skill.execute(params, guidance, context)
        else:
            return {"error": f"Skill {skill_name} not found"}

    async def execute_code_operation(self, operation: Dict[str, Any], params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute code-specific operations with LLM guidance"""
        operation_type = operation["type"]
        
        if operation_type == "generate":
            messages = [
                {"role": "system", "content": SYSTEM_PROMPTS["code_generation"]},
                {"role": "user", "content": f"Parameters: {params}\nContext: {context}"}
            ]
        elif operation_type == "modify":
            messages = [
                {"role": "system", "content": SYSTEM_PROMPTS["code_modification"]},
                {"role": "user", "content": f"Parameters: {params}\nContext: {context}"}
            ]
        else:
            return {"error": f"Unknown code operation type: {operation_type}"}
            
        guidance = await self.get_llm_response(messages)
        return await self.apply_code_changes(guidance, params)

    async def apply_code_changes(self, guidance: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply code changes based on LLM guidance"""
        try:
            # Create backup if required
            if guidance.get("backup_required"):
                await self.create_backup(params.get("files", []))
            
            # Validate changes
            validation_result = await self.validate_code_changes(guidance.get("changes", []))
            if not validation_result["valid"]:
                return {"error": "Code changes validation failed", "details": validation_result}
            
            # Apply changes
            applied_changes = []
            for change in guidance.get("changes", []):
                result = await self.apply_single_change(change)
                applied_changes.append(result)
                
            # Verify changes
            verification = await self.verify_code_changes(applied_changes)
            if not verification["success"]:
                await self.rollback_changes(applied_changes)
                return {"error": "Changes verification failed", "details": verification}
                
            return {
                "status": "success",
                "changes": applied_changes,
                "verification": verification
            }
        except Exception as e:
            return {"error": f"Failed to apply code changes: {str(e)}"}

    async def synthesize_response(self, results: List[Dict[str, Any]], original_command: str, execution_context: ExecutionContext) -> Dict[str, Any]:
        """Use LLM to synthesize final response from all results"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPTS["response_synthesis"]},
            {"role": "user", "content": f"""
                Original Command: {original_command}
                Results: {results}
                Execution Context: {execution_context.__dict__}
            """}
        ]
        
        return await self.get_llm_response(messages)

    async def get_llm_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Helper method to get LLM responses with retry and fallback"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                llm_service = await self.dns_client.get_service("llm")
                response = await self.client.post(
                    f"{llm_service.url}/chat/completions",
                    json={"messages": messages},
                    timeout=30.0
                )
                return response.json()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

class DNSClient:
    def __init__(self, dns_url: str = "http://localhost:9000"):
        self.dns_url = dns_url
        self.client = httpx.AsyncClient()
        self.cache = {}
        
    async def get_service(self, service_name: str) -> Dict[str, Any]:
        """Get service details from DNS server with caching"""
        if service_name in self.cache:
            if (datetime.now() - self.cache[service_name]["timestamp"]).seconds < 300:
                return self.cache[service_name]["data"]
                
        response = await self.client.get(f"{self.dns_url}/status/{service_name}")
        service_data = response.json()
        
        self.cache[service_name] = {
            "data": service_data,
            "timestamp": datetime.now()
        }
        
        return service_data 