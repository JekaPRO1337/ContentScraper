import aiosqlite
from config import DATABASE_PATH


class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH

    async def init_db(self):
        """Initialize database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Channel pairs table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS channel_pairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    donor_channel TEXT NOT NULL,
                    target_channel TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Statistics table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_id INTEGER,
                    posts_cloned INTEGER DEFAULT 0,
                    last_cloned_at TIMESTAMP,
                    FOREIGN KEY (pair_id) REFERENCES channel_pairs(id)
                )
            ''')
            
            # Link replacement rules table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS link_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT NOT NULL,
                    replacement TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Processed messages (to avoid duplicates)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS processed_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    message_id INTEGER NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(channel_id, message_id)
                )
            ''')
            
            await db.commit()

    async def add_channel_pair(self, donor_channel: str, target_channel: str):
        """Add a new channel pair"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'INSERT INTO channel_pairs (donor_channel, target_channel) VALUES (?, ?)',
                (donor_channel, target_channel)
            )
            pair_id = cursor.lastrowid
            
            # Initialize statistics for this pair
            await db.execute(
                'INSERT INTO statistics (pair_id, posts_cloned) VALUES (?, 0)',
                (pair_id,)
            )
            await db.commit()
            return pair_id

    async def remove_channel_pair(self, pair_id: int):
        """Remove a channel pair"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM channel_pairs WHERE id = ?', (pair_id,))
            await db.execute('DELETE FROM statistics WHERE pair_id = ?', (pair_id,))
            await db.commit()

    async def get_all_pairs(self):
        """Get all channel pairs"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('''
                SELECT cp.*, s.posts_cloned, s.last_cloned_at
                FROM channel_pairs cp
                LEFT JOIN statistics s ON cp.id = s.pair_id
                WHERE cp.enabled = 1
            ''') as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_pair_by_donor(self, donor_channel: str):
        """Get channel pair by donor channel"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM channel_pairs WHERE donor_channel = ? AND enabled = 1',
                (donor_channel,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def increment_statistics(self, pair_id: int):
        """Increment post count for a channel pair"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE statistics 
                SET posts_cloned = posts_cloned + 1,
                    last_cloned_at = CURRENT_TIMESTAMP
                WHERE pair_id = ?
            ''', (pair_id,))
            await db.commit()

    async def add_link_rule(self, pattern: str, replacement: str):
        """Add a link replacement rule"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'INSERT INTO link_rules (pattern, replacement) VALUES (?, ?)',
                (pattern, replacement)
            )
            await db.commit()
            return cursor.lastrowid

    async def remove_link_rule(self, rule_id: int):
        """Remove a link replacement rule"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM link_rules WHERE id = ?', (rule_id,))
            await db.commit()

    async def get_all_link_rules(self):
        """Get all enabled link replacement rules"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM link_rules WHERE enabled = 1'
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def is_message_processed(self, channel_id: str, message_id: int) -> bool:
        """Check if a message has already been processed"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT 1 FROM processed_messages WHERE channel_id = ? AND message_id = ?',
                (str(channel_id), message_id)
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None

    async def mark_message_processed(self, channel_id: str, message_id: int):
        """Mark a message as processed"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    'INSERT INTO processed_messages (channel_id, message_id) VALUES (?, ?)',
                    (str(channel_id), message_id)
                )
                await db.commit()
            except aiosqlite.IntegrityError:
                # Already exists, ignore
                pass

    async def get_statistics(self):
        """Get overall statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('''
                SELECT 
                    cp.id,
                    cp.donor_channel,
                    cp.target_channel,
                    COALESCE(s.posts_cloned, 0) as posts_cloned,
                    s.last_cloned_at
                FROM channel_pairs cp
                LEFT JOIN statistics s ON cp.id = s.pair_id
                WHERE cp.enabled = 1
            ''') as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


# Global database instance
db = Database()
