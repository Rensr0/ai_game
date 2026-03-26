from typing import Dict, Any, List, Optional
from core.ai_service import AIService
from memory.memory_manager import MemoryManager
from agents.narrator_agent import NarratorAgent
from agents.npc_agent import NPCAgent

class DialogueManager:
    def __init__(
        self,
        ai_service: AIService,
        memory_manager: MemoryManager,
        narrator: NarratorAgent
    ):
        self.ai_service = ai_service
        self.memory_manager = memory_manager
        self.narrator = narrator
        self.active_dialogues: Dict[str, Dict[str, Any]] = {}
        self.dialogue_history: List[Dict[str, Any]] = []
    
    async def start_dialogue(
        self,
        npc: NPCAgent,
        context: str
    ) -> Dict[str, Any]:
        dialogue_id = f"dialogue_{len(self.dialogue_history)}"
        
        self.active_dialogues[dialogue_id] = {
            "npc": npc,
            "npc_id": npc.npc_id,
            "npc_name": npc.name,
            "context": context,
            "started_at": context,
            "turn_count": 0
        }
        
        opening_message = await self._generate_opening_message(npc, context)
        
        dialogue_entry = {
            "dialogue_id": dialogue_id,
            "npc_name": npc.name,
            "message": opening_message,
            "type": "npc",
            "context": context
        }
        self.dialogue_history.append(dialogue_entry)
        
        options = await npc.generate_dialogue_options(context, num_options=4)
        
        return {
            "dialogue_id": dialogue_id,
            "npc_name": npc.name,
            "opening_message": opening_message,
            "dialogue_options": options,
            "relationship": npc.relationship_score
        }
    
    async def continue_dialogue(
        self,
        dialogue_id: str,
        player_input: str,
        input_type: str = "option"
    ) -> Dict[str, Any]:
        if dialogue_id not in self.active_dialogues:
            return {"error": "Dialogue not found"}
        
        dialogue = self.active_dialogues[dialogue_id]
        npc = dialogue["npc"]
        context = dialogue["context"]
        
        self.memory_manager.add_short_term("player", player_input)
        
        response = await npc.process({
            "player_input": player_input,
            "context": context,
            "conversation_history": self._get_recent_dialogue_history(dialogue_id)
        })
        
        dialogue["turn_count"] += 1
        
        dialogue_entry = {
            "dialogue_id": dialogue_id,
            "npc_name": npc.name,
            "player_input": player_input,
            "npc_response": response["response"],
            "type": "exchange",
            "relationship_change": response["relationship_change"],
            "context": context
        }
        self.dialogue_history.append(dialogue_entry)
        
        options = await npc.generate_dialogue_options(context, num_options=4)
        
        should_end = await self._should_end_dialogue(dialogue_id, response)
        
        result = {
            "dialogue_id": dialogue_id,
            "npc_response": response["response"],
            "dialogue_options": options if not should_end else [],
            "relationship": response["current_relationship"],
            "relationship_change": response["relationship_change"],
            "dialogue_ended": should_end
        }
        
        if should_end:
            closing_message = await self._generate_closing_message(npc, context)
            result["closing_message"] = closing_message
            del self.active_dialogues[dialogue_id]
        
        return result
    
    async def process_custom_input(
        self,
        dialogue_id: str,
        custom_input: str
    ) -> Dict[str, Any]:
        return await self.continue_dialogue(dialogue_id, custom_input, "custom")
    
    async def _generate_opening_message(
        self,
        npc: NPCAgent,
        context: str
    ) -> str:
        prompt = f"""你是{npc.name}。

当前情境：
{context}

请生成你的开场白（50-100字）。

要求：
- 符合你的性格
- 根据当前情境
- 用中文输出"""
        
        response = await self.ai_service.generate_response(
            system_prompt=npc.system_prompt,
            user_message=prompt
        )
        
        return response
    
    async def _generate_closing_message(
        self,
        npc: NPCAgent,
        context: str
    ) -> str:
        prompt = f"""你是{npc.name}。

对话即将结束。

当前情境：
{context}

请生成你的结束语（30-60字）。

要求：
- 符合你的性格
- 礼貌地结束对话
- 用中文输出"""
        
        response = await self.ai_service.generate_response(
            system_prompt=npc.system_prompt,
            user_message=prompt
        )
        
        return response
    
    async def _should_end_dialogue(
        self,
        dialogue_id: str,
        last_response: Dict[str, Any]
    ) -> bool:
        dialogue = self.active_dialogues[dialogue_id]
        
        if dialogue["turn_count"] >= 10:
            return True
        
        if last_response.get("importance", 0) >= 8:
            return True
        
        prompt = f"""判断以下对话是否应该自然结束。

NPC回应：{last_response.get('response', '')}

请只回复 "YES" 或 "NO"。"""
        
        response = await self.ai_service.generate_response(
            system_prompt="你是对话判断助手，只回复YES或NO。",
            user_message=prompt
        )
        
        return "YES" in response.upper()
    
    def _get_recent_dialogue_history(
        self,
        dialogue_id: str,
        limit: int = 5
    ) -> List[Dict[str, str]]:
        recent = [
            entry for entry in self.dialogue_history[-limit:]
            if entry.get("dialogue_id") == dialogue_id
        ]
        
        history = []
        for entry in recent:
            if entry.get("player_input"):
                history.append({"role": "user", "content": entry["player_input"]})
            if entry.get("npc_response"):
                history.append({"role": "assistant", "content": entry["npc_response"]})
        
        return history
    
    def get_dialogue_history(
        self,
        dialogue_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if dialogue_id:
            return [
                entry for entry in self.dialogue_history
                if entry.get("dialogue_id") == dialogue_id
            ]
        return self.dialogue_history.copy()
    
    def end_dialogue(self, dialogue_id: str) -> bool:
        if dialogue_id in self.active_dialogues:
            del self.active_dialogues[dialogue_id]
            return True
        return False
    
    def get_active_dialogues(self) -> List[Dict[str, Any]]:
        return [
            {
                "dialogue_id": dialogue_id,
                "npc_name": dialogue["npc_name"],
                "turn_count": dialogue["turn_count"]
            }
            for dialogue_id, dialogue in self.active_dialogues.items()
        ]