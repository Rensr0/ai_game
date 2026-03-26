import json
import sqlite3
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from utils.config import config

class MemoryEntry:
    def __init__(
        self,
        content: str,
        memory_type: str,
        importance: float,
        participants: List[str],
        context: str,
        timestamp: Optional[str] = None
    ):
        self.id = self._generate_id(content, timestamp)
        self.content = content
        self.memory_type = memory_type
        self.importance = importance
        self.participants = participants
        self.context = context
        self.timestamp = timestamp or datetime.now().isoformat()
        self.verified = True
        self.source = "system"
    
    def _generate_id(self, content: str, timestamp: Optional[str]) -> str:
        unique_string = f"{content}_{timestamp or datetime.now().isoformat()}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.memory_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "participants": self.participants,
            "importance": self.importance,
            "verified": self.verified,
            "source": self.source,
            "context": self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        entry = cls(
            content=data["content"],
            memory_type=data["type"],
            importance=data["importance"],
            participants=data["participants"],
            context=data["context"],
            timestamp=data["timestamp"]
        )
        entry.id = data["id"]
        entry.verified = data.get("verified", True)
        entry.source = data.get("source", "system")
        return entry

class ShortTermMemory:
    def __init__(self, max_entries: int = 20):
        self.max_entries = max_entries
        self.entries: List[Dict[str, str]] = []
    
    def add(self, role: str, content: str):
        self.entries.append({"role": role, "content": content})
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]
    
    def get_context(self) -> List[Dict[str, str]]:
        return self.entries.copy()
    
    def clear(self):
        self.entries.clear()
    
    def get_recent(self, n: int) -> List[Dict[str, str]]:
        return self.entries[-n:] if n < len(self.entries) else self.entries.copy()

class LongTermMemory:
    def __init__(self, db_path: str = "data/memories.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                participants TEXT,
                importance REAL,
                verified BOOLEAN,
                source TEXT,
                context TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS npc_relationships (
                npc_id TEXT PRIMARY KEY,
                player_name TEXT,
                relationship_score REAL,
                last_interaction TEXT,
                memories TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS world_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_memory(self, memory: MemoryEntry):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        data = memory.to_dict()
        cursor.execute('''
            INSERT OR REPLACE INTO memories 
            (id, type, content, timestamp, participants, importance, verified, source, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data["id"],
            data["type"],
            data["content"],
            data["timestamp"],
            json.dumps(data["participants"]),
            data["importance"],
            data["verified"],
            data["source"],
            data["context"]
        ))
        
        conn.commit()
        conn.close()
    
    def get_memories(
        self,
        memory_type: Optional[str] = None,
        participants: Optional[List[str]] = None,
        min_importance: Optional[float] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM memories WHERE 1=1"
        params = []
        
        if memory_type:
            query += " AND type = ?"
            params.append(memory_type)
        
        if participants:
            for participant in participants:
                query += " AND participants LIKE ?"
                params.append(f"%{participant}%")
        
        if min_importance is not None:
            query += " AND importance >= ?"
            params.append(min_importance)
        
        query += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        conn.close()
        
        memories = []
        for row in rows:
            memory_data = {
                "id": row[0],
                "type": row[1],
                "content": row[2],
                "timestamp": row[3],
                "participants": json.loads(row[4]),
                "importance": row[5],
                "verified": bool(row[6]),
                "source": row[7],
                "context": row[8]
            }
            memories.append(MemoryEntry.from_dict(memory_data))
        
        return memories
    
    def update_relationship(
        self,
        npc_id: str,
        player_name: str,
        relationship_change: float
    ):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT relationship_score FROM npc_relationships WHERE npc_id = ?
        ''', (npc_id,))
        
        result = cursor.fetchone()
        
        if result:
            new_score = result[0] + relationship_change
            new_score = max(-100, min(100, new_score))
            
            cursor.execute('''
                UPDATE npc_relationships 
                SET relationship_score = ?, last_interaction = ?
                WHERE npc_id = ?
            ''', (new_score, datetime.now().isoformat(), npc_id))
        else:
            cursor.execute('''
                INSERT INTO npc_relationships (npc_id, player_name, relationship_score, last_interaction, memories)
                VALUES (?, ?, ?, ?, ?)
            ''', (npc_id, player_name, relationship_change, datetime.now().isoformat(), "[]"))
        
        conn.commit()
        conn.close()
    
    def get_relationship(self, npc_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT npc_id, player_name, relationship_score, last_interaction, memories
            FROM npc_relationships WHERE npc_id = ?
        ''', (npc_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "npc_id": result[0],
                "player_name": result[1],
                "relationship_score": result[2],
                "last_interaction": result[3],
                "memories": json.loads(result[4])
            }
        return None
    
    def set_world_state(self, key: str, value: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO world_state (key, value, timestamp)
            VALUES (?, ?, ?)
        ''', (key, value, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_world_state(self, key: str) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM world_state WHERE key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None

class MemoryManager:
    def __init__(self):
        ai_config = config.get_ai_config()
        context_window = ai_config.get('context_window', 10)
        importance_threshold = ai_config.get('memory_importance_threshold', 5)
        
        self.short_term = ShortTermMemory(max_entries=context_window * 2)
        self.long_term = LongTermMemory()
        self.importance_threshold = importance_threshold
    
    def add_short_term(self, role: str, content: str):
        self.short_term.add(role, content)
    
    def add_long_term(
        self,
        content: str,
        memory_type: str,
        importance: float,
        participants: List[str],
        context: str
    ):
        if importance >= self.importance_threshold:
            memory = MemoryEntry(
                content=content,
                memory_type=memory_type,
                importance=importance,
                participants=participants,
                context=context
            )
            self.long_term.add_memory(memory)
    
    def get_context_for_ai(self) -> str:
        recent_context = self.short_term.get_context()
        context_str = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in recent_context[-10:]
        ])
        return context_str
    
    def search_memories(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 5
    ) -> List[MemoryEntry]:
        memories = self.long_term.get_memories(
            memory_type=memory_type,
            limit=limit * 2
        )
        
        query_lower = query.lower()
        scored_memories = []
        
        for memory in memories:
            score = 0
            if query_lower in memory.content.lower():
                score += 3
            if query_lower in memory.context.lower():
                score += 2
            for participant in memory.participants:
                if query_lower in participant.lower():
                    score += 1
            
            if score > 0:
                scored_memories.append((score, memory))
        
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [memory for score, memory in scored_memories[:limit]]
    
    def update_npc_relationship(self, npc_id: str, player_name: str, change: float):
        self.long_term.update_relationship(npc_id, player_name, change)
    
    def get_npc_relationship(self, npc_id: str) -> Optional[Dict[str, Any]]:
        return self.long_term.get_relationship(npc_id)
    
    def clear_short_term(self):
        self.short_term.clear()

    def set_world_state(self, key: str, value: str):
        """设置世界状态（委托给 LongTermMemory）"""
        self.long_term.set_world_state(key, value)

    def get_world_state(self, key: str) -> Optional[str]:
        """获取世界状态（委托给 LongTermMemory）"""
        return self.long_term.get_world_state(key)