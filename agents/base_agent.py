from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from core.ai_service import AIService
from memory.memory_manager import MemoryManager

class BaseAgent(ABC):
    def __init__(
        self,
        name: str,
        ai_service: AIService,
        memory_manager: MemoryManager,
        system_prompt: str
    ):
        self.name = name
        self.ai_service = ai_service
        self.memory_manager = memory_manager
        self.system_prompt = system_prompt
        self.conversation_history: List[Dict[str, str]] = []
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def think(self, context: str) -> str:
        prompt = f"{self.system_prompt}\n\n当前情境：\n{context}\n\n请分析当前情况并给出你的思考。"
        response = await self.ai_service.generate_response(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.conversation_history[-5:]
        )
        return response
    
    async def act(self, thought: str, context: str) -> Dict[str, Any]:
        prompt = f"基于你的思考：{thought}\n\n当前情境：{context}\n\n请决定你的行动。"
        response = await self.ai_service.generate_response(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.conversation_history[-5:]
        )
        return {"action": response}
    
    def update_conversation(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def get_memory_context(self) -> str:
        return self.memory_manager.get_context_for_ai()