from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from core.ai_service import AIService
from memory.memory_manager import MemoryManager

class GameMasterAgent(BaseAgent):
    def __init__(
        self,
        ai_service: AIService,
        memory_manager: MemoryManager
    ):
        system_prompt = """你是游戏管理员（Game Master），负责统筹整个AI冒险游戏。

你的职责：
1. 协调各个NPC Agent和Narrator Agent
2. 维护游戏世界的整体状态
3. 处理玩家的全局行为
4. 确保游戏逻辑的一致性
5. 评估玩家行为的重要性和影响

你需要：
- 保持客观和中立
- 确保游戏体验的连贯性
- 平衡游戏难度和乐趣
- 记录重要的游戏事件
"""
        super().__init__("GameMaster", ai_service, memory_manager, system_prompt)
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        player_action = input_data.get("player_action", "")
        current_state = input_data.get("current_state", {})
        
        context = self._build_context(current_state)
        thought = await self.think(context)
        
        action_result = await self.act(thought, context)
        
        importance = await self._evaluate_importance(player_action, context)
        
        if importance >= 5:
            self.memory_manager.add_long_term(
                content=f"玩家行为：{player_action}",
                memory_type="player_action",
                importance=importance,
                participants=["player"],
                context=context
            )
        
        self.update_conversation("assistant", thought)
        
        return {
            "thought": thought,
            "action": action_result["action"],
            "importance": importance,
            "state_update": await self._determine_state_updates(action_result, current_state)
        }
    
    def _build_context(self, current_state: Dict[str, Any]) -> str:
        context_parts = []
        
        if "location" in current_state:
            context_parts.append(f"当前位置：{current_state['location']}")
        
        if "active_quests" in current_state:
            context_parts.append(f"进行中的任务：{', '.join(current_state['active_quests'])}")
        
        if "nearby_npcs" in current_state:
            context_parts.append(f"附近的NPC：{', '.join(current_state['nearby_npcs'])}")
        
        memory_context = self.get_memory_context()
        if memory_context:
            context_parts.append(f"最近的互动：\n{memory_context}")
        
        return "\n".join(context_parts)
    
    async def _evaluate_importance(self, player_action: str, context: str) -> float:
        prompt = f"""请评估以下玩家行为的重要性（0-10分）：

玩家行为：{player_action}

当前情境：
{context}

评估标准：
- 0-3分：日常行为，如移动、观察等
- 4-6分：有意义的互动，如对话、简单任务
- 7-8分：重要决策，如选择阵营、重要物品
- 9-10分：关键事件，如战斗、重大剧情转折

请只返回数字分数。"""
        
        response = await self.ai_service.generate_response(
            system_prompt="你是一个评估助手，只返回数字分数。",
            user_message=prompt
        )
        
        try:
            return float(response.strip())
        except:
            return 5.0
    
    async def _determine_state_updates(
        self,
        action_result: Dict[str, Any],
        current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        updates = {}
        
        action = action_result.get("action", "").lower()
        
        if "移动" in action or "前往" in action:
            updates["location_changed"] = True
        
        if "战斗" in action or "攻击" in action:
            updates["combat_started"] = True
        
        if "任务" in action or "接受" in action:
            updates["quest_updated"] = True
        
        return updates
    
    async def coordinate_agents(
        self,
        narrator_output: str,
        npc_outputs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        prompt = f"""作为游戏管理员，请协调以下输出：

旁白：{narrator_output}

NPC反应：
{chr(10).join([f"{npc['name']}: {npc['response']}" for npc in npc_outputs])}

请整合这些输出，确保它们协调一致，并给出最终的游戏响应。"""
        
        response = await self.ai_service.generate_response(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        
        return {"coordinated_response": response}