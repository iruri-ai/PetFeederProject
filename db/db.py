import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple, Dict
import os

class maoDB:
    """猫粮数据库：吃饭事件记录 + 投喂时间表"""
    
    def __init__(self, db_path: str = "eating_records.db"):
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self):
        """初始化表结构（如果不存在则创建）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ========== 表1：吃饭事件记录 ==========
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='eating_records'
        """)
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            cursor.execute("""
                CREATE TABLE eating_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    result TEXT,
                    img_path TEXT,
                    begin_time TEXT NOT NULL,
                    begin_weight REAL NOT NULL,
                    end_time TEXT,
                    end_weight REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print(f"[DB] 表创建成功: eating_records")
        else:
            # 检查列是否存在（兼容旧表）
            cursor.execute("PRAGMA table_info(eating_records)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'created_at' not in columns:
                cursor.execute("ALTER TABLE eating_records ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
                print("[DB] 添加列: created_at")
        
        # ========== 表2：投喂时间表 ==========
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='feeding_schedule'
        """)
        schedule_exists = cursor.fetchone() is not None
        
        if not schedule_exists:
            cursor.execute("""
                CREATE TABLE feeding_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feed_time TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1
                )
            """)
            print(f"[DB] 表创建成功: feeding_schedule")
            
            # 插入几条示例数据（可选）
            cursor.execute("""
                INSERT INTO feeding_schedule (feed_time, enabled) VALUES 
                ('08:00', 1),
                ('12:00', 1),
                ('18:00', 1),
                ('22:00', 1)
            """)
            print("[DB] 插入示例投喂时间")
        
        conn.commit()
        conn.close()
        print(f"[DB] 数据库初始化完成: {self.db_path}")
    
    # ==================== 表1：吃饭事件记录 ====================
    
    def insert_record(self, 
                      result: str,
                      img_path: str,
                      begin_time: str,
                      begin_weight: float,
                      end_time: str = None,
                      end_weight: float = None) -> int:
        """插入一条吃饭记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO eating_records 
            (result, img_path, begin_time, begin_weight, end_time, end_weight)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (result, img_path, begin_time, begin_weight, end_time, end_weight))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[DB] 插入记录 ID={record_id}")
        return record_id
    
    def delete_record(self, record_id: int) -> bool:
        """删除指定吃饭记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM eating_records WHERE id = ?", (record_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected > 0:
            print(f"[DB] 删除记录 ID={record_id}")
            return True
        return False
    
    def delete_all_records(self) -> int:
        """删除所有吃饭记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM eating_records")
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"[DB] 删除所有记录，共 {count} 条")
        return count
    
    def get_record_by_id(self, record_id: int) -> Optional[Dict]:
        """根据ID查询吃饭记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM eating_records WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    def get_record_count(self) -> int:
        """获取吃饭记录的总数量"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM eating_records")
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    def get_all_records(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取所有吃饭记录（分页）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM eating_records 
            ORDER BY begin_time DESC 
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_recent_records(self, count: int = 10) -> List[Dict]:
        """获取最近N条吃饭记录"""
        if count == 0:
            return []
        return self.get_all_records(limit=count, offset=0)
    def get_daily_consumption(self, date: str = None):
        """
        获取每日吃饭量（消耗的重量 = begin_weight - end_weight）
        
        Args:
            date: 日期，格式 "YYYY-MM-DD"，None 则返回所有日期的统计
        
        Returns:
            每日吃饭量统计列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if date:
            # 查询指定日期
            cursor.execute("""
                SELECT 
                    DATE(begin_time) as date,
                    COUNT(*) as meal_count,
                    SUM(begin_weight - end_weight) as total_consumption,
                    AVG(begin_weight - end_weight) as avg_consumption
                FROM eating_records 
                WHERE DATE(begin_time) = ? 
                    AND end_weight IS NOT NULL
                GROUP BY DATE(begin_time)
            """, (date,))
        else:
            # 查询所有日期
            cursor.execute("""
                SELECT 
                    DATE(begin_time) as date,
                    COUNT(*) as meal_count,
                    SUM(begin_weight - end_weight) as total_consumption,
                    AVG(begin_weight - end_weight) as avg_consumption
                FROM eating_records 
                WHERE end_weight IS NOT NULL
                GROUP BY DATE(begin_time)
                ORDER BY date DESC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    # ==================== 表2：投喂时间表 ====================
    
    def insert_schedule(self, feed_time: str, enabled: int = 1) -> int:
        """
        插入投喂时间
        
        Args:
            feed_time: 投喂时间，格式 "HH:MM"（如 "08:00"）
            enabled: 是否启用，1=启用，0=禁用
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO feeding_schedule (feed_time, enabled)
            VALUES (?, ?)
        """, (feed_time, enabled))
        
        schedule_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[DB] 插入投喂时间 ID={schedule_id}, time={feed_time}")
        return schedule_id
    
    def delete_schedule(self, schedule_id: int) -> bool:
        """删除投喂时间"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM feeding_schedule WHERE id = ?", (schedule_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected > 0:
            print(f"[DB] 删除投喂时间 ID={schedule_id}")
            return True
        return False
    
    def delete_all_schedules(self) -> int:
        """删除所有投喂时间"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM feeding_schedule")
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"[DB] 删除所有投喂时间，共 {count} 条")
        return count
    
    def get_schedule_by_id(self, schedule_id: int) -> Optional[Dict]:
        """根据ID查询投喂时间"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM feeding_schedule WHERE id = ?", (schedule_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_all_schedules(self, include_disabled: bool = False) -> List[Dict]:
        """
        获取所有投喂时间
        
        Args:
            include_disabled: 是否包含禁用的时间
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if include_disabled:
            cursor.execute("SELECT * FROM feeding_schedule ORDER BY feed_time")
        else:
            cursor.execute("SELECT * FROM feeding_schedule WHERE enabled = 1 ORDER BY feed_time")
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_enabled_schedules(self) -> List[Dict]:
        """获取启用的投喂时间"""
        return self.get_all_schedules(include_disabled=False)
    
    def update_schedule_enabled(self, schedule_id: int, enabled: int) -> bool:
        """
        更新投喂时间的启用状态
        
        Args:
            schedule_id: 投喂时间ID
            enabled: 1=启用，0=禁用
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE feeding_schedule SET enabled = ? WHERE id = ?
        """, (enabled, schedule_id))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected > 0:
            print(f"[DB] 更新投喂时间 ID={schedule_id}, enabled={enabled}")
            return True
        return False
    
    def update_schedule_time(self, schedule_id: int, feed_time: str) -> bool:
        """更新投喂时间"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE feeding_schedule SET feed_time = ? WHERE id = ?
        """, (feed_time, schedule_id))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected > 0:
            print(f"[DB] 更新投喂时间 ID={schedule_id}, time={feed_time}")
            return True
        return False
    
    def get_next_feed_time(self) -> Optional[Dict]:
        """获取下一个将要执行的投喂时间（基于当前时间）"""
        now = datetime.now().strftime("%H:%M")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查找今天还没过的最早的投喂时间
        cursor.execute("""
            SELECT * FROM feeding_schedule 
            WHERE enabled = 1 AND feed_time > ?
            ORDER BY feed_time ASC
            LIMIT 1
        """, (now,))
        
        row = cursor.fetchone()
        
        if not row:
            # 如果没有，返回明天最早的
            cursor.execute("""
                SELECT * FROM feeding_schedule 
                WHERE enabled = 1
                ORDER BY feed_time ASC
                LIMIT 1
            """)
            row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None

