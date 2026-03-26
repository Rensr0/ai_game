from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from core.ai_service import AIService
from memory.memory_manager import MemoryManager

class QuestAgent(BaseAgent):
    def __init__(
        self,
        ai_service: AIService,
        memory_manager: MemoryManager
    ):
        system_prompt = """你是任务管理员（Quest Manager），负责管理游戏中的任务系统。

你的职责：
1. 生成有趣的任务
2. 追踪任务进度
3. 评估任务完成情况
4. 提供任务奖励
5. 确保任务与游戏世界的一致性

任务类型：
- 主线任务：推动主要剧情
- 支线任务：额外的冒险和挑战
- 日常任务：可重复的小任务
- 突发任务：随机出现的紧急任务

任务设计原则：
- 任务目标要清晰
- 奖励要与难度匹配
- 任务要符合世界观
- 提供多种完成方式
- 任务之间可以有关联"""
        
        super().__init__("QuestManager", ai_service, memory_manager, system_prompt)
        self.active_quests: List[Dict[str, Any]] = []
        self.completed_quests: List[Dict[str, Any]] = []
        self.quest_counter = 0
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action", "")
        context = input_data.get("context", "")
        
        if action == "generate":
            return await self.generate_quest(context)
        elif action == "update":
            quest_id = input_data.get("quest_id")
            progress = input_data.get("progress")
            return await self.update_quest(quest_id, progress, context)
        elif action == "complete":
            quest_id = input_data.get("quest_id")
            return await self.complete_quest(quest_id, context)
        elif action == "check":
            return await self.check_quests()
        else:
            return {"error": "Unknown action"}
    
    async def generate_quest(
        self,
        context: str,
        quest_type: str = "side"
    ) -> Dict[str, Any]:
        self.quest_counter += 1
        quest_id = f"quest_{self.quest_counter}"
        
        type_descriptions = {
            "main": "主线任务，推动主要剧情发展",
            "side": "支线任务，提供额外的冒险和挑战",
            "daily": "日常任务，可重复的小任务",
            "emergency": "突发任务，紧急情况需要处理"
        }
        
        prompt = f"""请生成一个{type_descriptions.get(quest_type, '支线任务')}。

当前情境：
{context}

请以JSON格式返回任务信息，包含以下字段：
{{
    "title": "任务标题",
    "description": "任务详细描述（100-150字）",
    "objectives": ["目标1", "目标2", ...],
    "rewards": ["奖励1", "奖励2", ...],
    "difficulty": 1-10,
    "location": "任务地点",
    "npc_involved": ["相关NPC1", "相关NPC2"]
}}"""
        
        response = await self.ai_service.generate_response(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        
        try:
            import json
            quest_data = json.loads(response)
            quest_data["id"] = quest_id
            quest_data["type"] = quest_type
            quest_data["status"] = "active"
            quest_data["progress"] = 0
            quest_data["created_at"] = context
            
            self.active_quests.append(quest_data)
            
            self.memory_manager.add_long_term(
                content=f"接受任务：{quest_data['title']}",
                memory_type="quest",
                importance=7,
                participants=["player"],
                context=context
            )
            
            return {"quest": quest_data}
        except json.JSONDecodeError:
            return {"error": "Failed to parse quest data"}
    
    async def update_quest(
        self,
        quest_id: str,
        progress: float,
        context: str
    ) -> Dict[str, Any]:
        for quest in self.active_quests:
            if quest["id"] == quest_id:
                old_progress = quest["progress"]
                quest["progress"] = min(100, max(0, progress))
                
                if quest["progress"] > old_progress:
                    self.memory_manager.add_short_term(
                        "quest",
                        f"任务'{quest['title']}'进度更新：{old_progress}% -> {quest['progress']}%"
                    )
                
                if quest["progress"] >= 100:
                    return await self.complete_quest(quest_id, context)
                
                return {
                    "quest_id": quest_id,
                    "progress": quest["progress"],
                    "status": "updated"
                }
        
        return {"error": "Quest not found"}
    
    async def complete_quest(
        self,
        quest_id: str,
        context: str
    ) -> Dict[str, Any]:
        for i, quest in enumerate(self.active_quests):
            if quest["id"] == quest_id:
                completed_quest = self.active_quests.pop(i)
                completed_quest["status"] = "completed"
                completed_quest["completed_at"] = context
                self.completed_quests.append(completed_quest)
                
                self.memory_manager.add_long_term(
                    content=f"完成任务：{completed_quest['title']}",
                    memory_type="quest",
                    importance=8,
                    participants=["player"],
                    context=context
                )
                
                return {
                    "quest": completed_quest,
                    "rewards": completed_quest.get("rewards", []),
                    "message": f"恭喜完成任务：{completed_quest['title']}！"
                }
        
        return {"error": "Quest not found"}
    
    async def check_quests(self) -> Dict[str, Any]:
        return {
            "active": self.active_quests,
            "completed": self.completed_quests,
            "summary": {
                "active_count": len(self.active_quests),
                "completed_count": len(self.completed_quests)
            }
        }
    
    async def generate_dynamic_quest(
        self,
        player_action: str,
        current_context: str
    ) -> Dict[str, Any]:
        prompt = f"""玩家执行了以下行为：{player_action}

当前情境：
{current_context}

请判断这个行为是否可以触发一个新的任务。

如果可以，请生成一个相关的任务（JSON格式）：
{{
    "title": "任务标题",
    "description": "任务描述",
    "objectives": ["目标1", "目标2"],
    "rewards": ["奖励1"],
    "difficulty": 1-10,
    "triggered_by": "触发行为"
}}

如果不应该触发任务，请回复："NO_TASK" """
        
        response = await self.ai_service.generate_response(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        
        if "NO_TASK" in response:
            return {"no_quest": True}
        
        try:
            import json
            quest_data = json.loads(response)
            self.quest_counter += 1
            quest_data["id"] = f"quest_{self.quest_counter}"
            quest_data["type"] = "dynamic"
            quest_data["status"] = "active"
            quest_data["progress"] = 0
            
            self.active_quests.append(quest_data)
            
            return {"quest": quest_data}
        except json.JSONDecodeError:
            return {"error": "Failed to parse dynamic quest"}