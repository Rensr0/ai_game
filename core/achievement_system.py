"""成就系统 - 跟踪玩家成就和里程碑"""
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime


# 成就定义
ACHIEVEMENTS = {
    # 境界成就
    "realm_qi_1": {
        "id": "realm_qi_1",
        "name": "初入仙途",
        "description": "达到炼气·1 层",
        "category": "realm",
        "condition": {"type": "realm", "realm_index": 0, "sub_level": 1},
        "reward": {"spirit_stones": 50, "exp": 100},
        "hidden": False,
    },
    "realm_zhuji": {
        "id": "realm_zhuji",
        "name": "筑基真人",
        "description": "达到筑基境界",
        "category": "realm",
        "condition": {"type": "realm", "realm_index": 1},
        "reward": {"spirit_stones": 200, "exp": 500},
        "hidden": False,
    },
    "realm_jindan": {
        "id": "realm_jindan",
        "name": "金丹大道",
        "description": "达到金丹境界",
        "category": "realm",
        "condition": {"type": "realm", "realm_index": 2},
        "reward": {"spirit_stones": 500, "exp": 1000},
        "hidden": False,
    },
    "realm_yuanying": {
        "id": "realm_yuanying",
        "name": "元婴老怪",
        "description": "达到元婴境界",
        "category": "realm",
        "condition": {"type": "realm", "realm_index": 3},
        "reward": {"spirit_stones": 1000, "exp": 2000},
        "hidden": False,
    },
    # 战斗成就
    "first_blood": {
        "id": "first_blood",
        "name": "初战告捷",
        "description": "赢得第一场战斗",
        "category": "combat",
        "condition": {"type": "combat_wins", "count": 1},
        "reward": {"spirit_stones": 30, "exp": 50},
        "hidden": False,
    },
    "combat_veteran": {
        "id": "combat_veteran",
        "name": "身经百战",
        "description": "赢得 50 场战斗",
        "category": "combat",
        "condition": {"type": "combat_wins", "count": 50},
        "reward": {"spirit_stones": 500, "exp": 1000, "item": "战斗徽章"},
        "hidden": False,
    },
    "slayer_beast": {
        "id": "slayer_beast",
        "name": "妖兽猎手",
        "description": "击败 10 只妖兽",
        "category": "combat",
        "condition": {"type": "enemy_kills", "enemy_type": "妖兽", "count": 10},
        "reward": {"spirit_stones": 200, "exp": 300},
        "hidden": False,
    },
    "slayer_demon": {
        "id": "slayer_demon",
        "name": "除魔卫道",
        "description": "击败 10 只魔修",
        "category": "combat",
        "condition": {"type": "enemy_kills", "enemy_type": "魔修", "count": 10},
        "reward": {"spirit_stones": 300, "exp": 500, "item": "降魔勋章"},
        "hidden": False,
    },
    # 收集成就
    "collector_common": {
        "id": "collector_common",
        "name": "收藏家·普通",
        "description": "收集 10 件普通品质物品",
        "category": "collection",
        "condition": {"type": "item_rarity_count", "rarity": "common", "count": 10},
        "reward": {"spirit_stones": 100},
        "hidden": False,
    },
    "collector_rare": {
        "id": "collector_rare",
        "name": "收藏家·稀有",
        "description": "收集 5 件稀有品质物品",
        "category": "collection",
        "condition": {"type": "item_rarity_count", "rarity": "rare", "count": 5},
        "reward": {"spirit_stones": 300, "item": "稀有宝箱"},
        "hidden": False,
    },
    "collector_legendary": {
        "id": "collector_legendary",
        "name": "传奇收藏",
        "description": "获得 1 件传说品质物品",
        "category": "collection",
        "condition": {"type": "item_rarity_count", "rarity": "legendary", "count": 1},
        "reward": {"spirit_stones": 1000, "item": "传奇宝箱"},
        "hidden": False,
    },
    # 社交成就
    "friend_first": {
        "id": "friend_first",
        "name": "初结善缘",
        "description": "与 NPC 关系达到友好 (50)",
        "category": "social",
        "condition": {"type": "npc_relationship", "score": 50},
        "reward": {"spirit_stones": 100, "exp": 200},
        "hidden": False,
    },
    "soulmate": {
        "id": "soulmate",
        "name": "知己好友",
        "description": "与 NPC 关系达到亲密 (100)",
        "category": "social",
        "condition": {"type": "npc_relationship", "score": 100},
        "reward": {"spirit_stones": 500, "item": "友谊之证"},
        "hidden": False,
    },
    # 隐藏成就
    "lucky_dog": {
        "id": "lucky_dog",
        "name": "？？？",
        "description": "???",
        "category": "secret",
        "condition": {"type": "lucky_event", "count": 5},
        "reward": {"spirit_stones": 888, "exp": 888},
        "hidden": True,
        "reveal_condition": "完成 5 次幸运事件",
    },
    "immortal": {
        "id": "immortal",
        "name": "？？？",
        "description": "???",
        "category": "secret",
        "condition": {"type": "realm", "realm_index": 7},
        "reward": {"spirit_stones": 9999, "exp": 9999, "item": "仙尊称号"},
        "hidden": True,
        "reveal_condition": "达到飞升境界",
    },
}


class AchievementSystem:
    """成就系统"""

    def __init__(self, save_file: str = "data/achievements.json"):
        self.save_file = save_file
        self.player_achievements: Dict[str, datetime] = {}  # 已解锁成就 {id: unlock_time}
        self.progress: Dict[str, Any] = {}  # 成就进度跟踪
        self.stats: Dict[str, Any] = {
            "combat_wins": 0,
            "enemy_kills": {},  # {enemy_type: count}
            "lucky_events": 0,
            "total_login_days": 0,
            "last_login": None,
        }
        self._load()

    def _load(self):
        """加载成就数据"""
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.player_achievements = {
                    k: datetime.fromisoformat(v)
                    for k, v in data.get("achievements", {}).items()
                }
                self.progress = data.get("progress", {})
                self.stats = data.get("stats", self.stats)
            except Exception as e:
                print(f"加载成就数据失败：{e}")

    def _save(self):
        """保存成就数据"""
        os.makedirs(os.path.dirname(self.save_file), exist_ok=True)
        data = {
            "achievements": {
                k: v.isoformat() for k, v in self.player_achievements.items()
            },
            "progress": self.progress,
            "stats": self.stats,
        }
        with open(self.save_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def update_stats(self, stat_type: str, **kwargs):
        """更新统计并检查成就"""
        unlocked = []

        if stat_type == "combat_win":
            self.stats["combat_wins"] += 1
            unlocked.extend(self._check_combat_achievements())

        elif stat_type == "enemy_kill":
            enemy_type = kwargs.get("enemy_type", "unknown")
            if enemy_type not in self.stats["enemy_kills"]:
                self.stats["enemy_kills"][enemy_type] = 0
            self.stats["enemy_kills"][enemy_type] += 1
            unlocked.extend(self._check_enemy_kill_achievements(enemy_type))

        elif stat_type == "realm":
            realm_index = kwargs.get("realm_index", 0)
            sub_level = kwargs.get("sub_level", 1)
            unlocked.extend(self._check_realm_achievements(realm_index, sub_level))

        elif stat_type == "npc_relationship":
            score = kwargs.get("score", 0)
            unlocked.extend(self._check_relationship_achievements(score))

        elif stat_type == "item_acquire":
            rarity = kwargs.get("rarity", "common")
            unlocked.extend(self._check_collection_achievements(rarity))

        elif stat_type == "lucky_event":
            self.stats["lucky_events"] += 1
            unlocked.extend(self._check_lucky_achievements())

        if unlocked:
            self._save()

        return unlocked

    def _check_combat_achievements(self) -> List[Dict[str, Any]]:
        """检查战斗成就"""
        unlocked = []
        wins = self.stats["combat_wins"]

        for ach_id, ach in ACHIEVEMENTS.items():
            if ach_id in self.player_achievements:
                continue
            cond = ach["condition"]
            if cond["type"] == "combat_wins" and wins >= cond["count"]:
                unlocked.append(self._unlock_achievement(ach_id))

        return unlocked

    def _check_enemy_kill_achievements(self, enemy_type: str) -> List[Dict[str, Any]]:
        """检查击杀成就"""
        unlocked = []
        kills = self.stats["enemy_kills"].get(enemy_type, 0)

        for ach_id, ach in ACHIEVEMENTS.items():
            if ach_id in self.player_achievements:
                continue
            cond = ach["condition"]
            if cond["type"] == "enemy_kills" and cond["enemy_type"] == enemy_type:
                if kills >= cond["count"]:
                    unlocked.append(self._unlock_achievement(ach_id))

        return unlocked

    def _check_realm_achievements(self, realm_index: int, sub_level: int) -> List[Dict[str, Any]]:
        """检查境界成就"""
        unlocked = []

        for ach_id, ach in ACHIEVEMENTS.items():
            if ach_id in self.player_achievements:
                continue
            cond = ach["condition"]
            if cond["type"] == "realm":
                if realm_index >= cond["realm_index"]:
                    if "sub_level" not in cond or sub_level >= cond["sub_level"]:
                        unlocked.append(self._unlock_achievement(ach_id))

        return unlocked

    def _check_relationship_achievements(self, score: int) -> List[Dict[str, Any]]:
        """检查关系成就"""
        unlocked = []

        for ach_id, ach in ACHIEVEMENTS.items():
            if ach_id in self.player_achievements:
                continue
            cond = ach["condition"]
            if cond["type"] == "npc_relationship" and score >= cond["score"]:
                unlocked.append(self._unlock_achievement(ach_id))

        return unlocked

    def _check_collection_achievements(self, rarity: str) -> List[Dict[str, Any]]:
        """检查收集成就（简化版，需要物品系统配合）"""
        # 实际实现需要查询玩家背包
        return []

    def _check_lucky_achievements(self) -> List[Dict[str, Any]]:
        """检查幸运成就"""
        unlocked = []
        lucky_count = self.stats["lucky_events"]

        for ach_id, ach in ACHIEVEMENTS.items():
            if ach_id in self.player_achievements:
                continue
            cond = ach["condition"]
            if cond["type"] == "lucky_event" and lucky_count >= cond["count"]:
                unlocked.append(self._unlock_achievement(ach_id))

        return unlocked

    def _unlock_achievement(self, ach_id: str) -> Dict[str, Any]:
        """解锁成就"""
        if ach_id not in ACHIEVEMENTS:
            return {"error": "Unknown achievement"}

        ach = ACHIEVEMENTS[ach_id]
        self.player_achievements[ach_id] = datetime.now()

        # 如果是隐藏成就，标记为已揭示
        if ach["hidden"]:
            ach = {**ach, "hidden": False, "name": ach.get("real_name", ach["name"])}

        return {
            "unlocked": True,
            "achievement": ach,
            "reward": ach["reward"],
            "message": f"🏆 解锁成就：{ach['name']}！奖励：{self._format_reward(ach['reward'])}",
        }

    def _format_reward(self, reward: Dict[str, Any]) -> str:
        """格式化奖励描述"""
        parts = []
        if "spirit_stones" in reward:
            parts.append(f"{reward['spirit_stones']}灵石")
        if "exp" in reward:
            parts.append(f"{reward['exp']}经验")
        if "item" in reward:
            parts.append(f"物品：{reward['item']}")
        return ", ".join(parts)

    def get_achievement(self, ach_id: str) -> Optional[Dict[str, Any]]:
        """获取成就详情"""
        return ACHIEVEMENTS.get(ach_id)

    def get_all_achievements(self) -> List[Dict[str, Any]]:
        """获取所有成就（隐藏成就显示 ???）"""
        result = []
        for ach_id, ach in ACHIEVEMENTS.items():
            ach_copy = ach.copy()
            if ach["hidden"] and ach_id not in self.player_achievements:
                ach_copy["name"] = "???"
                ach_copy["description"] = "???"
            ach_copy["unlocked"] = ach_id in self.player_achievements
            ach_copy["unlock_time"] = (
                self.player_achievements[ach_id].isoformat()
                if ach_id in self.player_achievements
                else None
            )
            result.append(ach_copy)
        return result

    def get_unlocked_achievements(self) -> List[Dict[str, Any]]:
        """获取已解锁成就"""
        return [
            {**ACHIEVEMENTS[ach_id], "unlock_time": t.isoformat()}
            for ach_id, t in self.player_achievements.items()
            if ach_id in ACHIEVEMENTS
        ]

    def get_progress(self) -> Dict[str, Any]:
        """获取成就进度"""
        total = len(ACHIEVEMENTS)
        unlocked = len(self.player_achievements)
        hidden_total = sum(1 for a in ACHIEVEMENTS.values() if a["hidden"])
        hidden_unlocked = sum(
            1 for ach_id in self.player_achievements
            if ach_id in ACHIEVEMENTS and ACHIEVEMENTS[ach_id]["hidden"]
        )

        return {
            "total": total,
            "unlocked": unlocked,
            "hidden_total": hidden_total,
            "hidden_unlocked": hidden_unlocked,
            "completion_rate": round(unlocked / total * 100, 1) if total > 0 else 0,
            "stats": self.stats,
        }

    def claim_reward(self, ach_id: str, game_state) -> Dict[str, Any]:
        """领取成就奖励（如果需要单独领取）"""
        if ach_id not in self.player_achievements:
            return {"error": "成就未解锁"}

        ach = ACHIEVEMENTS.get(ach_id)
        if not ach:
            return {"error": "未知成就"}

        reward = ach["reward"]
        result = {"claimed": True, "rewards": []}

        # 实际发放奖励需要游戏状态配合
        if "spirit_stones" in reward:
            result["rewards"].append(f"灵石 +{reward['spirit_stones']}")
        if "exp" in reward:
            result["rewards"].append(f"经验 +{reward['exp']}")
        if "item" in reward:
            result["rewards"].append(f"物品：{reward['item']}")

        return result
