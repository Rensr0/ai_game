import random
from typing import Dict, Any, List
from core.ai_service import AIService
from memory.memory_manager import MemoryManager
from agents.npc_agent import NPCAgent

class NPCGenerator:
    def __init__(
        self,
        ai_service: AIService,
        memory_manager: MemoryManager
    ):
        self.ai_service = ai_service
        self.memory_manager = memory_manager
        
        self.name_prefixes = ["老", "小", "大", "神秘的", "流浪的", "退休的", "年轻的"]
        self.name_surnames = ["李", "王", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴"]
        self.name_given_names = ["明", "华", "强", "伟", "芳", "娜", "杰", "婷", "磊", "敏", "静", "勇", "慧", "斌", "霞", "涛", "洋", "艳", "军", "平", "刚", "桂", "玲", "萍", "飞", "鹏", "浩", "宇", "轩", "怡", "然", "文", "博", "睿", "嘉", "怡", "欣", "颖", "雯", "凯", "健", "明", "秀", "娟", "彦", "豪", "峰", "磊", "军", "平", "亮", "翔", "超", "勇", "毅", "俊", "峰", "强", "辉", "鹏", "杰", "涛", "明", "超", "勇", "毅", "俊", "峰", "强", "辉"]
        
        self.personality_templates = [
            "温和谦逊，修为正道，乐于助人",
            "孤傲冷漠，修为魔道，不易信任他人",
            "幽默风趣，喜欢讲道法趣事，总能带来欢乐",
            "严肃认真，修炼刻苦，对道法一丝不苟",
            "慈悲善良，心怀苍生，总是帮助有需要的人",
            "急躁直率，说话不拐弯抹角，但道心纯正",
            "神秘深沉，修为隐道，话不多但每句都有深意",
            "乐观积极，充满灵气，总能看到事情好的一面",
            "谨慎稳重，总是担心天劫，但很细心",
            "好奇求知，喜欢探索秘境，充满冒险精神"
        ]
        
        self.background_templates = [
            "在这个宗门修炼多年，见证了无数的变化",
            "来自远方的散修，走遍各地，见多识广",
            "曾经是著名的修仙者，现在选择过平静的生活",
            "出身贫寒，靠自己的努力获得了现在的修为",
            "有着神秘的过去，不愿多提自己的来历",
            "家族世代居住于此，对当地修仙界了如指掌",
            "年轻时离开家乡，如今带着丰富的经历归来",
            "经历过重大变故，正在寻找新的道心",
            "拥有特殊的天赋，被人们称为奇才",
            "只是一个普通修士，过着简单而充实的修炼生活"
        ]
        
        self.goal_templates = [
            ["突破境界", "飞升仙界"],
            ["探索秘境", "发现新的机缘"],
            ["积累灵石", "成为最富有的人"],
            ["帮助有需要的人", "传播正道"],
            ["寻找失散的亲人", "解开家族的秘密"],
            ["学习新的功法", "成为一代宗师"],
            ["建立自己的宗门", "获得认可"],
            ["守护宗门的和平", "维护正义"],
            ["寻找道侣", "建立幸福的家庭"],
            ["记录修仙历史", "传承道统"]
        ]
    
    async def generate_npc(
        self,
        location: str,
        context: str,
        npc_type: str = "commoner"
    ) -> NPCAgent:
        prompt = f"""请为以下地点生成一个修仙世界的NPC：

地点：{location}
NPC类型：{npc_type}

当前情境：
{context}

请以JSON格式返回NPC信息：
{{
    "name": "NPC姓名（中文名字）",
    "personality": "性格描述（20-30字）",
    "background": "背景故事（30-50字）",
    "goals": ["目标1", "目标2"],
    "appearance": "外貌描述（20-30字）",
    "role": "在修仙界的角色（如散修、宗门长老、炼丹师等）"
}}

要求：
- 名字必须是中文，符合修仙界文化
- 性格要具体生动，符合修仙者特点
- 背景要有修仙故事性
- 目标要符合修仙界设定（如突破境界、寻找机缘等）
- 用中文输出"""
        
        response = await self.ai_service.generate_response(
            system_prompt="你是NPC生成助手，以JSON格式返回NPC信息。",
            user_message=prompt
        )
        
        try:
            import json
            npc_data = json.loads(response)
            
            npc_id = f"npc_{random.randint(1000, 9999)}"
            
            npc = NPCAgent(
                npc_id=npc_id,
                name=npc_data.get("name", "未知NPC"),
                personality=npc_data.get("personality", "普通"),
                background=npc_data.get("background", "无"),
                goals=npc_data.get("goals", ["生存"]),
                ai_service=self.ai_service,
                memory_manager=self.memory_manager
            )
            
            npc.appearance = npc_data.get("appearance", "普通外貌")
            npc.role = npc_data.get("role", "村民")
            npc.location = location
            npc.npc_type = npc_type
            
            return npc
            
        except json.JSONDecodeError:
            return await self._generate_fallback_npc(location, npc_type)
    
    async def _generate_fallback_npc(
        self,
        location: str,
        npc_type: str
    ) -> NPCAgent:
        prefix = random.choice(self.name_prefixes)
        surname = random.choice(self.name_surnames)
        given_name = random.choice(self.name_given_names)
        name = f"{prefix}{surname}{given_name}"
        
        personality = random.choice(self.personality_templates)
        background = random.choice(self.background_templates)
        goals = random.choice(self.goal_templates)
        
        npc_id = f"npc_{random.randint(1000, 9999)}"
        
        npc = NPCAgent(
            npc_id=npc_id,
            name=name,
            personality=personality,
            background=background,
            goals=goals,
            ai_service=self.ai_service,
            memory_manager=self.memory_manager
        )
        
        npc.appearance = "普通的外表"
        npc.role = "村民"
        npc.location = location
        npc.npc_type = npc_type
        
        return npc
    
    async def generate_npc_group(
        self,
        location: str,
        context: str,
        count: int = 3
    ) -> List[NPCAgent]:
        npcs = []
        
        for _ in range(count):
            npc = await self.generate_npc(location, context)
            npcs.append(npc)
        
        return npcs
    
    async def generate_special_npc(
        self,
        location: str,
        context: str,
        special_type: str
    ) -> NPCAgent:
        prompt = f"""请为以下地点生成一个特殊NPC：

地点：{location}
特殊类型：{special_type}

当前情境：
{context}

请以JSON格式返回NPC信息：
{{
    "name": "NPC姓名",
    "personality": "性格描述（30-40字）",
    "background": "背景故事（50-80字）",
    "goals": ["目标1", "目标2", "目标3"],
    "appearance": "外貌描述（30-40字）",
    "role": "特殊角色",
    "special_abilities": ["特殊能力1", "特殊能力2"]
}}

要求：
- 要有独特的特征和能力
- 背景要有神秘感或传奇色彩
- 用中文输出"""
        
        response = await self.ai_service.generate_response(
            system_prompt="你是特殊NPC生成助手，以JSON格式返回NPC信息。",
            user_message=prompt
        )
        
        try:
            import json
            npc_data = json.loads(response)
            
            npc_id = f"special_npc_{random.randint(1000, 9999)}"
            
            npc = NPCAgent(
                npc_id=npc_id,
                name=npc_data.get("name", "神秘NPC"),
                personality=npc_data.get("personality", "神秘"),
                background=npc_data.get("background", "未知"),
                goals=npc_data.get("goals", ["探索"]),
                ai_service=self.ai_service,
                memory_manager=self.memory_manager
            )
            
            npc.appearance = npc_data.get("appearance", "神秘的外表")
            npc.role = npc_data.get("role", "神秘人物")
            npc.location = location
            npc.npc_type = "special"
            npc.special_abilities = npc_data.get("special_abilities", [])
            
            return npc
            
        except json.JSONDecodeError:
            return await self._generate_fallback_npc(location, "special")
    
    def get_npc_types_for_location(self, location: str) -> List[str]:
        location_npc_types = {
            "起始村庄": ["散修", "宗门弟子", "农夫", "炼丹师"],
            "秘境": ["修仙者", "隐士", "散修", "妖兽"],
            "仙城": ["商贾", "守卫", "仙师", "阵法师", "刺客"],
            "灵山": ["矿工", "隐士", "剑修", "佛修"],
            "仙海": ["渔夫", "修士", "海盗", "商贾"]
        }
        
        return location_npc_types.get(location, ["散修"])