from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from core.ai_service import AIService
from memory.memory_manager import MemoryManager

class NPCAgent(BaseAgent):
    def __init__(
        self,
        npc_id: str,
        name: str,
        personality: str,
        background: str,
        goals: List[str],
        ai_service: AIService,
        memory_manager: MemoryManager
    ):
        system_prompt = f"""你是{name}，一个游戏中的NPC角色。

你的性格：{personality}

你的背景：{background}

你的目标：{', '.join(goals)}

你的职责：
1. 根据你的性格和背景与玩家互动
2. 对玩家的行为做出符合你人设的反应
3. 追求你的目标，但保持角色的真实性
4. 记住与玩家的互动历史
5. 根据与玩家的关系调整你的态度

互动原则：
- 保持角色的一致性
- 对玩家的善意或恶意做出相应反应
- 不要脱离角色设定
- 可以有自己的秘密和动机
- 与玩家的关系会影响你的行为"""
        
        super().__init__(name, ai_service, memory_manager, system_prompt)
        self.npc_id = npc_id
        self.personality = personality
        self.background = background
        self.goals = goals
        self.relationship_score = 0
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        player_input = input_data.get("player_input", "")
        context = input_data.get("context", "")
        conversation_history = input_data.get("conversation_history", [])
        
        thought = await self.think(player_input, context)
        
        response = await self._generate_response(thought, player_input, context)
        
        relationship_change = await self._evaluate_relationship_change(player_input, response)
        self.relationship_score += relationship_change
        self.relationship_score = max(-100, min(100, self.relationship_score))
        
        self.memory_manager.update_npc_relationship(
            self.npc_id,
            "player",
            relationship_change
        )
        
        self.update_conversation("assistant", response)
        
        importance = await self._evaluate_conversation_importance(player_input, response)
        
        if importance >= 5:
            self.memory_manager.add_long_term(
                content=f"与{self.name}的对话：玩家说'{player_input}'，{self.name}回应'{response}'",
                memory_type="dialogue",
                importance=importance,
                participants=["player", self.npc_id],
                context=context
            )
        
        return {
            "response": response,
            "thought": thought,
            "relationship_change": relationship_change,
            "current_relationship": self.relationship_score,
            "importance": importance
        }
    
    async def think(self, player_input: str, context: str) -> str:
        relationship_info = self.memory_manager.get_npc_relationship(self.npc_id)
        relationship_desc = f"当前关系值：{self.relationship_score}"
        
        if relationship_info:
            relationship_desc += f"（{self._describe_relationship(self.relationship_score)}）"
        
        prompt = f"""玩家说：{player_input}

当前情境：
{context}

{relationship_desc}

请分析玩家的意图，并思考你应该如何回应。考虑你的性格、目标和当前关系。"""
        
        response = await self.ai_service.generate_response(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.conversation_history[-5:]
        )
        
        return response
    
    async def _generate_response(
        self,
        thought: str,
        player_input: str,
        context: str
    ) -> str:
        prompt = f"""基于你的思考：{thought}

玩家说：{player_input}

当前情境：
{context}

请生成你的回应（50-150字）。

要求：
- 符合你的性格和背景
- 考虑当前关系
- 可以包含情感表达
- 用中文输出"""
        
        response = await self.ai_service.generate_response(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.conversation_history[-5:]
        )
        
        return response
    
    async def _evaluate_relationship_change(
        self,
        player_input: str,
        npc_response: str
    ) -> float:
        prompt = f"""评估以下对话对NPC-玩家关系的影响（-10到+10）：

玩家说：{player_input}
NPC回应：{npc_response}

评估标准：
- 负值（-10到-1）：关系恶化，如冒犯、攻击、背叛
- 0：关系无变化，如日常对话
- 正值（1到+10）：关系改善，如帮助、赞美、合作

请只返回数字。"""
        
        response = await self.ai_service.generate_response(
            system_prompt="你是一个关系评估助手，只返回数字。",
            user_message=prompt
        )
        
        try:
            return float(response.strip())
        except:
            return 0.0
    
    async def _evaluate_conversation_importance(
        self,
        player_input: str,
        npc_response: str
    ) -> float:
        prompt = f"""评估以下对话的重要性（0-10分）：

玩家说：{player_input}
NPC回应：{npc_response}

评估标准：
- 0-3分：日常闲聊
- 4-6分：有意义的交流
- 7-8分：重要信息交换
- 9-10分：关键对话，影响剧情

请只返回数字。"""
        
        response = await self.ai_service.generate_response(
            system_prompt="你是一个重要性评估助手，只返回数字。",
            user_message=prompt
        )
        
        try:
            return float(response.strip())
        except:
            return 3.0
    
    def _describe_relationship(self, score: float) -> str:
        if score >= 80:
            return "亲密好友"
        elif score >= 60:
            return "友好"
        elif score >= 40:
            return "友善"
        elif score >= 20:
            return "中立偏善"
        elif score >= -20:
            return "中立"
        elif score >= -40:
            return "中立偏恶"
        elif score >= -60:
            return "敌对"
        elif score >= -80:
            return "仇恨"
        else:
            return "死敌"
    
    async def generate_dialogue_options(
        self,
        context: str,
        num_options: int = 4
    ) -> List[str]:
        prompt = f"""当前情境：
{context}

请生成{num_options}个玩家可以选择的对话选项，每个选项20-40字。

要求：
- 选项要多样化（友好、敌对、询问、交易等）
- 符合当前情境
- 用中文输出
- 每个选项单独一行"""
        
        response = await self.ai_service.generate_response(
            system_prompt="你是对话选项生成助手。",
            user_message=prompt
        )
        
        options = [line.strip() for line in response.split('\n') if line.strip()]
        return options[:num_options]
    
    async def autonomous_action(self, context: str) -> Dict[str, Any]:
        prompt = f"""当前情境：
{context}

你的目标：{', '.join(self.goals)}

请思考并决定你接下来要做什么自主行动（如移动、与其他NPC互动、准备某事等）。

请以以下格式回复：
思考：[你的思考过程]
行动：[你的行动描述]"""
        
        response = await self.ai_service.generate_response(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        
        lines = response.split('\n')
        thought = ""
        action = ""
        
        for line in lines:
            if line.startswith("思考："):
                thought = line[3:].strip()
            elif line.startswith("行动："):
                action = line[3:].strip()
        
        return {
            "thought": thought,
            "action": action
        }