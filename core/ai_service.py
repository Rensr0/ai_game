import aiohttp
import asyncio
import json
from typing import Dict, List, Any, Optional
from utils.config import config

class AIService:
    def __init__(self):
        api_config = config.get_api_config()
        self.base_url = api_config.get('base_url')
        self.api_key = api_config.get('api_key')
        self.model = api_config.get('model')
        self.timeout = api_config.get('timeout', 30)
        self.max_retries = api_config.get('max_retries', 3)
        
        ai_config = config.get_ai_config()
        self.temperature = ai_config.get('temperature', 0.7)
        self.max_tokens = ai_config.get('max_tokens', 2000)
        
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        temperature = temperature or self.temperature
        max_tokens = max_tokens or self.max_tokens
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        raise Exception(f"API Error {response.status}: {error_text}")
            except asyncio.TimeoutError:
                if attempt == self.max_retries - 1:
                    raise Exception(f"API timeout after {self.max_retries} attempts")
                await asyncio.sleep(1)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1)
    
    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": user_message})
        
        response = await self.chat_completion(messages, **kwargs)
        
        if "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]
        else:
            raise Exception("Invalid response format from API")
    
    async def generate_with_function_calling(
        self,
        system_prompt: str,
        user_message: str,
        functions: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": user_message})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get('temperature', self.temperature),
            "max_tokens": kwargs.get('max_tokens', self.max_tokens),
            "functions": functions,
            "function_call": "auto"
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        async with self.session.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as response:
            result = await response.json()
            return result
    
    async def close(self):
        if self.session:
            await self.session.close()

async def get_ai_service():
    return AIService()