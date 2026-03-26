"""
AI内容生成器 - 使用AI动态生成游戏内容并存储到数据库
支持：物品、地图区域、敌人模板、技能
"""
import json
import hashlib
import random
from typing import Dict, Any, List, Optional
from core.ai_service import AIService
from core.database import GameDatabase


class AIContentGenerator:
    """AI驱动的游戏内容生成器"""

    def __init__(self, ai_service: AIService, db: GameDatabase):
        self.ai = ai_service
        self.db = db

    async def generate_item(
        self,
        item_type: str = "consumable",
        realm_level: int = 1,
        context: str = ""
    ) -> Optional[Dict[str, Any]]:
        """AI生成一个物品"""
        type_prompts = {
            "consumable": "消耗品（丹药、药水等）",
            "equipment": "装备（武器或护甲）",
            "skill_book": "功法秘籍",
            "material": "材料（灵石、矿石、灵草等）",
        }

        rarity_by_realm = {
            1: "普通(common)或优秀(uncommon)",
            2: "优秀(uncommon)或稀有(rare)",
            3: "稀有(rare)或史诗(epic)",
            4: "史诗(epic)或传说(legendary)",
        }

        realm_desc = f"适合{realm_level}境界修士使用"
        rarity_hint = rarity_by_realm.get(min(realm_level, 4), "任意品质")

        prompt = f"""请为修仙世界游戏生成一个{type_prompts.get(item_type, '物品')}。

要求：
- 境界要求：{realm_desc}
- 品质倾向：{rarity_hint}
- 当前情境：{context or '普通游戏进程'}

请以严格的JSON格式返回（不要包含markdown代码块）：
{{
    "name": "物品名称（修仙风格中文名）",
    "type": "{item_type}",
    "subtype": "子类型（如pill/weapon/armor/manual/ore/herb等）",
    "effect": {{"具体效果键值对"}},
    "description": "物品描述（20-40字）",
    "price": 价格数字,
    "rarity": "品质（common/uncommon/rare/epic/legendary之一）",
    "realm_required": 最低境界等级(1-8)
}}

效果说明：
- consumable: effect可用 heal_hp, heal_mp, exp_boost+duration, breakthrough_bonus
- equipment(weapon): effect用 attack, 可选 speed
- equipment(armor): effect用 defense, 可选 hp
- skill_book: effect用 skill(技能名)
- material: effect用 spirit_stones 或 exp_gain 或空

品质对照价格参考：common=10-50, uncommon=30-150, rare=100-500, epic=300-2000, legendary=1000-5000"""

        try:
            response = await self.ai.generate_response(
                system_prompt="你是修仙世界物品生成助手，只返回JSON。",
                user_message=prompt
            )
            item_data = self._parse_json_response(response)
            if not item_data or "name" not in item_data:
                return None

            item_data["source"] = "ai_generated"
            item_id = self.db.add_item(item_data)
            item_data["id"] = item_id
            return item_data
        except Exception as e:
            print(f"AI生成物品失败: {e}")
            return None

    async def generate_region(
        self,
        connect_to: str = "",
        danger_range: tuple = (1, 5),
        context: str = ""
    ) -> Optional[Dict[str, Any]]:
        """AI生成一个新地图区域"""
        connect_hint = ""
        if connect_to:
            connect_hint = f"该区域需要与「{connect_to}」相连"

        prompt = f"""请为修仙世界游戏生成一个新的探索区域。

要求：
- 危险等级在{danger_range[0]}到{danger_range[1]}之间
- {connect_hint}
- 当前情境：{context or '玩家正在探索世界'}

请以严格的JSON格式返回（不要包含markdown代码块）：
{{
    "name": "区域名称（修仙风格中文地名）",
    "description": "区域描述（50-100字，要有画面感）",
    "connections": ["连接的区域名1", "连接的区域名2"],
    "npc_types": ["可能出现的NPC类型1", "NPC类型2"],
    "danger_level": 危险等级(1-7),
    "resources": ["可采集资源1", "资源2"]
}}

注意：
- 区域名要有修仙意境（如：XX峰、XX潭、XX谷、XX城等）
- 危险等级越高，资源越丰富但敌人越强
- NPC类型用修仙术语（散修、宗门弟子、炼丹师等）"""

        try:
            response = await self.ai.generate_response(
                system_prompt="你是修仙世界地图生成助手，只返回JSON。",
                user_message=prompt
            )
            region_data = self._parse_json_response(response)
            if not region_data or "name" not in region_data:
                return None

            # 确保与指定区域相连
            if connect_to and connect_to not in region_data.get("connections", []):
                region_data.setdefault("connections", []).append(connect_to)

            region_data["source"] = "ai_generated"
            region_id = self.db.add_region(region_data)
            region_data["id"] = region_id
            return region_data
        except Exception as e:
            print(f"AI生成区域失败: {e}")
            return None

    async def generate_enemy_template(
        self,
        enemy_type: str = "",
        danger_level: int = 1,
        context: str = ""
    ) -> Optional[Dict[str, Any]]:
        """AI生成一个敌人模板"""
        type_hint = enemy_type or "根据危险等级自动选择合适的类型"

        prompt = f"""请为修仙世界游戏生成一个敌人模板。

要求：
- 敌人类型：{type_hint}
- 危险等级：{danger_level}
- 当前情境：{context or '普通遭遇'}

请以严格的JSON格式返回（不要包含markdown代码块）：
{{
    "type": "敌人类型（如妖兽/灵兽/魔修/散修/妖王/守护者等）",
    "name_prefix": "名字前缀（如凶猛的/远古的，可为空）",
    "name_suffix": "名字后缀（如烈焰虎/血魔）",
    "base_hp": 基础生命值,
    "base_mp": 基础灵力值,
    "base_atk": 基础攻击力,
    "base_def": 基础防御力,
    "skills": ["技能1", "技能2"],
    "description": "敌人描述（20-40字）",
    "min_danger": 最低出现危险等级,
    "max_danger": 最高出现危险等级
}}

属性参考（danger_level=1）：hp=30-80, mp=10-40, atk=8-20, def=3-12
danger越高属性按1+(level-1)*0.5倍率增长"""

        try:
            response = await self.ai.generate_response(
                system_prompt="你是修仙世界敌人生成助手，只返回JSON。",
                user_message=prompt
            )
            enemy_data = self._parse_json_response(response)
            if not enemy_data or "name_suffix" not in enemy_data:
                return None

            enemy_data["source"] = "ai_generated"
            enemy_id = self.db.add_enemy_template(enemy_data)
            enemy_data["id"] = enemy_id
            return enemy_data
        except Exception as e:
            print(f"AI生成敌人失败: {e}")
            return None

    async def generate_skill(
        self,
        realm: int = 1,
        skill_type: str = "attack",
        context: str = ""
    ) -> Optional[Dict[str, Any]]:
        """AI生成一个技能"""
        type_desc = {
            "attack": "攻击型技能",
            "defense": "防御/增益型技能",
            "recover": "恢复型技能",
        }

        prompt = f"""请为修仙世界游戏生成一个{type_desc.get(skill_type, '技能')}。

要求：
- 适合第{realm}境界修士使用
- 当前情境：{context or '普通修炼进程'}

请以严格的JSON格式返回（不要包含markdown代码块）：
{{
    "name": "技能名称（修仙风格）",
    "realm": {realm},
    "mp_cost": 灵力消耗,
    "damage": 伤害值(攻击型时),
    "defense": 防御加成(防御型时),
    "heal_hp": 恢复生命值(恢复型时),
    "heal_mp": 恢复灵力(恢复型时),
    "duration": 持续回合数(防御型时),
    "dodge": 闪避率(可选),
    "type": "{skill_type}",
    "description": "技能描述（20-40字）"
}}

属性参考（realm=1）：
- 攻击：damage=15-30, mp_cost=8-15
- 防御：defense=8-15, duration=2-3, mp_cost=6-12
- 恢复：heal_hp=30-60, mp_cost=5-10
每提高1个境界，数值约翻1.5-2倍"""

        try:
            response = await self.ai.generate_response(
                system_prompt="你是修仙世界技能生成助手，只返回JSON。",
                user_message=prompt
            )
            skill_data = self._parse_json_response(response)
            if not skill_data or "name" not in skill_data:
                return None

            skill_data["source"] = "ai_generated"
            skill_id = self.db.add_skill(skill_data)
            skill_data["id"] = skill_id
            return skill_data
        except Exception as e:
            print(f"AI生成技能失败: {e}")
            return None

    async def ensure_content_availability(
        self,
        realm_level: int = 1,
        context: str = ""
    ):
        """检查并确保有足够的动态内容可用，不够则自动生成"""
        stats = self.db.get_stats()

        # 确保至少有一定数量的物品
        if stats["items"] < 10:
            for item_type in ["consumable", "material", "skill_book"]:
                existing = self.db.get_all_items(item_type)
                if len(existing) < 3:
                    try:
                        await self.generate_item(item_type, realm_level, context)
                    except Exception:
                        pass

        # 确保有敌人模板
        if stats["enemies"] < 5:
            for dtype in ["妖兽", "灵兽", "魔修"]:
                try:
                    await self.generate_enemy_template(dtype, realm_level, context)
                except Exception:
                    pass

    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析AI返回的JSON，处理各种边界情况"""
        response = response.strip()

        # 移除可能的markdown代码块标记
        if response.startswith("```"):
            lines = response.split("\n")
            # 去掉第一行```json 和最后一行```
            if lines[-1].strip() == "```":
                lines = lines[:-1]
            if lines[0].startswith("```"):
                lines = lines[1:]
            response = "\n".join(lines)

        # 尝试找到JSON对象
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1 and end > start:
            response = response[start:end + 1]

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return None
