import random
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from core.cultivation import SKILL_LIBRARY, CultivationState

# 内置敌人模板（fallback）
BUILTIN_ENEMY_TEMPLATES = {
    "妖兽": {"name_prefix": "", "name_suffix": "妖兽", "base_hp": 50, "base_mp": 20, "base_atk": 12, "base_def": 5, "skills": ["爪击", "妖气弹"]},
    "灵兽": {"name_prefix": "", "name_suffix": "灵兽", "base_hp": 60, "base_mp": 30, "base_atk": 10, "base_def": 8, "skills": ["灵爪", "灵力冲击"]},
    "散修": {"name_prefix": "邪恶的", "name_suffix": "散修", "base_hp": 45, "base_mp": 35, "base_atk": 10, "base_def": 6, "skills": ["火球术", "灵气弹"]},
    "魔修": {"name_prefix": "堕落的", "name_suffix": "魔修", "base_hp": 55, "base_mp": 40, "base_atk": 15, "base_def": 4, "skills": ["魔气侵蚀", "血祭"]},
    "妖王": {"name_prefix": "远古", "name_suffix": "妖王", "base_hp": 200, "base_mp": 100, "base_atk": 40, "base_def": 20, "skills": ["妖王之怒", "吞噬", "妖气风暴"]},
    "守护者": {"name_prefix": "仙宫", "name_suffix": "守护者", "base_hp": 300, "base_mp": 150, "base_atk": 50, "base_def": 30, "skills": ["仙术·制裁", "天罡护体", "仙力净化"]},
}


@dataclass
class CombatEntity:
    """战斗实体"""
    name: str
    hp: int
    max_hp: int
    mp: int
    max_mp: int
    attack: int
    defense: int
    speed: int = 10
    skills: List[str] = field(default_factory=list)
    is_player: bool = False
    buffs: Dict[str, int] = field(default_factory=dict)  # buff_name: remaining_turns

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, damage: int) -> int:
        """承受伤害，返回实际伤害值"""
        actual_damage = max(1, damage - self.defense)
        # 检查防御buff
        if "defense_up" in self.buffs:
            actual_damage = int(actual_damage * 0.6)
        self.hp = max(0, self.hp - actual_damage)
        return actual_damage

    def heal(self, amount: int) -> int:
        """恢复生命，返回实际恢复量"""
        actual_heal = min(amount, self.max_hp - self.hp)
        self.hp += actual_heal
        return actual_heal

    def restore_mp(self, amount: int) -> int:
        """恢复灵力"""
        actual_restore = min(amount, self.max_mp - self.mp)
        self.mp += actual_restore
        return actual_restore

    def use_mp(self, cost: int) -> bool:
        """消耗灵力"""
        if self.mp >= cost:
            self.mp -= cost
            return True
        return False

    def tick_buffs(self):
        """减少buff回合数"""
        expired = []
        for buff_name, turns in self.buffs.items():
            self.buffs[buff_name] = turns - 1
            if self.buffs[buff_name] <= 0:
                expired.append(buff_name)
        for buff_name in expired:
            del self.buffs[buff_name]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "mp": self.mp,
            "max_mp": self.max_mp,
            "attack": self.attack,
            "defense": self.defense,
            "speed": self.speed,
            "skills": self.skills,
            "is_player": self.is_player,
            "buffs": self.buffs,
        }


class CombatSystem:
    """回合制战斗系统"""

    def __init__(self, db=None):
        self.active_combat: Optional[Dict[str, Any]] = None
        self.combat_log: List[str] = []
        self.db = db  # GameDatabase实例，可选

    def create_enemy(self, enemy_type: str, level: int = 1) -> CombatEntity:
        """根据类型和等级创建敌人 - 优先从DB获取，fallback到内置"""
        template = None

        # 从数据库查找AI生成的敌人模板
        if self.db:
            db_templates = self.db.get_enemy_templates(level)
            for t in db_templates:
                if t.get("type") == enemy_type:
                    template = t
                    break

        # fallback到内置模板
        if not template:
            template = BUILTIN_ENEMY_TEMPLATES.get(enemy_type, BUILTIN_ENEMY_TEMPLATES["妖兽"])

        multiplier = 1 + (level - 1) * 0.5

        # 从DB模板获取前缀，或随机选择
        db_prefix = template.get("name_prefix", "")
        name_prefixes = ["凶猛的", "狂暴的", "狡猾的", "远古的", "变异的", ""]
        prefix = db_prefix if db_prefix else random.choice(name_prefixes)

        skills = template.get("skills", ["爪击"])

        return CombatEntity(
            name=f"{prefix}{template.get('name_suffix', '怪物')}",
            hp=int(template.get("base_hp", 50) * multiplier),
            max_hp=int(template.get("base_hp", 50) * multiplier),
            mp=int(template.get("base_mp", 20) * multiplier),
            max_mp=int(template.get("base_mp", 20) * multiplier),
            attack=int(template.get("base_atk", 12) * multiplier),
            defense=int(template.get("base_def", 5) * multiplier),
            speed=random.randint(5, 15),
            skills=skills if isinstance(skills, list) else [],
        )

    def create_player_entity(self, player_stats: Dict[str, Any], cultivation: CultivationState) -> CombatEntity:
        """创建玩家战斗实体"""
        bonus = cultivation.get_stats_bonus()
        return CombatEntity(
            name=player_stats.get("player_name", "玩家"),
            hp=player_stats["stats"]["health"] + bonus["hp"],
            max_hp=player_stats["stats"]["health"] + bonus["hp"],
            mp=player_stats["stats"]["mana"] + bonus["mp"],
            max_mp=player_stats["stats"]["mana"] + bonus["mp"],
            attack=10 + bonus["atk"],
            defense=5 + bonus["def"],
            speed=10,
            skills=cultivation.skills.copy(),
            is_player=True,
        )

    def start_combat(self, player: CombatEntity, enemy: CombatEntity) -> Dict[str, Any]:
        """开始战斗"""
        self.active_combat = {
            "player": player,
            "enemy": enemy,
            "turn": 1,
            "turn_order": sorted([player, enemy], key=lambda e: e.speed, reverse=True),
            "status": "active",
        }
        self.combat_log = [f"⚔️ 战斗开始！{player.name} VS {enemy.name}"]

        return {
            "status": "combat_started",
            "player": player.to_dict(),
            "enemy": enemy.to_dict(),
            "log": self.combat_log.copy(),
            "turn": 1,
        }

    def execute_turn(self, action: str, skill_name: Optional[str] = None) -> Dict[str, Any]:
        """执行一回合战斗"""
        if not self.active_combat or self.active_combat["status"] != "active":
            return {"error": "没有进行中的战斗"}

        player = self.active_combat["player"]
        enemy = self.active_combat["enemy"]
        turn_log = []

        # 玩家行动
        player_action_result = self._execute_action(player, enemy, action, skill_name)
        turn_log.extend(player_action_result.get("log", []))

        # 检查战斗是否结束
        if not enemy.is_alive:
            return self._end_combat(player, enemy, True, turn_log)

        # 敌人行动
        enemy_action_result = self._enemy_turn(enemy, player)
        turn_log.extend(enemy_action_result.get("log", []))

        # 检查战斗是否结束
        if not player.is_alive:
            return self._end_combat(player, enemy, False, turn_log)

        # 更新buff
        player.tick_buffs()
        enemy.tick_buffs()

        self.active_combat["turn"] += 1
        self.combat_log.extend(turn_log)

        return {
            "status": "combat_continue",
            "player": player.to_dict(),
            "enemy": enemy.to_dict(),
            "log": turn_log,
            "turn": self.active_combat["turn"],
        }

    def _execute_action(
        self,
        attacker: CombatEntity,
        defender: CombatEntity,
        action: str,
        skill_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行一个行动"""
        log = []

        if action == "attack":
            # 普通攻击
            base_damage = attacker.attack + random.randint(-3, 5)
            if "attack_up" in attacker.buffs:
                base_damage = int(base_damage * 1.5)
            actual_damage = defender.take_damage(base_damage)
            log.append(f"🗡️ {attacker.name} 发起攻击，对 {defender.name} 造成 {actual_damage} 点伤害")

        elif action == "skill" and skill_name:
            # 合并内置 + 数据库技能库
            skill_lib = dict(SKILL_LIBRARY)
            if self.db:
                db_skills = self.db.get_all_skills()
                skill_lib.update(db_skills)
            if skill_name not in skill_lib:
                log.append(f"❌ {attacker.name} 不会使用 {skill_name}")
            elif skill_name not in attacker.skills and attacker.is_player:
                log.append(f"❌ {attacker.name} 尚未学会 {skill_name}")
            else:
                skill = skill_lib[skill_name]
                if not attacker.use_mp(skill["mp_cost"]):
                    log.append(f"❌ {attacker.name} 灵力不足，无法使用 {skill_name}")
                else:
                    if skill["type"] == "attack":
                        damage = skill["damage"] + random.randint(-10, 15)
                        if "attack_up" in attacker.buffs:
                            damage = int(damage * 1.5)
                        actual_damage = defender.take_damage(damage)
                        log.append(f"✨ {attacker.name} 使用【{skill_name}】，对 {defender.name} 造成 {actual_damage} 点伤害")
                    elif skill["type"] == "defense":
                        attacker.buffs["defense_up"] = skill.get("duration", 3)
                        log.append(f"🛡️ {attacker.name} 使用【{skill_name}】，防御力提升 {skill.get('duration', 3)} 回合")
                    elif skill["type"] == "recover":
                        if "heal_hp" in skill:
                            actual_heal = attacker.heal(skill["heal_hp"])
                            log.append(f"💚 {attacker.name} 使用【{skill_name}】，恢复 {actual_heal} 点生命")
                        if "heal_mp" in skill:
                            actual_restore = attacker.restore_mp(skill["heal_mp"])
                            log.append(f"💙 {attacker.name} 使用【{skill_name}】，恢复 {actual_restore} 点灵力")

        elif action == "defend":
            attacker.buffs["defense_up"] = 1
            log.append(f"🛡️ {attacker.name} 进行防御姿态")

        elif action == "flee":
            if random.random() < 0.4:
                log.append(f"🏃 {attacker.name} 成功逃跑了！")
                self.active_combat["status"] = "fled"
            else:
                log.append(f"❌ {attacker.name} 逃跑失败！")

        elif action == "use_item":
            # 使用道具
            actual_heal = attacker.heal(50)
            log.append(f"💊 {attacker.name} 使用丹药，恢复 {actual_heal} 点生命")

        return {"log": log}

    def _enemy_turn(self, enemy: CombatEntity, player: CombatEntity) -> Dict[str, Any]:
        """敌人AI行动"""
        log = []
        # 合并内置 + 数据库技能库
        skill_lib = dict(SKILL_LIBRARY)
        if self.db:
            db_skills = self.db.get_all_skills()
            skill_lib.update(db_skills)
        available_skills = [s for s in enemy.skills if s in skill_lib]

        # 简单AI：低血量时倾向于恢复或防御
        if enemy.hp < enemy.max_hp * 0.3:
            if available_skills and random.random() < 0.5:
                # 尝试使用技能
                skill_name = random.choice(available_skills)
                result = self._execute_action(enemy, player, "skill", skill_name)
                log.extend(result.get("log", []))
            else:
                result = self._execute_action(enemy, player, "defend")
                log.extend(result.get("log", []))
        else:
            # 正常情况下大部分攻击
            if available_skills and random.random() < 0.6:
                skill_name = random.choice(available_skills)
                result = self._execute_action(enemy, player, "skill", skill_name)
                log.extend(result.get("log", []))
            else:
                result = self._execute_action(enemy, player, "attack")
                log.extend(result.get("log", []))

        return {"log": log}

    def _end_combat(
        self,
        player: CombatEntity,
        enemy: CombatEntity,
        victory: bool,
        turn_log: List[str]
    ) -> Dict[str, Any]:
        """结束战斗"""
        if victory:
            self.active_combat["status"] = "victory"
            # 计算奖励
            exp_reward = random.randint(20, 50) + enemy.max_hp // 5
            gold_reward = random.randint(5, 20) + enemy.attack
            spirit_stones = random.randint(0, 5)

            turn_log.append(f"🎉 战斗胜利！{enemy.name} 被击败！")
            turn_log.append(f"📊 获得经验：{exp_reward}，金币：{gold_reward}，灵石：{spirit_stones}")

            # 随机掉落物品
            drops = []
            item_pool = ["回灵丹", "筑基丹", "灵石碎片", "妖兽材料", "灵草", "矿石"]
            num_drops = random.randint(0, 2)
            for _ in range(num_drops):
                drops.append(random.choice(item_pool))
            if drops:
                turn_log.append(f"🎁 掉落物品：{', '.join(drops)}")

            return {
                "status": "victory",
                "log": turn_log,
                "rewards": {
                    "experience": exp_reward,
                    "gold": gold_reward,
                    "spirit_stones": spirit_stones,
                    "items": drops,
                },
                "player": player.to_dict(),
            }
        else:
            self.active_combat["status"] = "defeat"
            turn_log.append(f"💀 战斗失败！{player.name} 被 {enemy.name} 击败...")
            turn_log.append("💫 你失去了一部分修为和灵石...")

            return {
                "status": "defeat",
                "log": turn_log,
                "penalty": {
                    "exp_lost": random.randint(10, 30),
                    "gold_lost": random.randint(5, 15),
                },
                "player": player.to_dict(),
            }

    def get_combat_status(self) -> Optional[Dict[str, Any]]:
        """获取当前战斗状态"""
        if not self.active_combat:
            return None
        return {
            "status": self.active_combat["status"],
            "turn": self.active_combat["turn"],
            "player": self.active_combat["player"].to_dict(),
            "enemy": self.active_combat["enemy"].to_dict(),
            "log": self.combat_log[-5:],  # 最近5条
        }

    def end_combat_cleanup(self):
        """清理战斗状态"""
        self.active_combat = None
        self.combat_log = []
