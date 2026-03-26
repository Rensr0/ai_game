import random
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from core.ai_service import AIService
from memory.memory_manager import MemoryManager
from agents.npc_generator import NPCGenerator

class WorldAgent(BaseAgent):
    def __init__(
        self,
        ai_service: AIService,
        memory_manager: MemoryManager
    ):
        system_prompt = """你是世界模拟器（World Simulator），负责维护游戏世界的状态和演化。

你的职责：
1. 模拟世界的自然变化
2. 处理环境事件（天气、时间等）
3. 管理NPC之间的互动
4. 维护世界的逻辑一致性
5. 生成随机事件和遭遇

世界要素：
- 地点和区域
- 天气和季节
- 时间系统
- NPC社会网络
- 经济和政治状况

模拟原则：
- 保持世界的真实感
- 事件要有合理的因果关系
- 变化要渐进而非突兀
- 给玩家提供探索和发现的机会"""
        
        super().__init__("WorldSimulator", ai_service, memory_manager, system_prompt)
        self.world_state = {
            "time": "早晨",
            "weather": "晴朗",
            "season": "春季",
            "locations": {},
            "npc_network": {}
        }
        self.npc_generator = NPCGenerator(ai_service, memory_manager)
        self.npc_pool: Dict[str, Any] = {}
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action", "")
        context = input_data.get("context", "")
        
        if action == "advance_time":
            return await self.advance_time(input_data.get("amount", 1))
        elif action == "change_weather":
            return await self.change_weather(context)
        elif action == "npc_interaction":
            return await self.simulate_npc_interaction(input_data)
        elif action == "generate_event":
            return await self.generate_random_event(context)
        elif action == "update_location":
            return await self.update_location(input_data)
        else:
            return await self.simulate_world(context)
    
    async def simulate_world(self, context: str) -> Dict[str, Any]:
        prompt = f"""当前世界状态：
时间：{self.world_state['time']}
天气：{self.world_state['weather']}
季节：{self.world_state['season']}

当前情境：
{context}

请描述世界在这一刻的自然变化和状态（100-150字）。

包括：
- 环境的细微变化
- 可能发生的小事件
- 氛围的描述"""
        
        response = await self.ai_service.generate_response(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        
        return {
            "world_description": response,
            "current_state": self.world_state.copy()
        }
    
    async def advance_time(self, amount: int = 1) -> Dict[str, Any]:
        time_periods = ["早晨", "上午", "中午", "下午", "傍晚", "夜晚", "深夜"]
        
        current_index = time_periods.index(self.world_state["time"])
        new_index = (current_index + amount) % len(time_periods)
        self.world_state["time"] = time_periods[new_index]
        
        self.memory_manager.set_world_state("time", self.world_state["time"])
        
        return {
            "time": self.world_state["time"],
            "message": f"时间流逝，现在是{self.world_state['time']}"
        }
    
    async def change_weather(self, context: str) -> Dict[str, Any]:
        prompt = f"""当前天气：{self.world_state['weather']}
季节：{self.world_state['season']}

当前情境：
{context}

请决定天气是否变化，以及变成什么天气。

可能的天气：晴朗、多云、阴天、小雨、大雨、雷暴、雪、雾

请只返回新的天气（如果不变化，返回当前天气）。"""
        
        response = await self.ai_service.generate_response(
            system_prompt="你是天气系统，只返回天气名称。",
            user_message=prompt
        )
        
        new_weather = response.strip()
        self.world_state["weather"] = new_weather
        self.memory_manager.set_world_state("weather", new_weather)
        
        return {
            "weather": new_weather,
            "message": f"天气变成了{new_weather}"
        }
    
    async def simulate_npc_interaction(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        npc1 = input_data.get("npc1", "")
        npc2 = input_data.get("npc2", "")
        context = input_data.get("context", "")
        
        prompt = f"""模拟以下两个NPC之间的互动：

NPC1：{npc1}
NPC2：{npc2}

当前情境：
{context}

请描述他们之间可能发生的互动（100-150字）。

包括：
- 他们的对话或行为
- 互动的结果
- 对关系的影响"""
        
        response = await self.ai_service.generate_response(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        
        return {
            "interaction": response,
            "npc1": npc1,
            "npc2": npc2
        }
    
    async def generate_random_event(self, context: str) -> Dict[str, Any]:
        prompt = f"""当前世界状态：
时间：{self.world_state['time']}
天气：{self.world_state['weather']}
季节：{self.world_state['season']}

当前情境：
{context}

请生成一个随机事件（100-150字）。

事件类型可以是：
- 自然现象
- NPC的自主行为
- 意外发现
- 小型冲突
- 有趣的遭遇

用中文输出。"""
        
        response = await self.ai_service.generate_response(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        
        return {
            "event": response,
            "event_type": "random"
        }
    
    async def update_location(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        location_name = input_data.get("name", "")
        location_data = input_data.get("data", {})
        
        if location_name:
            self.world_state["locations"][location_name] = location_data
            
            self.memory_manager.set_world_state(
                f"location_{location_name}",
                str(location_data)
            )
            
            return {
                "location": location_name,
                "data": location_data,
                "message": f"地点'{location_name}'已更新"
            }
        
        return {"error": "Location name required"}
    
    async def generate_location(
        self,
        location_type: str,
        context: str
    ) -> Dict[str, Any]:
        prompt = f"""请生成一个{location_type}类型的地点。

当前情境：
{context}

请以JSON格式返回地点信息：
{{
    "name": "地点名称",
    "description": "地点描述（100-150字）",
    "environment": "环境特征",
    "npcs": ["可能出现的NPC1", "NPC2"],
    "points_of_interest": ["兴趣点1", "兴趣点2"],
    "atmosphere": "氛围描述"
}}"""
        
        response = await self.ai_service.generate_response(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        
        try:
            import json
            location_data = json.loads(response)
            self.world_state["locations"][location_data["name"]] = location_data
            
            return {"location": location_data}
        except json.JSONDecodeError:
            return {"error": "Failed to parse location data"}
    
    def get_world_state(self) -> Dict[str, Any]:
        return self.world_state.copy()
    
    def set_world_state(self, key: str, value: Any):
        self.world_state[key] = value
        self.memory_manager.set_world_state(key, str(value))
    
    async def spawn_npc(
        self,
        location: str,
        context: str,
        npc_type: str = "commoner"
    ) -> Dict[str, Any]:
        npc = await self.npc_generator.generate_npc(location, context, npc_type)
        
        self.npc_pool[npc.npc_id] = npc
        
        if location not in self.world_state["npc_network"]:
            self.world_state["npc_network"][location] = []
        
        self.world_state["npc_network"][location].append(npc.npc_id)
        
        self.memory_manager.add_long_term(
            content=f"新NPC {npc.name} 出现在 {location}",
            memory_type="npc_spawn",
            importance=4,
            participants=[npc.npc_id],
            context=context
        )
        
        return {
            "npc_id": npc.npc_id,
            "npc_name": npc.name,
            "location": location,
            "npc_type": npc_type,
            "message": f"{npc.name} 出现在了 {location}"
        }
    
    async def spawn_npc_group(
        self,
        location: str,
        context: str,
        count: int = 3
    ) -> Dict[str, Any]:
        npcs = await self.npc_generator.generate_npc_group(location, context, count)
        
        spawned_npcs = []
        for npc in npcs:
            self.npc_pool[npc.npc_id] = npc
            
            if location not in self.world_state["npc_network"]:
                self.world_state["npc_network"][location] = []
            
            self.world_state["npc_network"][location].append(npc.npc_id)
            spawned_npcs.append({
                "npc_id": npc.npc_id,
                "npc_name": npc.name
            })
        
        npc_names = ", ".join([npc.name for npc in npcs])
        
        self.memory_manager.add_long_term(
            content=f"新NPC群体出现在 {location}：{npc_names}",
            memory_type="npc_spawn",
            importance=5,
            participants=[npc.npc_id for npc in npcs],
            context=context
        )
        
        return {
            "npcs": spawned_npcs,
            "location": location,
            "count": count,
            "message": f"{count} 个新NPC出现在了 {location}"
        }
    
    async def spawn_special_npc(
        self,
        location: str,
        context: str,
        special_type: str
    ) -> Dict[str, Any]:
        npc = await self.npc_generator.generate_special_npc(location, context, special_type)
        
        self.npc_pool[npc.npc_id] = npc
        
        if location not in self.world_state["npc_network"]:
            self.world_state["npc_network"][location] = []
        
        self.world_state["npc_network"][location].append(npc.npc_id)
        
        self.memory_manager.add_long_term(
            content=f"特殊NPC {npc.name} 出现在 {location}",
            memory_type="special_npc_spawn",
            importance=8,
            participants=[npc.npc_id],
            context=context
        )
        
        return {
            "npc_id": npc.npc_id,
            "npc_name": npc.name,
            "location": location,
            "special_type": special_type,
            "message": f"神秘的 {npc.name} 出现在了 {location}"
        }
    
    def get_npc(self, npc_id: str) -> Any:
        return self.npc_pool.get(npc_id)
    
    def get_npcs_at_location(self, location: str) -> List[Any]:
        npc_ids = self.world_state["npc_network"].get(location, [])
        return [self.npc_pool.get(npc_id) for npc_id in npc_ids if npc_id in self.npc_pool]
    
    def remove_npc(self, npc_id: str) -> bool:
        if npc_id in self.npc_pool:
            npc = self.npc_pool[npc_id]
            
            for location, npc_ids in self.world_state["npc_network"].items():
                if npc_id in npc_ids:
                    npc_ids.remove(npc_id)
            
            del self.npc_pool[npc_id]
            
            self.memory_manager.add_long_term(
                content=f"NPC {npc.name} 离开了当前区域",
                memory_type="npc_departure",
                importance=3,
                participants=[npc_id],
                context="NPC离开"
            )
            
            return True
        
        return False
    
    async def random_npc_encounter(
        self,
        location: str,
        context: str
    ) -> Dict[str, Any]:
        npc_types = self.npc_generator.get_npc_types_for_location(location)
        npc_type = random.choice(npc_types)
        
        return await self.spawn_npc(location, context, npc_type)
    
    async def generate_dynamic_world_content(
        self,
        location: str,
        context: str
    ) -> Dict[str, Any]:
        import random
        
        actions = []
        
        if random.random() < 0.3:
            npc_spawn = await self.random_npc_encounter(location, context)
            actions.append({
                "type": "npc_spawn",
                "data": npc_spawn
            })
        
        if random.random() < 0.2:
            event = await self.generate_random_event(context)
            actions.append({
                "type": "event",
                "data": event
            })
        
        if random.random() < 0.15:
            weather_change = await self.change_weather(context)
            actions.append({
                "type": "weather_change",
                "data": weather_change
            })
        
        return {
            "location": location,
            "actions": actions,
            "message": f"世界发生了 {len(actions)} 个变化"
        }