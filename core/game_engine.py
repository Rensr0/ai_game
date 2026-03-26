import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from core.ai_service import AIService
from core.database import GameDatabase
from core.ai_content_generator import AIContentGenerator
from memory.memory_manager import MemoryManager
from core.cultivation import CultivationState, MAP_REGIONS, SKILL_LIBRARY
from core.combat_system import CombatSystem, CombatEntity
from core.item_system import ItemSystem
from agents.game_master_agent import GameMasterAgent
from agents.narrator_agent import NarratorAgent
from agents.npc_agent import NPCAgent
from agents.quest_agent import QuestAgent
from agents.world_agent import WorldAgent


class GameState:
    def __init__(self):
        self.player_name = "玩家"
        self.current_location = "起始村庄"
        self.inventory: List[str] = ["回灵丹", "回灵丹", "聚灵丹"]  # 初始物品
        self.stats = {
            "health": 100,
            "mana": 50,
            "gold": 100,
        }
        self.equipment = {
            "weapon": None,
            "armor": None,
        }
        self.active_quests = []
        self.completed_quests = []
        self.npc_relationships = {}
        self.world_time = "早晨"
        self.weather = "晴朗"
        self.game_started = False
        self.cultivation = CultivationState()
        # 初始技能
        self.cultivation.skills = ["火球术", "护体灵光"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_name": self.player_name,
            "current_location": self.current_location,
            "inventory": self.inventory,
            "stats": self.stats,
            "equipment": self.equipment,
            "active_quests": self.active_quests,
            "completed_quests": self.completed_quests,
            "npc_relationships": self.npc_relationships,
            "world_time": self.world_time,
            "weather": self.weather,
            "game_started": self.game_started,
            "cultivation": self.cultivation.to_dict(),
        }

    def save(self, filepath: str):
        """保存游戏状态到文件"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'GameState':
        """从文件加载游戏状态"""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            state = cls()
            state.player_name = data.get("player_name", "玩家")
            state.current_location = data.get("current_location", "起始村庄")
            state.inventory = data.get("inventory", [])
            state.stats = data.get("stats", {"health": 100, "mana": 50, "gold": 100})
            state.equipment = data.get("equipment", {"weapon": None, "armor": None})
            state.active_quests = data.get("active_quests", [])
            state.completed_quests = data.get("completed_quests", [])
            state.npc_relationships = data.get("npc_relationships", {})
            state.world_time = data.get("world_time", "早晨")
            state.weather = data.get("weather", "晴朗")
            state.game_started = data.get("game_started", False)

            # 加载修仙状态
            cult_data = data.get("cultivation")
            if cult_data:
                state.cultivation = CultivationState.from_dict(cult_data)

            return state
        return cls()

    def get_total_stats(self) -> Dict[str, int]:
        """获取包含装备和境界加成的总属性"""
        bonus = self.cultivation.get_stats_bonus()
        equip_atk = 0
        equip_def = 0
        equip_hp = 0

        for slot, item_name in self.equipment.items():
            if item_name:
                from core.item_system import ITEM_DATABASE
                item = ITEM_DATABASE.get(item_name, {})
                effect = item.get("effect", {})
                equip_atk += effect.get("attack", 0)
                equip_def += effect.get("defense", 0)
                equip_hp += effect.get("hp", 0)

        return {
            "health": self.stats["health"] + bonus["hp"] + equip_hp,
            "mana": self.stats["mana"] + bonus["mp"],
            "attack": 10 + bonus["atk"] + equip_atk,
            "defense": 5 + bonus["def"] + equip_def,
            "gold": self.stats["gold"],
        }


class GameEngine:
    def __init__(self, save_file: str = "data/savegame.json"):
        self.ai_service = None
        self.memory_manager = None
        self.game_master = None
        self.narrator = None
        self.quest_manager = None
        self.world_simulator = None
        self.npcs: Dict[str, NPCAgent] = {}
        self.game_state = GameState()
        self.conversation_history: List[Dict[str, str]] = []
        self.save_file = save_file

        # 数据库和AI内容生成
        self.db = GameDatabase()
        self.content_generator = None  # 初始化后设置

        # 系统（传入数据库引用）
        self.combat_system = CombatSystem(db=self.db)
        self.item_system = ItemSystem(db=self.db)

    async def initialize(self):
        self.ai_service = AIService()
        await self.ai_service.__aenter__()

        self.memory_manager = MemoryManager()

        # 设置AI内容生成器
        self.content_generator = AIContentGenerator(self.ai_service, self.db)

        # 设置修仙状态的数据库引用
        self.game_state.cultivation.set_db(self.db)

        self.game_master = GameMasterAgent(self.ai_service, self.memory_manager)
        self.narrator = NarratorAgent(self.ai_service, self.memory_manager)
        self.quest_manager = QuestAgent(self.ai_service, self.memory_manager)
        self.world_simulator = WorldAgent(self.ai_service, self.memory_manager)

        await self.load_game()

        # AI内容生成放到后台，不阻塞初始化
        # 内容会在游戏过程中按需生成

    async def load_game(self):
        """加载保存的游戏状态"""
        if os.path.exists(self.save_file):
            print(f"正在加载存档：{self.save_file}")
            self.game_state = GameState.load(self.save_file)
            # 加载NPC数据
            npc_file = self.save_file.replace('.json', '_npcs.json')
            if os.path.exists(npc_file):
                try:
                    with open(npc_file, 'r', encoding='utf-8') as f:
                        npc_data = json.load(f)
                    for npc_id, data in npc_data.items():
                        npc = NPCAgent(
                            npc_id=data["npc_id"],
                            name=data["name"],
                            personality=data.get("personality", "友善"),
                            background=data.get("background", "无特殊背景"),
                            goals=data.get("goals", ["生存"]),
                            ai_service=self.ai_service,
                            memory_manager=self.memory_manager,
                        )
                        npc.relationship_score = data.get("relationship_score", 0)
                        npc.role = data.get("role", "村民")
                        npc.location = data.get("location", self.game_state.current_location)
                        npc.appearance = data.get("appearance", "")
                        npc.npc_type = data.get("npc_type", "commoner")
                        self.npcs[npc_id] = npc
                        # 同步到 world_simulator
                        self.world_simulator.npc_pool[npc_id] = npc
                        loc = npc.location
                        if loc not in self.world_simulator.world_state["npc_network"]:
                            self.world_simulator.world_state["npc_network"][loc] = []
                        if npc_id not in self.world_simulator.world_state["npc_network"][loc]:
                            self.world_simulator.world_state["npc_network"][loc].append(npc_id)
                    if npc_data:
                        print(f"已加载 {len(npc_data)} 个NPC")
                except Exception as e:
                    print(f"NPC数据加载失败: {e}")
            print("存档加载成功！")
        else:
            print("未找到存档，开始新游戏。")

    async def save_game(self):
        """保存当前游戏状态"""
        # 保存游戏状态
        self.game_state.save(self.save_file)
        # 保存NPC数据
        npc_file = self.save_file.replace('.json', '_npcs.json')
        npc_data = {}
        for npc_id, npc in self.npcs.items():
            npc_data[npc_id] = {
                "npc_id": npc.npc_id,
                "name": npc.name,
                "personality": npc.personality,
                "background": getattr(npc, 'background', ''),
                "goals": getattr(npc, 'goals', []),
                "role": getattr(npc, 'role', '村民'),
                "location": getattr(npc, 'location', self.game_state.current_location),
                "appearance": getattr(npc, 'appearance', ''),
                "npc_type": getattr(npc, 'npc_type', 'commoner'),
                "relationship_score": npc.relationship_score,
            }
        os.makedirs(os.path.dirname(npc_file), exist_ok=True)
        with open(npc_file, 'w', encoding='utf-8') as f:
            json.dump(npc_data, f, ensure_ascii=False, indent=2)
        # 同步保存到 world_simulator
        self.world_simulator.npc_pool = self.npcs.copy()
        print(f"游戏已保存到：{self.save_file}")

    async def start_game(self) -> Dict[str, Any]:
        all_regions = self._get_all_regions()
        if not self.game_state.game_started:
            self.game_state.game_started = True

            opening_scene = await self._generate_opening_scene()

            return {
                "type": "game_start",
                "narration": opening_scene["narration"],
                "location": self.game_state.current_location,
                "world_state": self.game_state.to_dict(),
                "map_info": all_regions.get(self.game_state.current_location, {}),
            }

        return {
            "type": "already_started",
            "world_state": self.game_state.to_dict(),
            "map_info": all_regions.get(self.game_state.current_location, {}),
        }

    async def _generate_opening_scene(self) -> Dict[str, Any]:
        all_regions = self._get_all_regions()
        region = all_regions.get(self.game_state.current_location, {})
        scene_data = {
            "name": self.game_state.current_location,
            "environment": region.get("description", "一个宁静的地方"),
            "time": self.game_state.world_time,
            "weather": self.game_state.weather,
            "characters": "几位修士在附近活动"
        }

        narration = await self.narrator.describe_scene(scene_data)
        self.memory_manager.add_short_term("narrator", narration)

        return {"narration": narration, "scene": scene_data}

    async def process_player_input(
        self,
        player_input: str,
        input_type: str = "action"
    ) -> Dict[str, Any]:
        self.memory_manager.add_short_term("user", player_input)
        context = self._build_context()

        if input_type == "action":
            return await self._process_action(player_input, context)
        elif input_type == "dialogue":
            return await self._process_dialogue(player_input, context)
        elif input_type == "custom":
            return await self._process_custom_input(player_input, context)
        else:
            return {"error": "Unknown input type"}

    async def _process_action(
        self,
        player_action: str,
        context: str
    ) -> Dict[str, Any]:
        tasks = []

        gm_task = self.game_master.process({
            "player_action": player_action,
            "current_state": self.game_state.to_dict()
        })
        tasks.append(("game_master", gm_task))

        narrator_task = self.narrator.process({
            "event": player_action,
            "location": self.game_state.current_location,
            "player_action": player_action
        })
        tasks.append(("narrator", narrator_task))

        world_task = self.world_simulator.process({
            "action": "simulate_world",
            "context": context
        })
        tasks.append(("world", world_task))

        results = {}
        for name, task in tasks:
            try:
                results[name] = await asyncio.wait_for(task, timeout=30)
            except asyncio.TimeoutError:
                results[name] = {"error": "Timeout"}

        gm_result = results.get("game_master", {})
        narrator_result = results.get("narrator", {})
        world_result = results.get("world", {})

        if gm_result.get("importance", 0) >= 7:
            dynamic_quest = await self.quest_manager.generate_dynamic_quest(
                player_action, context
            )
            if "quest" in dynamic_quest:
                self.game_state.active_quests.append(dynamic_quest["quest"])
                results["new_quest"] = dynamic_quest

        self._update_game_state(gm_result, world_result)

        # 每次行动获得少量修炼经验
        exp_result = self.game_state.cultivation.add_experience(2)

        response = {
            "type": "action_response",
            "narration": narrator_result.get("narration", ""),
            "game_master_thought": gm_result.get("thought", ""),
            "world_description": world_result.get("world_description", ""),
            "state_changes": gm_result.get("state_update", {}),
            "current_state": self.game_state.to_dict(),
            "cultivation": self.game_state.cultivation.to_dict(),
            "map_info": self._get_all_regions().get(self.game_state.current_location, {}),
        }

        if exp_result.get("breakthrough"):
            response["breakthrough"] = {
                "new_realm": exp_result["new_realm"],
                "message": f"🎉 恭喜突破！当前境界：{exp_result['new_realm']}"
            }

        if "new_quest" in results:
            response["new_quest"] = results["new_quest"]

        return response

    async def _process_dialogue(
        self,
        player_input: str,
        context: str
    ) -> Dict[str, Any]:
        nearby_npcs = self._get_nearby_npcs()

        if not nearby_npcs:
            return {
                "type": "dialogue_response",
                "message": "附近没有可以对话的NPC",
                "current_state": self.game_state.to_dict()
            }

        npc_responses = []
        for npc_id in nearby_npcs:
            npc = self.npcs.get(npc_id)
            if npc:
                response = await npc.process({
                    "player_input": player_input,
                    "context": context,
                    "conversation_history": self.conversation_history[-5:]
                })
                npc_responses.append({
                    "npc_id": npc_id,
                    "npc_name": npc.name,
                    **response
                })

        primary_npc = npc_responses[0] if npc_responses else None

        if primary_npc:
            npc_id = primary_npc.get("npc_id")
            npc = self.npcs.get(npc_id)
            if npc:
                self.memory_manager.add_short_term(
                    "dialogue",
                    f"{primary_npc['npc_name']}: {primary_npc['response']}"
                )
                dialogue_options = await npc.generate_dialogue_options(context, num_options=4)
            else:
                dialogue_options = []
        else:
            dialogue_options = []

        return {
            "type": "dialogue_response",
            "npc_responses": npc_responses,
            "dialogue_options": dialogue_options,
            "current_state": self.game_state.to_dict()
        }

    async def _process_custom_input(
        self,
        player_input: str,
        context: str
    ) -> Dict[str, Any]:
        prompt = f"""玩家输入：{player_input}

当前情境：
{context}

请分析这个输入，并决定如何处理。

可能的处理方式：
1. 作为普通行动处理
2. 作为对话处理
3. 作为特殊指令处理

请以JSON格式返回：
{{
    "input_type": "action|dialogue|special",
    "confidence": 0-1,
    "reason": "判断理由"
}}"""

        response = await self.ai_service.generate_response(
            system_prompt="你是输入分析助手，以JSON格式返回分析结果。",
            user_message=prompt
        )

        try:
            import json
            analysis = json.loads(response)

            if analysis["input_type"] == "dialogue":
                return await self._process_dialogue(player_input, context)
            else:
                return await self._process_action(player_input, context)
        except json.JSONDecodeError:
            return await self._process_action(player_input, context)

    def _build_context(self) -> str:
        all_regions = self._get_all_regions()
        context_parts = []

        region = all_regions.get(self.game_state.current_location, {})
        context_parts.append(f"当前位置：{self.game_state.current_location}")
        context_parts.append(f"区域描述：{region.get('description', '')}")
        context_parts.append(f"危险等级：{region.get('danger_level', 1)}")
        context_parts.append(f"时间：{self.game_state.world_time}")
        context_parts.append(f"天气：{self.game_state.weather}")
        context_parts.append(f"修仙境界：{self.game_state.cultivation.full_realm}")

        if self.game_state.active_quests:
            context_parts.append(f"进行中的任务：{', '.join([q['title'] for q in self.game_state.active_quests])}")

        nearby_npcs = self._get_nearby_npcs()
        if nearby_npcs:
            npc_names = [self.npcs[npc_id].name for npc_id in nearby_npcs if npc_id in self.npcs]
            context_parts.append(f"附近的NPC：{', '.join(npc_names)}")

        connections = region.get("connections", [])
        if connections:
            context_parts.append(f"可前往的区域：{', '.join(connections)}")

        memory_context = self.memory_manager.get_context_for_ai()
        if memory_context:
            context_parts.append(f"最近的互动：\n{memory_context}")

        return "\n".join(context_parts)

    def _get_nearby_npcs(self) -> List[str]:
        npc_objects = self.world_simulator.get_npcs_at_location(self.game_state.current_location)
        return [npc.npc_id for npc in npc_objects if hasattr(npc, 'npc_id')]

    def _update_game_state(
        self,
        gm_result: Dict[str, Any],
        world_result: Dict[str, Any]
    ):
        state_updates = gm_result.get("state_update", {})

        if "current_state" in world_result:
            world_state = world_result["current_state"]
            if "time" in world_state:
                self.game_state.world_time = world_state["time"]
            if "weather" in world_state:
                self.game_state.weather = world_state["weather"]

    # ====== 地图系统 ======
    def _get_all_regions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有区域（合并内置 + 数据库AI生成）"""
        regions = dict(MAP_REGIONS)  # 内置区域
        if self.db:
            db_regions = self.db.get_all_regions()
            regions.update(db_regions)
        return regions

    def get_map_info(self) -> Dict[str, Any]:
        """获取地图信息"""
        all_regions = self._get_all_regions()
        region = all_regions.get(self.game_state.current_location, {})
        return {
            "current_location": self.game_state.current_location,
            "region": region,
            "all_regions": {name: {"description": r.get("description", ""), "danger_level": r.get("danger_level", 1)}
                           for name, r in all_regions.items()},
        }

    async def move_to_location(self, target_location: str) -> Dict[str, Any]:
        """移动到指定位置"""
        all_regions = self._get_all_regions()
        current_region = all_regions.get(self.game_state.current_location, {})
        connections = current_region.get("connections", [])

        if target_location not in connections:
            return {
                "error": f"无法直接前往 {target_location}，当前位置只能前往：{', '.join(connections)}"
            }

        if target_location not in all_regions:
            return {"error": f"未知地点：{target_location}"}

        self.game_state.current_location = target_location
        self.memory_manager.add_short_term(
            "movement",
            f"玩家移动到了 {target_location}"
        )

        region = all_regions[target_location]

        # 移动时消耗时间
        time_result = await self.world_simulator.advance_time(1)

        # 随机遭遇
        encounter = None
        import random
        if random.random() < 0.3 * region["danger_level"] / 7:
            enemy_types = {
                1: ["妖兽", "散修"],
                2: ["妖兽", "灵兽"],
                3: ["妖兽", "魔修"],
                4: ["魔修", "妖兽"],
                5: ["灵兽", "魔修"],
                6: ["妖王"],
                7: ["守护者"],
            }
            possible_enemies = enemy_types.get(region["danger_level"], ["妖兽"])
            enemy_type = random.choice(possible_enemies)
            level = region["danger_level"]
            enemy = self.combat_system.create_enemy(enemy_type, level)
            encounter = {
                "type": "combat",
                "enemy": enemy.to_dict(),
            }

        # 生成旁白
        scene_data = {
            "name": target_location,
            "environment": region["description"],
            "time": self.game_state.world_time,
            "weather": self.game_state.weather,
            "characters": "周围有零星的修士身影"
        }
        narration = await self.narrator.describe_scene(scene_data)

        return {
            "type": "movement",
            "new_location": target_location,
            "narration": narration,
            "region": region,
            "time": self.game_state.world_time,
            "encounter": encounter,
            "current_state": self.game_state.to_dict(),
        }

    # ====== 战斗系统 ======
    def start_combat(self, enemy_data: Dict[str, Any]) -> Dict[str, Any]:
        """开始战斗"""
        total_stats = self.game_state.get_total_stats()
        player_entity = CombatEntity(
            name=self.game_state.player_name,
            hp=total_stats["health"],
            max_hp=total_stats["health"],
            mp=total_stats["mana"],
            max_mp=total_stats["mana"],
            attack=total_stats["attack"],
            defense=total_stats["defense"],
            speed=10,
            skills=self.game_state.cultivation.skills.copy(),
            is_player=True,
        )

        enemy = CombatEntity(
            name=enemy_data["name"],
            hp=enemy_data["hp"],
            max_hp=enemy_data["max_hp"],
            mp=enemy_data["mp"],
            max_mp=enemy_data["max_mp"],
            attack=enemy_data["attack"],
            defense=enemy_data["defense"],
            speed=enemy_data.get("speed", 10),
            skills=enemy_data.get("skills", []),
        )

        return self.combat_system.start_combat(player_entity, enemy)

    def execute_combat_turn(self, action: str, skill_name: Optional[str] = None) -> Dict[str, Any]:
        """执行战斗回合"""
        result = self.combat_system.execute_turn(action, skill_name)

        if result.get("status") == "victory":
            rewards = result.get("rewards", {})
            # 应用奖励
            exp_result = self.game_state.cultivation.add_experience(rewards.get("experience", 0))
            self.game_state.cultivation.spirit_stones += rewards.get("spirit_stones", 0)
            self.game_state.stats["gold"] += rewards.get("gold", 0)
            for item in rewards.get("items", []):
                self.game_state.inventory.append(item)
            result["exp_result"] = exp_result

        elif result.get("status") == "defeat":
            penalty = result.get("penalty", {})
            self.game_state.stats["gold"] = max(0, self.game_state.stats["gold"] - penalty.get("gold_lost", 0))
            # 复活并恢复部分血量
            self.game_state.stats["health"] = max(30, self.game_state.stats["health"])

        # 更新玩家战斗后的状态
        player_data = result.get("player", {})
        if player_data:
            self.game_state.stats["health"] = player_data.get("hp", self.game_state.stats["health"])
            self.game_state.stats["mana"] = player_data.get("mp", self.game_state.stats["mana"])

        return result

    def get_combat_status(self) -> Optional[Dict[str, Any]]:
        return self.combat_system.get_combat_status()

    def end_combat(self):
        self.combat_system.end_combat_cleanup()

    # ====== 物品系统 ======
    def use_item(self, item_name: str) -> Dict[str, Any]:
        if item_name not in self.game_state.inventory:
            return {"error": f"你没有 {item_name}"}

        item_info = self.item_system.get_item_info(item_name)
        if not item_info:
            return {"error": f"未知物品：{item_name}"}

        # 使用物品（传入 total_stats 以便正确计算恢复上限）
        player_data = self.game_state.to_dict()
        player_data["total_stats"] = self.game_state.get_total_stats()
        result = self.item_system.use_item(item_name, player_data)

        # 消耗物品（一次性物品）
        if item_info["type"] in ["consumable", "skill_book", "material"]:
            self.game_state.inventory.remove(item_name)

        # 学习技能
        if "skill_learned" in result:
            skill = result["skill_learned"]
            if self.game_state.cultivation.can_learn_skill(skill):
                self.game_state.cultivation.learn_skill(skill)
            else:
                result["warning"] = f"已经学会了 {skill} 或境界不足"

        # 获取灵石
        if "spirit_stones_gained" in result:
            self.game_state.cultivation.spirit_stones += result["spirit_stones_gained"]

        # 获取经验
        if "exp_gained" in result:
            self.game_state.cultivation.add_experience(result["exp_gained"])

        # 装备
        if "equipped" in result:
            equip_type = item_info["subtype"]
            slot = "weapon" if equip_type == "weapon" else "armor"
            if self.game_state.equipment[slot]:
                self.game_state.inventory.append(self.game_state.equipment[slot])
            self.game_state.equipment[slot] = item_name
            self.game_state.inventory.remove(item_name)

        result["current_state"] = self.game_state.to_dict()
        return result

    def get_shop_items(self) -> List[Dict[str, Any]]:
        return self.item_system.get_shop_items(self.game_state.cultivation.realm_index)

    def buy_item(self, item_name: str) -> Dict[str, Any]:
        item = self.item_system.get_item_info(item_name)
        if not item:
            return {"error": f"未知物品：{item_name}"}

        price = item.get("price", 0)
        if self.game_state.stats["gold"] < price:
            return {"error": f"金币不足，需要 {price} 金币，当前只有 {self.game_state.stats['gold']} 金币"}

        self.game_state.stats["gold"] -= price
        self.game_state.inventory.append(item_name)

        return {
            "success": True,
            "item": item_name,
            "gold_spent": price,
            "gold_remaining": self.game_state.stats["gold"],
        }

    def sell_item(self, item_name: str) -> Dict[str, Any]:
        if item_name not in self.game_state.inventory:
            return {"error": f"你没有 {item_name}"}

        item = self.item_system.get_item_info(item_name)
        if not item:
            return {"error": f"未知物品：{item_name}"}

        sell_price = item.get("price", 0) // 2
        self.game_state.inventory.remove(item_name)
        self.game_state.stats["gold"] += sell_price

        return {
            "success": True,
            "item": item_name,
            "gold_gained": sell_price,
            "gold_total": self.game_state.stats["gold"],
        }

    # ====== 修仙系统 ======
    def get_cultivation_info(self) -> Dict[str, Any]:
        return {
            "cultivation": self.game_state.cultivation.to_dict(),
            "available_skills": self.game_state.cultivation.get_available_skills(),
            "total_stats": self.game_state.get_total_stats(),
        }

    async def meditate(self) -> Dict[str, Any]:
        """打坐修炼"""
        import random
        base_exp = 5 + self.game_state.cultivation.realm_index * 3
        bonus_exp = random.randint(0, base_exp // 2)
        total_exp = base_exp + bonus_exp

        # 回复灵力
        mp_restore = 10 + self.game_state.cultivation.realm_index * 5
        max_mp = self.game_state.get_total_stats()["mana"]
        actual_mp = min(mp_restore, max_mp - self.game_state.stats["mana"])
        self.game_state.stats["mana"] += actual_mp

        # 推进时间
        await self.world_simulator.advance_time(2)
        # 同步时间到 game_state
        self.game_state.world_time = self.world_simulator.world_state["time"]

        exp_result = self.game_state.cultivation.add_experience(total_exp)

        return {
            "exp_gained": total_exp,
            "mp_restored": actual_mp,
            "exp_result": exp_result,
            "cultivation": self.game_state.cultivation.to_dict(),
        }

    # ====== 原有功能 ======
    def add_npc(self, npc: NPCAgent):
        self.npcs[npc.npc_id] = npc

    async def get_quests(self) -> Dict[str, Any]:
        return await self.quest_manager.check_quests()

    async def accept_quest(self, quest_type: str = "side") -> Dict[str, Any]:
        context = self._build_context()
        return await self.quest_manager.generate_quest(context, quest_type)

    async def advance_time(self, amount: int = 1) -> Dict[str, Any]:
        result = await self.world_simulator.advance_time(amount)
        self.game_state.world_time = result["time"]
        return result

    async def trigger_random_event(self) -> Dict[str, Any]:
        context = self._build_context()
        return await self.world_simulator.generate_random_event(context)

    async def spawn_random_npc(self, npc_type: str = "散修") -> Dict[str, Any]:
        context = self._build_context()
        result = await self.world_simulator.spawn_npc(
            self.game_state.current_location, context, npc_type
        )
        npc_id = result.get("npc_id")
        if npc_id and npc_id in self.world_simulator.npc_pool:
            npc = self.world_simulator.npc_pool[npc_id]
            self.npcs[npc_id] = npc
        return result

    async def spawn_npc_group(self, count: int = 3) -> Dict[str, Any]:
        context = self._build_context()
        result = await self.world_simulator.spawn_npc_group(
            self.game_state.current_location, context, count
        )
        for npc_info in result.get("npcs", []):
            npc_id = npc_info.get("npc_id")
            if npc_id and npc_id in self.world_simulator.npc_pool:
                npc = self.world_simulator.npc_pool[npc_id]
                self.npcs[npc_id] = npc
        return result

    async def spawn_special_npc(self, special_type: str) -> Dict[str, Any]:
        context = self._build_context()
        result = await self.world_simulator.spawn_special_npc(
            self.game_state.current_location, context, special_type
        )
        npc_id = result.get("npc_id")
        if npc_id and npc_id in self.world_simulator.npc_pool:
            npc = self.world_simulator.npc_pool[npc_id]
            self.npcs[npc_id] = npc
        return result

    async def trigger_dynamic_world(self) -> Dict[str, Any]:
        context = self._build_context()
        result = await self.world_simulator.generate_dynamic_world_content(
            self.game_state.current_location, context
        )
        for action in result.get("actions", []):
            if action["type"] == "npc_spawn":
                npc_id = action["data"].get("npc_id")
                if npc_id and npc_id in self.world_simulator.npc_pool:
                    npc = self.world_simulator.npc_pool[npc_id]
                    self.npcs[npc_id] = npc
            if "current_state" in action.get("data", {}):
                world_state = action["data"]["current_state"]
                if "time" in world_state:
                    self.game_state.world_time = world_state["time"]
                if "weather" in world_state:
                    self.game_state.weather = world_state["weather"]
        return result

    def get_all_npcs(self) -> Dict[str, NPCAgent]:
        return self.world_simulator.npc_pool.copy()

    def get_npc_by_id(self, npc_id: str) -> Optional[NPCAgent]:
        return self.world_simulator.get_npc(npc_id)

    async def close(self):
        if self.ai_service:
            await self.ai_service.close()
