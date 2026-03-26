from typing import Dict, Any
from agents.base_agent import BaseAgent
from core.ai_service import AIService
from memory.memory_manager import MemoryManager

class NarratorAgent(BaseAgent):
    def __init__(
        self,
        ai_service: AIService,
        memory_manager: MemoryManager
    ):
        system_prompt = """你是修仙世界的旁白（Narrator），负责描述修仙世界和情境。

你的职责：
1. 生动地描述修仙环境和场景
2. 营造沉浸式的修仙氛围
3. 根据玩家行为调整叙述风格
4. 提供适当的仙侠情感色彩
5. 保持叙述的连贯性和一致性

描述风格：
- 使用丰富的感官描述（灵气、道韵、仙光等）
- 适度的情感渲染，体现修仙者的心境
- 保持客观但富有感染力
- 避免过度干预玩家的选择
- 根据情境调整语气（紧张、轻松、神秘等）
- 使用修仙术语（境界、灵气、道法、天劫等）"""
        super().__init__("Narrator", ai_service, memory_manager, system_prompt)
        self.current_tone = "neutral"
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        event = input_data.get("event", "")
        location = input_data.get("location", "")
        player_action = input_data.get("player_action", "")
        
        context = self._build_context(event, location, player_action)
        thought = await self.think(context)
        
        narration = await self._generate_narration(thought, context)
        
        self.update_conversation("assistant", narration)
        
        self.memory_manager.add_short_term("narrator", narration)
        
        return {
            "narration": narration,
            "tone": self.current_tone,
            "thought": thought
        }
    
    def _build_context(
        self,
        event: str,
        location: str,
        player_action: str
    ) -> str:
        context_parts = []
        
        if location:
            context_parts.append(f"地点：{location}")
        
        if event:
            context_parts.append(f"事件：{event}")
        
        if player_action:
            context_parts.append(f"玩家行为：{player_action}")
        
        memory_context = self.get_memory_context()
        if memory_context:
            context_parts.append(f"最近发生的事：\n{memory_context}")
        
        return "\n".join(context_parts)
    
    async def _generate_narration(self, thought: str, context: str) -> str:
        prompt = f"""基于你的思考：{thought}

当前情境：
{context}

请生成一段生动的旁白描述（200-300字）。

要求：
- 使用丰富的感官描述
- 营造适当的氛围
- 保持客观但富有感染力
- 不要替玩家做决定
- 用中文输出"""
        
        response = await self.ai_service.generate_response(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        
        return response
    
    async def describe_scene(self, scene_data: Dict[str, Any]) -> str:
        prompt = f"""请描述以下场景：

地点：{scene_data.get('name', '')}
环境：{scene_data.get('environment', '')}
时间：{scene_data.get('time', '')}
天气：{scene_data.get('weather', '')}
在场人物：{scene_data.get('characters', '')}

请生成一段生动的场景描述（150-250字）。"""
        
        response = await self.ai_service.generate_response(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        
        return response
    
    async def describe_action(self, action: str, result: str) -> str:
        prompt = f"""玩家执行了以下行动：{action}

行动结果：{result}

请生成一段描述性文字，生动地描述这个行动及其结果（100-150字）。"""
        
        response = await self.ai_service.generate_response(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        
        return response
    
    def set_tone(self, tone: str):
        self.current_tone = tone
        
        tone_prompts = {
            "tense": "当前情境紧张，描述要营造紧迫感。",
            "relaxed": "当前情境轻松，描述要平和舒缓。",
            "mysterious": "当前情境神秘，描述要引人入胜。",
            "dramatic": "当前情境戏剧性，描述要富有张力。",
            "neutral": "保持客观中立的叙述风格。"
        }
        
        self.system_prompt = f"""你是游戏的旁白（Narrator），负责描述游戏世界和情境。

你的职责：
1. 生动地描述环境和场景
2. 营造沉浸式的游戏氛围
3. 根据玩家行为调整叙述风格
4. 提供适当的情感色彩
5. 保持叙述的连贯性和一致性

{tone_prompts.get(tone, tone_prompts['neutral'])}"""