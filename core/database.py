"""
游戏数据库模块 - 支持AI动态生成内容的持久化存储
使用SQLite存储物品、地图区域、敌人模板、技能等数据
"""
import json
import sqlite3
import hashlib
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class GameDatabase:
    """游戏内容数据库 - 管理AI生成的游戏内容"""

    def __init__(self, db_path: str = "data/game_content.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()

        # 物品表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL,
                subtype TEXT DEFAULT '',
                effect TEXT NOT NULL DEFAULT '{}',
                description TEXT DEFAULT '',
                price INTEGER DEFAULT 0,
                rarity TEXT DEFAULT 'common',
                source TEXT DEFAULT 'ai_generated',
                realm_required INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')

        # 地图区域表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS map_regions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                connections TEXT NOT NULL DEFAULT '[]',
                npc_types TEXT NOT NULL DEFAULT '[]',
                danger_level INTEGER DEFAULT 1,
                resources TEXT NOT NULL DEFAULT '[]',
                source TEXT DEFAULT 'ai_generated',
                discovered_at TEXT NOT NULL
            )
        ''')

        # 敌人模板表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enemy_templates (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name_prefix TEXT DEFAULT '',
                name_suffix TEXT NOT NULL,
                base_hp INTEGER NOT NULL,
                base_mp INTEGER NOT NULL,
                base_atk INTEGER NOT NULL,
                base_def INTEGER NOT NULL,
                skills TEXT NOT NULL DEFAULT '[]',
                description TEXT DEFAULT '',
                min_danger INTEGER DEFAULT 1,
                max_danger INTEGER DEFAULT 10,
                source TEXT DEFAULT 'ai_generated',
                created_at TEXT NOT NULL
            )
        ''')

        # 技能表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                realm INTEGER NOT NULL DEFAULT 1,
                mp_cost INTEGER NOT NULL DEFAULT 10,
                damage INTEGER DEFAULT 0,
                defense INTEGER DEFAULT 0,
                heal_hp INTEGER DEFAULT 0,
                heal_mp INTEGER DEFAULT 0,
                duration INTEGER DEFAULT 0,
                dodge INTEGER DEFAULT 0,
                type TEXT NOT NULL DEFAULT 'attack',
                description TEXT DEFAULT '',
                source TEXT DEFAULT 'ai_generated',
                created_at TEXT NOT NULL
            )
        ''')

        # AI生成记录表（防重复生成）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS generation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gen_type TEXT NOT NULL,
                prompt_hash TEXT NOT NULL,
                result_id TEXT,
                created_at TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()

    # ==================== 物品系统 ====================

    def add_item(self, item_data: Dict[str, Any]) -> str:
        """添加物品到数据库"""
        conn = self._get_conn()
        cursor = conn.cursor()

        item_id = item_data.get("id", hashlib.md5(
            item_data["name"].encode()
        ).hexdigest()[:12])

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO items
                (id, name, type, subtype, effect, description, price, rarity, source, realm_required, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item_id,
                item_data["name"],
                item_data.get("type", "consumable"),
                item_data.get("subtype", ""),
                json.dumps(item_data.get("effect", {}), ensure_ascii=False),
                item_data.get("description", ""),
                item_data.get("price", 0),
                item_data.get("rarity", "common"),
                item_data.get("source", "ai_generated"),
                item_data.get("realm_required", 0),
                datetime.now().isoformat()
            ))
            conn.commit()
        finally:
            conn.close()

        return item_id

    def get_item(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取物品"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM items WHERE name = ?', (name,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_dict(row, "effect")
        return None

    def get_all_items(self, item_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有物品，可按类型过滤"""
        conn = self._get_conn()
        cursor = conn.cursor()

        if item_type:
            cursor.execute('SELECT * FROM items WHERE type = ?', (item_type,))
        else:
            cursor.execute('SELECT * FROM items')

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row, "effect") for row in rows]

    def get_shop_items(self, realm_level: int = 1) -> List[Dict[str, Any]]:
        """获取商店物品（不包含装备，只包含消耗品/材料/秘籍）"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM items
            WHERE type IN ('consumable', 'material', 'skill_book')
            AND realm_required <= ?
            ORDER BY rarity, price
        ''', (realm_level,))
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row, "effect") for row in rows]

    def get_items_count(self) -> int:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM items')
        count = cursor.fetchone()[0]
        conn.close()
        return count

    # ==================== 地图区域系统 ====================

    def add_region(self, region_data: Dict[str, Any]) -> str:
        """添加地图区域"""
        conn = self._get_conn()
        cursor = conn.cursor()

        region_id = region_data.get("id", hashlib.md5(
            region_data["name"].encode()
        ).hexdigest()[:12])

        cursor.execute('''
            INSERT OR REPLACE INTO map_regions
            (id, name, description, connections, npc_types, danger_level, resources, source, discovered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            region_id,
            region_data["name"],
            region_data.get("description", ""),
            json.dumps(region_data.get("connections", []), ensure_ascii=False),
            json.dumps(region_data.get("npc_types", []), ensure_ascii=False),
            region_data.get("danger_level", 1),
            json.dumps(region_data.get("resources", []), ensure_ascii=False),
            region_data.get("source", "ai_generated"),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

        return region_id

    def get_region(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取区域"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM map_regions WHERE name = ?', (name,))
        row = cursor.fetchone()
        conn.close()

        if row:
            data = self._row_to_dict(row, "connections", "npc_types", "resources")
            return data
        return None

    def get_all_regions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有区域（返回字典格式兼容MAP_REGIONS）"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM map_regions')
        rows = cursor.fetchall()
        conn.close()

        regions = {}
        for row in rows:
            data = self._row_to_dict(row, "connections", "npc_types", "resources")
            name = data.pop("name")
            regions[name] = data

        return regions

    def get_regions_count(self) -> int:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM map_regions')
        count = cursor.fetchone()[0]
        conn.close()
        return count

    # ==================== 敌人模板系统 ====================

    def add_enemy_template(self, enemy_data: Dict[str, Any]) -> str:
        """添加敌人模板"""
        conn = self._get_conn()
        cursor = conn.cursor()

        enemy_id = enemy_data.get("id", hashlib.md5(
            f"{enemy_data.get('type', '')}_{enemy_data.get('name_suffix', '')}".encode()
        ).hexdigest()[:12])

        cursor.execute('''
            INSERT OR REPLACE INTO enemy_templates
            (id, type, name_prefix, name_suffix, base_hp, base_mp, base_atk, base_def,
             skills, description, min_danger, max_danger, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            enemy_id,
            enemy_data.get("type", "妖兽"),
            enemy_data.get("name_prefix", ""),
            enemy_data.get("name_suffix", "怪物"),
            enemy_data.get("base_hp", 50),
            enemy_data.get("base_mp", 20),
            enemy_data.get("base_atk", 10),
            enemy_data.get("base_def", 5),
            json.dumps(enemy_data.get("skills", []), ensure_ascii=False),
            enemy_data.get("description", ""),
            enemy_data.get("min_danger", 1),
            enemy_data.get("max_danger", 10),
            enemy_data.get("source", "ai_generated"),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

        return enemy_id

    def get_enemy_templates(self, danger_level: int = 1) -> List[Dict[str, Any]]:
        """获取指定危险等级可用的敌人模板"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM enemy_templates
            WHERE min_danger <= ? AND max_danger >= ?
        ''', (danger_level, danger_level))
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row, "skills") for row in rows]

    def get_enemy_types_for_danger(self, danger_level: int) -> List[str]:
        """获取指定危险等级可用的敌人类型"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT type FROM enemy_templates
            WHERE min_danger <= ? AND max_danger >= ?
        ''', (danger_level, danger_level))
        rows = cursor.fetchall()
        conn.close()

        return [row[0] for row in rows]

    def get_enemies_count(self) -> int:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM enemy_templates')
        count = cursor.fetchone()[0]
        conn.close()
        return count

    # ==================== 技能系统 ====================

    def add_skill(self, skill_data: Dict[str, Any]) -> str:
        """添加技能"""
        conn = self._get_conn()
        cursor = conn.cursor()

        skill_id = skill_data.get("id", hashlib.md5(
            skill_data["name"].encode()
        ).hexdigest()[:12])

        cursor.execute('''
            INSERT OR REPLACE INTO skills
            (id, name, realm, mp_cost, damage, defense, heal_hp, heal_mp,
             duration, dodge, type, description, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            skill_id,
            skill_data["name"],
            skill_data.get("realm", 1),
            skill_data.get("mp_cost", 10),
            skill_data.get("damage", 0),
            skill_data.get("defense", 0),
            skill_data.get("heal_hp", 0),
            skill_data.get("heal_mp", 0),
            skill_data.get("duration", 0),
            skill_data.get("dodge", 0),
            skill_data.get("type", "attack"),
            skill_data.get("description", ""),
            skill_data.get("source", "ai_generated"),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

        return skill_id

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM skills WHERE name = ?', (name,))
        row = cursor.fetchone()
        conn.close()
        return self._row_to_dict(row) if row else None

    def get_all_skills(self) -> Dict[str, Dict[str, Any]]:
        """获取所有技能（返回字典格式兼容SKILL_LIBRARY）"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM skills')
        rows = cursor.fetchall()
        conn.close()

        skills = {}
        for row in rows:
            data = self._row_to_dict(row)
            name = data.pop("name")
            skills[name] = data

        return skills

    def get_skills_count(self) -> int:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM skills')
        count = cursor.fetchone()[0]
        conn.close()
        return count

    # ==================== 生成日志 ====================

    def log_generation(self, gen_type: str, prompt_hash: str, result_id: str = ""):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO generation_log (gen_type, prompt_hash, result_id, created_at)
            VALUES (?, ?, ?, ?)
        ''', (gen_type, prompt_hash, result_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    # ==================== 工具方法 ====================

    @staticmethod
    def _row_to_dict(row: sqlite3.Row, *json_fields: str) -> Dict[str, Any]:
        """将sqlite Row转换为字典，并解析JSON字段"""
        d = dict(row)
        for field in json_fields:
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d

    def get_stats(self) -> Dict[str, int]:
        """获取数据库统计信息"""
        return {
            "items": self.get_items_count(),
            "regions": self.get_regions_count(),
            "enemies": self.get_enemies_count(),
            "skills": self.get_skills_count(),
        }
