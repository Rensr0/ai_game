"""物品系统 - 整合硬编码数据和AI动态生成数据"""
import random
from typing import Dict, Any, List, Optional

# 内置默认物品数据（fallback）
ITEM_DATABASE = {
    # 消耗品 - 丹药
    "回灵丹": {"type": "consumable", "subtype": "pill", "effect": {"heal_hp": 50}, "description": "基础恢复丹药，恢复50点生命", "price": 10, "rarity": "common"},
    "大回灵丹": {"type": "consumable", "subtype": "pill", "effect": {"heal_hp": 150}, "description": "高级恢复丹药，恢复150点生命", "price": 50, "rarity": "uncommon"},
    "聚灵丹": {"type": "consumable", "subtype": "pill", "effect": {"heal_mp": 40}, "description": "恢复灵力的丹药", "price": 15, "rarity": "common"},
    "筑基丹": {"type": "consumable", "subtype": "pill", "effect": {"exp_boost": 1.5, "duration": 300}, "description": "服用后300秒内获得额外50%修炼经验", "price": 100, "rarity": "rare"},
    "破境丹": {"type": "consumable", "subtype": "pill", "effect": {"breakthrough_bonus": 20}, "description": "突破境界时使用，增加20%成功率", "price": 500, "rarity": "epic"},
    "天劫护体丹": {"type": "consumable", "subtype": "pill", "effect": {"reduce_damage": 30, "duration": 180}, "description": "渡劫时服用，减少30%受到的伤害", "price": 1000, "rarity": "legendary"},
    # 消耗品 - 材料
    "灵石碎片": {"type": "material", "subtype": "spirit_stone", "effect": {"spirit_stones": 5}, "description": "蕴含灵力的石碎片", "price": 5, "rarity": "common"},
    "灵石": {"type": "material", "subtype": "spirit_stone", "effect": {"spirit_stones": 20}, "description": "标准灵石，修仙界通用货币", "price": 20, "rarity": "uncommon"},
    "上品灵石": {"type": "material", "subtype": "spirit_stone", "effect": {"spirit_stones": 100}, "description": "高品质灵石，蕴含浓郁灵力", "price": 100, "rarity": "rare"},
    "妖兽内丹": {"type": "material", "subtype": "crafting", "effect": {}, "description": "妖兽体内的灵核，可用于炼丹或炼器", "price": 30, "rarity": "uncommon"},
    "灵草": {"type": "material", "subtype": "herb", "effect": {}, "description": "常见的灵草，炼丹材料", "price": 8, "rarity": "common"},
    "矿石": {"type": "material", "subtype": "ore", "effect": {}, "description": "含有灵力的矿石", "price": 12, "rarity": "common"},
    "灵木": {"type": "material", "subtype": "wood", "effect": {}, "description": "蕴含灵力的木材", "price": 15, "rarity": "common"},
    "妖兽材料": {"type": "material", "subtype": "crafting", "effect": {}, "description": "妖兽身上的珍贵材料", "price": 25, "rarity": "uncommon"},
    "灵兽内丹": {"type": "material", "subtype": "crafting", "effect": {"exp_gain": 30}, "description": "灵兽体内的灵核，服用可获得30点经验", "price": 50, "rarity": "rare"},
    # 装备
    "铁剑": {"type": "equipment", "subtype": "weapon", "effect": {"attack": 5}, "description": "普通的铁剑", "price": 30, "rarity": "common"},
    "灵铁剑": {"type": "equipment", "subtype": "weapon", "effect": {"attack": 15}, "description": "以灵铁铸造的剑，锋利无比", "price": 150, "rarity": "uncommon"},
    "仙剑·青霜": {"type": "equipment", "subtype": "weapon", "effect": {"attack": 50, "speed": 5}, "description": "传世仙剑，蕴含霜寒之力", "price": 2000, "rarity": "epic"},
    "布衣": {"type": "equipment", "subtype": "armor", "effect": {"defense": 3}, "description": "普通的布衣", "price": 15, "rarity": "common"},
    "灵甲": {"type": "equipment", "subtype": "armor", "effect": {"defense": 12}, "description": "以灵力加持的护甲", "price": 120, "rarity": "uncommon"},
    "金蚕丝甲": {"type": "equipment", "subtype": "armor", "effect": {"defense": 40, "hp": 100}, "description": "金蚕丝编织的宝甲，轻盈坚韧", "price": 1500, "rarity": "epic"},
    # 功法秘籍
    "基础功法": {"type": "skill_book", "subtype": "manual", "effect": {"skill": "火球术"}, "description": "修仙入门功法，学会火球术", "price": 50, "rarity": "common"},
    "三昧真火诀": {"type": "skill_book", "subtype": "manual", "effect": {"skill": "三昧真火"}, "description": "记载三昧真火修炼法门的秘籍", "price": 300, "rarity": "rare"},
    "雷法秘典": {"type": "skill_book", "subtype": "manual", "effect": {"skill": "雷法·天雷引"}, "description": "天雷宗的不传之秘", "price": 800, "rarity": "epic"},
    "剑诀·万剑归宗": {"type": "skill_book", "subtype": "manual", "effect": {"skill": "天地无极"}, "description": "天剑峰的镇峰剑诀", "price": 2000, "rarity": "legendary"},
}

ITEM_RARITY_COLORS = {
    "common": "#9ca3af",
    "uncommon": "#22c55e",
    "rare": "#3b82f6",
    "epic": "#a855f7",
    "legendary": "#f59e0b",
}

ITEM_RARITY_NAMES = {
    "common": "普通",
    "uncommon": "优秀",
    "rare": "稀有",
    "epic": "史诗",
    "legendary": "传说",
}


class ItemSystem:
    """物品系统 - 支持内置数据 + 数据库动态数据"""

    def __init__(self, db=None):
        self.db = db  # GameDatabase实例，可选

    def get_item_info(self, item_name: str) -> Optional[Dict[str, Any]]:
        """获取物品信息 - 优先查数据库，fallback到内置"""
        # 先查数据库（AI生成的物品）
        if self.db:
            db_item = self.db.get_item(item_name)
            if db_item:
                return db_item
        # fallback到内置数据
        return ITEM_DATABASE.get(item_name)

    def use_item(self, item_name: str, player_stats: Dict[str, Any]) -> Dict[str, Any]:
        """使用物品"""
        item = self.get_item_info(item_name)
        if not item:
            return {"error": f"未知物品：{item_name}"}

        result = {"item_used": item_name, "effects": []}

        if item["type"] == "consumable":
            effect = item.get("effect", {})
            # 从 total_stats 获取实际最大值（含境界和装备加成）
            total = player_stats.get("total_stats", player_stats.get("stats", {}))
            max_hp = total.get("health", player_stats["stats"].get("health", 100))
            max_mp = total.get("mana", player_stats["stats"].get("mana", 50))
            if "heal_hp" in effect:
                healed = min(effect["heal_hp"], max_hp - player_stats["stats"]["health"])
                player_stats["stats"]["health"] += healed
                result["effects"].append(f"恢复 {healed} 点生命")
            if "heal_mp" in effect:
                restored = min(effect["heal_mp"], max_mp - player_stats["stats"]["mana"])
                player_stats["stats"]["mana"] += restored
                result["effects"].append(f"恢复 {restored} 点灵力")
            if "exp_boost" in effect:
                result["effects"].append(f"获得经验加成 {effect['exp_boost']}x 持续 {effect.get('duration', 300)} 秒")

        elif item["type"] == "material" and "spirit_stones" in item.get("effect", {}):
            amount = item["effect"]["spirit_stones"]
            result["effects"].append(f"获得 {amount} 灵石")
            result["spirit_stones_gained"] = amount

        elif item["type"] == "material" and "exp_gain" in item.get("effect", {}):
            amount = item["effect"]["exp_gain"]
            result["effects"].append(f"获得 {amount} 点经验")
            result["exp_gained"] = amount

        elif item["type"] == "skill_book":
            skill = item.get("effect", {}).get("skill")
            if skill:
                result["effects"].append(f"学会技能：{skill}")
                result["skill_learned"] = skill

        elif item["type"] == "equipment":
            for stat, value in item.get("effect", {}).items():
                result["effects"].append(f"{stat} +{value}")
            result["equipped"] = item_name

        return result

    def get_shop_items(self, realm_level: int = 1) -> List[Dict[str, Any]]:
        """获取商店物品列表 - 不包含装备，结合DB和内置数据"""
        shop = []

        # 从数据库获取（AI生成的物品）
        if self.db:
            db_items = self.db.get_shop_items(realm_level)
            for item in db_items:
                shop.append(item)

        # 从内置数据获取（不包含装备）
        for name, data in ITEM_DATABASE.items():
            if data["type"] in ["consumable", "material", "skill_book"]:
                shop.append({"name": name, **data})

        return shop

    def get_item_color(self, item_name: str) -> str:
        """获取物品品质颜色"""
        item = self.get_item_info(item_name)
        if item:
            return ITEM_RARITY_COLORS.get(item.get("rarity", "common"), "#9ca3af")
        return "#9ca3af"

    def get_item_rarity_name(self, item_name: str) -> str:
        """获取物品品质名称"""
        item = self.get_item_info(item_name)
        if item:
            return ITEM_RARITY_NAMES.get(item.get("rarity", "common"), "普通")
        return "普通"

    def generate_random_drop(self, danger_level: int = 1) -> List[str]:
        """根据危险等级生成随机掉落"""
        drops = []
        num_drops = random.randint(0, min(3, danger_level))

        rarity_weights = {
            "common": 50,
            "uncommon": 30,
            "rare": 15 if danger_level >= 3 else 5,
            "epic": 5 if danger_level >= 5 else 0,
            "legendary": 1 if danger_level >= 7 else 0,
        }

        eligible_items = []
        # 从内置数据
        for name, data in ITEM_DATABASE.items():
            weight = rarity_weights.get(data["rarity"], 0)
            if weight > 0:
                eligible_items.extend([name] * weight)

        # 从数据库
        if self.db:
            db_items = self.db.get_all_items()
            for item in db_items:
                weight = rarity_weights.get(item.get("rarity", "common"), 0)
                if weight > 0:
                    eligible_items.extend([item["name"]] * weight)

        if eligible_items:
            for _ in range(num_drops):
                drops.append(random.choice(eligible_items))

        return drops
