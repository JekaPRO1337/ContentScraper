import aiosqlite
from config import DATABASE_PATH


class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH

    async def init_db(self):
        """Initialize database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS channel_pairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    donor_channel TEXT NOT NULL,
                    target_channel TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            async with db.execute("PRAGMA table_info(channel_pairs)") as cursor:
                columns = [row[1] for row in await cursor.fetchall()]
            if "realtime_enabled" not in columns:
                await db.execute(
                    "ALTER TABLE channel_pairs ADD COLUMN realtime_enabled INTEGER NOT NULL DEFAULT 0"
                )
            
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

            await db.execute('''
                CREATE TABLE IF NOT EXISTS button_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT NOT NULL,
                    text1 TEXT NOT NULL,
                    url1 TEXT NOT NULL,
                    text2 TEXT,
                    url2 TEXT,
                    text3 TEXT,
                    url3 TEXT,
                    custom_buttons_mode INTEGER DEFAULT 0,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Check and add columns if missing for button_rules
            async with db.execute("PRAGMA table_info(button_rules)") as cursor:
                btn_columns = [row[1] for row in await cursor.fetchall()]
            
            if "text3" not in btn_columns:
                await db.execute("ALTER TABLE button_rules ADD COLUMN text3 TEXT")
            if "url3" not in btn_columns:
                await db.execute("ALTER TABLE button_rules ADD COLUMN url3 TEXT")
            if "custom_buttons_mode" not in btn_columns:
                await db.execute("ALTER TABLE button_rules ADD COLUMN custom_buttons_mode INTEGER DEFAULT 0")
            
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

            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    lang TEXT NOT NULL DEFAULT 'ru',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.commit()

    async def get_user_lang(self, user_id: int) -> str:
        """Get user language preference"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT lang FROM user_settings WHERE user_id = ?',
                (int(user_id),)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row and row[0] else 'ru'

    async def set_user_lang(self, user_id: int, lang: str):
        """Set user language preference"""
        lang = (lang or 'ru').lower()
        if lang not in {'ru', 'en'}:
            lang = 'ru'

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                '''
                INSERT INTO user_settings (user_id, lang, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    lang = excluded.lang,
                    updated_at = CURRENT_TIMESTAMP
                ''',
                (int(user_id), lang)
            )
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

    async def _reset_sequences(self, db: aiosqlite.Connection, names: list[str]):
        placeholders = ",".join(["?"] * len(names))
        await db.execute(f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})", names)

    async def remove_channel_pair(self, pair_id: int):
        """Remove a channel pair"""
        donor_channel = None
        async with aiosqlite.connect(self.db_path) as db:
            # Get channel info to clear processed messages
            async with db.execute('SELECT donor_channel FROM channel_pairs WHERE id = ?', (pair_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    donor_channel = row[0]
                    # Try to normalize if it's an ID
                    await db.execute('DELETE FROM processed_messages WHERE channel_id = ?', (donor_channel,))
                    # Also try to delete by normalized ID just in case
                    if donor_channel.startswith("-100"):
                         await db.execute('DELETE FROM processed_messages WHERE channel_id = ?', (donor_channel,))

            await db.execute('DELETE FROM channel_pairs WHERE id = ?', (pair_id,))
            await db.execute('DELETE FROM statistics WHERE pair_id = ?', (pair_id,))

            async with db.execute('SELECT COUNT(1) FROM channel_pairs') as cursor:
                row = await cursor.fetchone()
                if row and int(row[0]) == 0:
                    await self._reset_sequences(db, ["channel_pairs", "statistics"])

            await db.commit()
            return donor_channel

    async def clear_data(self, include_rules: bool = False):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM processed_messages')
            await db.execute('DELETE FROM statistics')
            await db.execute('DELETE FROM channel_pairs')

            names = ["processed_messages", "statistics", "channel_pairs"]

            if include_rules:
                await db.execute('DELETE FROM link_rules')
                names.append("link_rules")

                await db.execute('DELETE FROM button_rules')
                names.append("button_rules")

            await self._reset_sequences(db, names)
            await db.commit()

    async def reset_pair_progress(self, pair_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            donor_channel = None
            async with db.execute(
                'SELECT donor_channel FROM channel_pairs WHERE id = ?',
                (pair_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    donor_channel = row[0]
            if donor_channel is None:
                return
            await db.execute(
                'DELETE FROM processed_messages WHERE channel_id = ?',
                (donor_channel,),
            )
            await db.execute(
                'UPDATE statistics SET posts_cloned = 0, last_cloned_at = NULL WHERE pair_id = ?',
                (pair_id,),
            )
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

    async def get_pair_by_id(self, pair_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                '''
                SELECT cp.*, s.posts_cloned, s.last_cloned_at
                FROM channel_pairs cp
                LEFT JOIN statistics s ON cp.id = s.pair_id
                WHERE cp.id = ?
                ''',
                (pair_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

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

    async def set_realtime_enabled(self, pair_id: int, enabled: bool):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE channel_pairs SET realtime_enabled = ? WHERE id = ?',
                (1 if enabled else 0, pair_id),
            )
            await db.commit()

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

    async def remove_link_rule_by_pattern(self, pattern: str):
        """Remove link replacement rules by exact pattern (case-insensitive)"""
        patt = (pattern or "").strip()
        if not patt:
            return 0
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'DELETE FROM link_rules WHERE LOWER(pattern) = LOWER(?)',
                (patt,)
            )
            await db.commit()
            # Return count removed
            async with db.execute(
                'SELECT COUNT(1) FROM link_rules WHERE LOWER(pattern) = LOWER(?)',
                (patt,)
            ) as cursor:
                row = await cursor.fetchone()
                return int(row[0]) if row and row[0] else 0

    async def get_all_link_rules(self):
        """Get all enabled link replacement rules"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM link_rules WHERE enabled = 1'
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def add_button_rule(
        self,
        mode: str,
        text1: str,
        url1: str,
        text2: str | None = None,
        url2: str | None = None,
        text3: str | None = None,
        url3: str | None = None,
    ):
        async with aiosqlite.connect(self.db_path) as db:
            # Clear existing rules first (system supports one global set for now)
            await db.execute('DELETE FROM button_rules')
            
            cursor = await db.execute(
                '''
                INSERT INTO button_rules (mode, text1, url1, text2, url2, text3, url3)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    mode,
                    text1,
                    url1,
                    text2,
                    url2,
                    text3,
                    url3,
                )
            )
            await db.commit()
            return cursor.lastrowid

    async def remove_button_rule(self, rule_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM button_rules WHERE id = ?', (rule_id,))
            await db.commit()

    async def clear_button_rules(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM button_rules')
            await db.commit()

    async def get_all_button_rules(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM button_rules WHERE enabled = 1 ORDER BY id ASC'
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
