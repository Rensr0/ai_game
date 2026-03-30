from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# 修仙境界
CULTIVATION_REALMS = [
    {"name": "炼气", "level": 1, "hp_bonus": 50, "mp_bonus": 30, "atk_bonus": 5, "def_bonus": 3, "description": "初窥修仙门径，引气入体"},
    {"name": "筑基", "level": 2, "hp_bonus": 120, "mp_bonus": 80, "atk_bonus": 15, "def_bonus": 10, "description": "凝聚灵力根基，脱胎换骨"},
    {"name": "金丹", "level": 3, "hp_bonus": 250, "mp_bonus": 180, "atk_bonus": 35, "def_bonus": 25, "description": "凝聚金丹，实力大增"},
    {"name": "元婴", "level": 4, "hp_bonus": 500, "mp_bonus": 350, "atk_bonus": 80, "def_bonus": 55, "description": "元婴出窍，神通初现"},
    {"name": "化神", "level": 5, "hp_bonus": 1000, "mp_bonus": 700, "atk_bonus": 180, "def_bonus": 120, "description": "化神通为己用，天地共鸣"},
    {"name": "渡劫", "level": 6, "hp_bonus": 2000, "mp_bonus": 1500, "atk_bonus": 400, "def_bonus": 280, "description": "渡过天劫，超凡入圣"},
    {"name": "大乘", "level": 7, "hp_bonus": 5000, "mp_bonus": 3500, "atk_bonus": 1000, "def_bonus": 700, "description": "大乘圆满，距飞升一步之遥"},
    {"name": "飞升", "level": 8, "hp_bonus": 10000, "mp_bonus": 7000, "atk_bonus": 2500, "def_bonus": 1800, "description": "飞升仙界，长生不死"},
]

# 技能库
SKILL_LIBRARY = {
    # 炼气期技能
    "火球术": {"realm": 1, "mp_cost": 10, "damage": 20, "type": "attack", "description": "凝聚火灵力，释放一枚火球"},
    "护体灵光": {"realm": 1, "mp_cost": 8, "defense": 10, "duration": 3, "type": "defense", "description": "以灵力护体，增强防御"},
    "灵气弹": {"realm": 1, "mp_cost": 12, "damage": 25, "type": "attack", "description": "凝聚灵力弹射向敌人"},
    # 筑基期技能
    "三昧真火": {"realm": 2, "mp_cost": 25, "damage": 55, "type": "attack", "description": "释放三昧真火，灼烧一切"},
    "金钟罩": {"realm": 2, "mp_cost": 20, "defense": 30, "duration": 3, "type": "defense", "description": "凝聚金钟罩，刀枪不入"},
    "灵力恢复": {"realm": 2, "mp_cost": 0, "heal_mp": 40, "type": "recover", "description": "运功恢复灵力"},
    # 金丹期技能
    "雷法·天雷引": {"realm": 3, "mp_cost": 50, "damage": 120, "type": "attack", "description": "引动天雷之力，轰杀敌人"},
    "五行遁术": {"realm": 3, "mp_cost": 35, "dodge": 50, "duration": 2, "type": "defense", "description": "五行遁术，闪避攻击"},
    "丹药炼制": {"realm": 3, "mp_cost": 30, "heal_hp": 150, "type": "recover", "description": "现场炼制丹药恢复生命"},
    # 元婴期技能
    "元婴出窍": {"realm": 4, "mp_cost": 80, "damage": 280, "type": "attack", "description": "元婴出窍，神识攻击敌人"},
    "天地无极": {"realm": 4, "mp_cost": 60, "defense": 80, "duration": 3, "type": "defense", "description": "天地无极，万法不侵"},
    "生生不息": {"realm": 4, "mp_cost": 50, "heal_hp": 400, "type": "recover", "description": "生生不息之力，大量恢复生命"},
    # 化神期技能
    "天崩地裂": {"realm": 5, "mp_cost": 150, "damage": 600, "type": "attack", "description": "天崩地裂，毁灭性的攻击"},
    "万法归宗": {"realm": 5, "mp_cost": 100, "defense": 200, "duration": 3, "type": "defense", "description": "万法归宗，一切攻击化为虚无"},
    "造化之力": {"realm": 5, "mp_cost": 120, "heal_hp": 1000, "type": "recover", "description": "造化之力，近乎起死回生"},
    # 渡劫期技能
    "天劫之雷": {"realm": 6, "mp_cost": 300, "damage": 1500, "type": "attack", "description": "引动天劫之雷，灭杀万物"},
    "劫云护体": {"realm": 6, "mp_cost": 200, "defense": 500, "duration": 3, "type": "defense", "description": "劫云护体，天劫之力守护"},
    # 大乘期技能
    "天地同寿": {"realm": 7, "mp_cost": 500, "damage": 4000, "type": "attack", "description": "天地同寿，一击惊天"},
    "万物归元": {"realm": 7, "mp_cost": 400, "heal_hp": 5000, "type": "recover", "description": "万物归元，完全恢复"},
}

# 地图区域
MAP_REGIONS = {
    "起始村庄": {
        "description": "一个宁静的修仙者聚集小村，四周灵气稀薄但适合初学者修炼",
        "connections": ["青云森林", "灵石矿洞"],
        "npc_types": ["散修", "宗门弟子", "农夫", "炼丹师"],
        "danger_level": 1,
        "resources": ["灵草", "矿石"],
    },
    "青云森林": {
        "description": "茂密的灵木森林，据说深处藏有灵兽和天材地宝",
        "connections": ["起始村庄", "仙灵城", "毒龙潭"],
        "npc_types": ["猎人", "隐士", "游侠"],
        "danger_level": 3,
        "resources": ["灵木", "灵兽内丹", "灵草"],
    },
    "灵石矿洞": {
        "description": "蕴含丰富灵石的矿洞，但也盘踞着危险的妖兽",
        "connections": ["起始村庄", "地底暗河"],
        "npc_types": ["矿工", "散修"],
        "danger_level": 2,
        "resources": ["灵石", "矿石", "稀有矿材"],
    },
    "仙灵城": {
        "description": "繁华的修仙大城，商铺林立，各大宗门在此设有分支",
        "connections": ["青云森林", "天剑峰", "东海之滨"],
        "npc_types": ["商贾", "守卫", "仙师", "阵法师", "刺客"],
        "danger_level": 2,
        "resources": ["丹药", "法宝", "功法秘籍"],
    },
    "天剑峰": {
        "description": "险峻的剑修圣地，峰顶常年有剑气纵横",
        "connections": ["仙灵城", "云顶仙宫"],
        "npc_types": ["剑修", "隐世高手"],
        "danger_level": 5,
        "resources": ["剑诀", "灵铁", "剑意碎片"],
    },
    "毒龙潭": {
        "description": "阴森的毒潭，据说有上古毒龙的后裔潜伏其中",
        "connections": ["青云森林", "万妖谷"],
        "npc_types": ["毒修", "妖兽"],
        "danger_level": 4,
        "resources": ["毒草", "龙鳞", "毒丹"],
    },
    "东海之滨": {
        "description": "浩瀚的东海，蕴含无尽的秘密和宝藏",
        "connections": ["仙灵城", "蓬莱仙岛"],
        "npc_types": ["渔夫", "修士", "海盗", "商贾"],
        "danger_level": 3,
        "resources": ["灵珠", "海兽内丹", "珊瑚"],
    },
    "万妖谷": {
        "description": "万妖聚集之地，危险重重但天材地宝无数",
        "connections": ["毒龙潭", "云顶仙宫"],
        "npc_types": ["妖王", "妖兽", "猎妖师"],
        "danger_level": 6,
        "resources": ["妖丹", "妖兽材料", "灵草"],
    },
    "云顶仙宫": {
        "description": "传说中的仙人遗迹，蕴含飞升之秘",
        "connections": ["天剑峰", "万妖谷"],
        "npc_types": ["仙人残影", "守护者"],
        "danger_level": 7,
        "resources": ["仙器碎片", "仙法残卷", "仙灵之气"],
    },
    "地底暗河": {
        "description": "幽暗的地下河流，深处隐藏着远古的秘密",
        "connections": ["灵石矿洞"],
        "npc_types": ["地底生物", "矿工"],
        "danger_level": 4,
        "resources": ["暗灵石", "地心炎", "远古遗物"],
    },
    "蓬莱仙岛": {
        "description": "海外仙岛，灵气浓郁，是修仙者梦寐以求的修炼圣地",
        "connections": ["东海之滨"],
        "npc_types": ["仙人", "散仙"],
        "danger_level": 5,
        "resources": ["仙果", "仙草", "仙气结晶"],
    },
}


@dataclass
class CultivationState:
    """修仙状态"""
    realm_index: int = 0  # 境界索引
    sub_level: int = 1  # 境界内小等级(1-9)
    experience: int = 0  # 修炼经验
    exp_to_next: int = 100  # 升级所需经验
    spirit_stones: int = 0  # 灵石
    skills: List[str] = field(default_factory=list)  # 已学技能
    active_buffs: Dict[str, int] = field(default_factory=dict)  # 活跃增益效果
    _db = None  # GameDatabase实例，可选

    def set_db(self, db):
        """设置数据库引用"""
        self._db = db

    def _get_skill_library(self) -> Dict[str, Any]:
        """获取技能库 - 优先数据库，无数据时使用内置"""
        if self._db:
            db_skills = self._db.get_all_skills()
            if db_skills:
                return db_skills
        # 数据库为空时返回内置技能库作为 fallback
        return dict(SKILL_LIBRARY)

    def get_all_regions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有地图区域 - 优先数据库，无数据时使用内置"""
        if self._db:
            db_regions = self._db.get_all_regions()
            if db_regions:
                return db_regions
        # 数据库为空时返回内置地图作为 fallback
        return dict(MAP_REGIONS)

    @property
    def realm_name(self) -> str:
        return CULTIVATION_REALMS[self.realm_index]["name"]

    @property
    def full_realm(self) -> str:
        return f"{self.realm_name}·{self.sub_level}层"

    @property
    def realm_data(self) -> Dict[str, Any]:
        return CULTIVATION_REALMS[self.realm_index]

    def get_stats_bonus(self) -> Dict[str, int]:
        """获取当前境界的属性加成"""
        data = self.realm_data
        multiplier = 1 + (self.sub_level - 1) * 0.1
        return {
            "hp": int(data["hp_bonus"] * multiplier),
            "mp": int(data["mp_bonus"] * multiplier),
            "atk": int(data["atk_bonus"] * multiplier),
            "def": int(data["def_bonus"] * multiplier),
        }

    def get_available_skills(self) -> List[Dict[str, Any]]:
        """获取当前可学习的技能（合并内置+数据库）"""
        skill_lib = self._get_skill_library()
        available = []
        for skill_name, skill_data in skill_lib.items():
            if skill_data.get("realm", 1) <= self.realm_index + 1:
                entry = {"name": skill_name}
                entry.update(skill_data)
                available.append(entry)
        return available

    def can_learn_skill(self, skill_name: str) -> bool:
        if skill_name in self.skills:
            return False
        skill_lib = self._get_skill_library()
        if skill_name not in skill_lib:
            return False
        return skill_lib[skill_name].get("realm", 1) <= self.realm_index + 1

    def learn_skill(self, skill_name: str) -> bool:
        if self.can_learn_skill(skill_name):
            self.skills.append(skill_name)
            return True
        return False

    def add_experience(self, amount: int) -> Dict[str, Any]:
        """添加修炼经验，检查是否升级"""
        self.experience += amount
        result = {"exp_gained": amount, "leveled_up": False, "breakthrough": False}

        while self.experience >= self.exp_to_next:
            self.experience -= self.exp_to_next
            result["leveled_up"] = True

            if self.sub_level < 9:
                self.sub_level += 1
            elif self.realm_index < len(CULTIVATION_REALMS) - 1:
                # 突破境界
                self.realm_index += 1
                self.sub_level = 1
                result["breakthrough"] = True
                result["new_realm"] = self.realm_name

            # 每级经验需求递增
            self.exp_to_next = int(100 * (1.5 ** (self.realm_index * 3 + self.sub_level)))

        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "realm_index": self.realm_index,
            "sub_level": self.sub_level,
            "realm_name": self.full_realm,
            "experience": self.experience,
            "exp_to_next": self.exp_to_next,
            "spirit_stones": self.spirit_stones,
            "skills": self.skills,
            "active_buffs": self.active_buffs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CultivationState':
        state = cls()
        state.realm_index = data.get("realm_index", 0)
        state.sub_level = data.get("sub_level", 1)
        state.experience = data.get("experience", 0)
        state.exp_to_next = data.get("exp_to_next", 100)
        state.spirit_stones = data.get("spirit_stones", 0)
        state.skills = data.get("skills", [])
        state.active_buffs = data.get("active_buffs", {})
        return state
