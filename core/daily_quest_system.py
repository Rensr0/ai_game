"""每日任务系统 - 提供每日挑战和奖励"""
import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


# 任务池定义
DAILY_QUESTS = {
    "cultivation": [
        {
            "id": "daily_cult_1",
            "name": "静心修炼",
            "description": "打坐修炼 3 次",
            "type": "meditate",
            "target": 3,
            "reward": {"exp": 100, "spirit_stones": 50},
            "difficulty": "easy",
        },
        {
            "id": "daily_cult_2",
            "name": "突破自我",
            "description": "获得 500 点修炼经验",
            "type": "gain_exp",
            "target": 500,
            "reward": {"exp": 200, "spirit_stones": 100},
            "difficulty": "medium",
        },
        {
            "id": "daily_cult_3",
            "name": "潜心修行",
            "description": "打坐修炼 5 次",
            "type": "meditate",
            "target": 5,
            "reward": {"exp": 300, "spirit_stones": 150},
            "difficulty": "hard",
        },
    ],
    "combat": [
        {
            "id": "daily_combat_1",
            "name": "初露锋芒",
            "description": "赢得 3 场战斗",
            "type": "combat_win",
            "target": 3,
            "reward": {"exp": 150, "spirit_stones": 80},
            "difficulty": "easy",
        },
        {
            "id": "daily_combat_2",
            "name": "斩妖除魔",
            "description": "击败 5 只妖兽",
            "type": "kill_enemy",
            "enemy_type": "妖兽",
            "target": 5,
            "reward": {"exp": 250, "spirit_stones": 120},
            "difficulty": "medium",
        },
        {
            "id": "daily_combat_3",
            "name": "身经百战",
            "description": "赢得 10 场战斗",
            "type": "combat_win",
            "target": 10,
            "reward": {"exp": 500, "spirit_stones": 250},
            "difficulty": "hard",
        },
        {
            "id": "daily_combat_4",
            "name": "除魔卫道",
            "description": "击败 3 只魔修",
            "type": "kill_enemy",
            "enemy_type": "魔修",
            "target": 3,
            "reward": {"exp": 300, "spirit_stones": 150},
            "difficulty": "medium",
        },
    ],
    "exploration": [
        {
            "id": "daily_explore_1",
            "name": "云游四方",
            "description": "访问 3 个不同地点",
            "type": "visit_location",
            "target": 3,
            "reward": {"exp": 100, "spirit_stones": 60},
            "difficulty": "easy",
        },
        {
            "id": "daily_explore_2",
            "name": "探索秘境",
            "description": "访问 5 个不同地点",
            "type": "visit_location",
            "target": 5,
            "reward": {"exp": 200, "spirit_stones": 100},
            "difficulty": "medium",
        },
        {
            "id": "daily_explore_3",
            "name": "踏遍山河",
            "description": "访问 10 个不同地点",
            "type": "visit_location",
            "target": 10,
            "reward": {"exp": 400, "spirit_stones": 200},
            "difficulty": "hard",
        },
    ],
    "social": [
        {
            "id": "daily_social_1",
            "name": "广结善缘",
            "description": "与 2 个 NPC 对话",
            "type": "talk_to_npc",
            "target": 2,
            "reward": {"exp": 80, "spirit_stones": 40},
            "difficulty": "easy",
        },
        {
            "id": "daily_social_2",
            "name": "深交好友",
            "description": "与 NPC 关系提升 20 点",
            "type": "increase_relationship",
            "target": 20,
            "reward": {"exp": 150, "spirit_stones": 80},
            "difficulty": "medium",
        },
    ],
    "collection": [
        {
            "id": "daily_collect_1",
            "name": "小试身手",
            "description": "获得 3 件物品",
            "type": "acquire_item",
            "target": 3,
            "reward": {"exp": 100, "spirit_stones": 50},
            "difficulty": "easy",
        },
        {
            "id": "daily_collect_2",
            "name": "收藏爱好者",
            "description": "获得 10 件物品",
            "type": "acquire_item",
            "target": 10,
            "reward": {"exp": 200, "spirit_stones": 100},
            "difficulty": "medium",
        },
    ],
}


class DailyQuestSystem:
    """每日任务系统"""

    def __init__(self, save_file: str = "data/daily_quests.json"):
        self.save_file = save_file
        self.active_quests: List[Dict[str, Any]] = []  # 当前活跃任务
        self.quest_progress: Dict[str, int] = {}  # 任务进度 {quest_id: progress}
        self.completed_today: List[str] = []  # 今日已完成任务 ID
        self.last_reset: Optional[str] = None  # 上次重置时间
        self.streak: int = 0  # 连续登录天数
        self._load()
        self._check_reset()

    def _load(self):
        """加载任务数据"""
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.active_quests = data.get("active_quests", [])
                self.quest_progress = data.get("progress", {})
                self.completed_today = data.get("completed_today", [])
                self.last_reset = data.get("last_reset")
                self.streak = data.get("streak", 0)
            except Exception as e:
                print(f"加载任务数据失败：{e}")

    def _save(self):
        """保存任务数据"""
        os.makedirs(os.path.dirname(self.save_file), exist_ok=True)
        data = {
            "active_quests": self.active_quests,
            "progress": self.quest_progress,
            "completed_today": self.completed_today,
            "last_reset": self.last_reset,
            "streak": self.streak,
        }
        with open(self.save_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _check_reset(self):
        """检查是否需要重置每日任务"""
        today = datetime.now().strftime("%Y-%m-%d")

        if self.last_reset != today:
            # 新的一天，重置任务
            if self.last_reset:
                # 检查是否连续登录
                last_date = datetime.strptime(self.last_reset, "%Y-%m-%d")
                if (datetime.now() - last_date).days == 1:
                    self.streak += 1
                else:
                    self.streak = 1
            else:
                self.streak = 1

            self._reset_daily_quests()
            self.last_reset = today
            self._save()

    def _reset_daily_quests(self):
        """重置每日任务"""
        self.active_quests = self._generate_daily_quests()
        self.quest_progress = {}
        self.completed_today = []

        print(f"📋 每日任务已刷新！连续登录：{self.streak}天")

    def _generate_daily_quests(self) -> List[Dict[str, Any]]:
        """生成每日任务（每个类别选 1-2 个）"""
        selected = []

        # 从每个类别中随机选择任务
        categories = ["cultivation", "combat", "exploration", "social", "collection"]

        for category in categories:
            quests = DAILY_QUESTS.get(category, [])
            if not quests:
                continue

            # 根据难度权重选择
            easy_quests = [q for q in quests if q["difficulty"] == "easy"]
            medium_quests = [q for q in quests if q["difficulty"] == "medium"]
            hard_quests = [q for q in quests if q["difficulty"] == "hard"]

            # 至少选一个简单或中等难度的
            if easy_quests or medium_quests:
                pool = easy_quests + medium_quests
                selected_quest = random.choice(pool)
                selected.append({
                    **selected_quest,
                    "category": category,
                    "progress": 0,
                    "completed": False,
                })

            # 30% 概率额外选一个困难任务
            if hard_quests and random.random() < 0.3:
                selected_quest = random.choice(hard_quests)
                selected.append({
                    **selected_quest,
                    "category": category,
                    "progress": 0,
                    "completed": False,
                })

        # 确保至少有 3 个任务
        while len(selected) < 3:
            category = random.choice(categories)
            quests = DAILY_QUESTS.get(category, [])
            if quests:
                quest = random.choice(quests)
                if not any(q["id"] == quest["id"] for q in selected):
                    selected.append({
                        **quest,
                        "category": category,
                        "progress": 0,
                        "completed": False,
                    })

        return selected

    def update_progress(self, quest_type: str, **kwargs) -> List[Dict[str, Any]]:
        """更新任务进度"""
        completed_quests = []

        for quest in self.active_quests:
            if quest["completed"] or quest["id"] in self.completed_today:
                continue

            if quest["type"] == quest_type:
                increment = kwargs.get("increment", 1)

                # 检查特定条件
                if "enemy_type" in quest and kwargs.get("enemy_type"):
                    if quest["enemy_type"] != kwargs["enemy_type"]:
                        continue

                # 更新进度
                current = self.quest_progress.get(quest["id"], 0)
                new_progress = min(current + increment, quest["target"])
                self.quest_progress[quest["id"]] = new_progress
                quest["progress"] = new_progress

                # 检查是否完成
                if new_progress >= quest["target"]:
                    quest["completed"] = True
                    self.completed_today.append(quest["id"])
                    completed_quests.append(quest)

        if completed_quests:
            self._save()

        return completed_quests

    def get_active_quests(self) -> List[Dict[str, Any]]:
        """获取当前活跃任务"""
        return self.active_quests

    def get_quest_progress(self, quest_id: str) -> Dict[str, Any]:
        """获取单个任务进度"""
        quest = next((q for q in self.active_quests if q["id"] == quest_id), None)
        if not quest:
            return {"error": "Quest not found"}

        return {
            "quest": quest,
            "progress": self.quest_progress.get(quest_id, 0),
            "completed": quest["completed"],
        }

    def claim_reward(self, quest_id: str, game_state=None) -> Dict[str, Any]:
        """领取任务奖励"""
        quest = next((q for q in self.active_quests if q["id"] == quest_id), None)

        if not quest:
            return {"error": "任务不存在"}

        if not quest["completed"]:
            return {"error": "任务未完成"}

        if quest_id in self.completed_today:
            return {"error": "奖励已领取"}

        # 发放奖励
        reward = quest["reward"]
        result = {
            "claimed": True,
            "quest_name": quest["name"],
            "rewards": [],
        }

        if "exp" in reward:
            result["rewards"].append(f"经验 +{reward['exp']}")
        if "spirit_stones" in reward:
            result["rewards"].append(f"灵石 +{reward['spirit_stones']}")

        # 标记为已领取
        self.completed_today.append(quest_id)
        self._save()

        return result

    def get_summary(self) -> Dict[str, Any]:
        """获取任务摘要"""
        total = len(self.active_quests)
        completed = sum(1 for q in self.active_quests if q["completed"])

        return {
            "total": total,
            "completed": completed,
            "progress": f"{completed}/{total}",
            "streak": self.streak,
            "streak_bonus": f"连续登录 {self.streak} 天，明日奖励 +{min(self.streak * 10, 100)}%",
            "quests": [
                {
                    "id": q["id"],
                    "name": q["name"],
                    "description": q["description"],
                    "progress": q["progress"],
                    "target": q["target"],
                    "completed": q["completed"],
                    "reward": q["reward"],
                    "difficulty": q["difficulty"],
                }
                for q in self.active_quests
            ],
        }
