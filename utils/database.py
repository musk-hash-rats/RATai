import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'database.db')

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS levels (
                user_id INTEGER,
                guild_id INTEGER,
                xp REAL DEFAULT 0,
                level INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, guild_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS reactions (
                user_id INTEGER,
                guild_id INTEGER,
                reaction_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS active_jails (
                user_id INTEGER,
                guild_id INTEGER,
                release_at REAL,
                password TEXT,
                roles_data TEXT,
                primary key (user_id, guild_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS counting (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                current_count INTEGER DEFAULT 0,
                last_user_id INTEGER DEFAULT 0,
                high_score INTEGER DEFAULT 0
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS counting_stats (
                user_id INTEGER,
                guild_id INTEGER,
                correct_counts INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS eyes_state (
                channel_id INTEGER PRIMARY KEY,
                current_index INTEGER DEFAULT 0
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_flags (
                user_id INTEGER,
                flag_name TEXT,
                PRIMARY KEY (user_id, flag_name)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS private_channels (
                channel_id INTEGER PRIMARY KEY,
                owner_id INTEGER
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS bot_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        await db.commit()

async def add_xp(user_id: int, guild_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if user exists
        cursor = await db.execute('SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?', (user_id, guild_id))
        row = await cursor.fetchone()
        
        if row:
            current_xp, current_level = row
            new_xp = current_xp + amount
            # Exponential calculation: Level = (XP / 100) ^ 0.5
            new_level = int((new_xp / 100) ** 0.5) + 1 
            
            await db.execute('UPDATE levels SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?', 
                             (new_xp, new_level, user_id, guild_id))
        else:
            new_xp = amount
            new_level = int((new_xp / 100) ** 0.5) + 1
            await db.execute('INSERT INTO levels (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)', 
                             (user_id, guild_id, new_xp, new_level))
        
        await db.commit()
        return new_level

async def get_user_data(user_id: int, guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?', (user_id, guild_id))
        return await cursor.fetchone()

async def add_reaction_count(user_id: int, guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO reactions (user_id, guild_id, reaction_count) 
            VALUES (?, ?, 1) 
            ON CONFLICT(user_id, guild_id) 
            DO UPDATE SET reaction_count = reaction_count + 1
        ''', (user_id, guild_id))
        await db.commit()

async def get_reaction_count(user_id: int, guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT reaction_count FROM reactions WHERE user_id = ? AND guild_id = ?', (user_id, guild_id))
        row = await cursor.fetchone()
        return row[0] if row else 0

async def get_top_users(guild_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT user_id, xp, level FROM levels WHERE guild_id = ? ORDER BY xp DESC LIMIT ?', (guild_id, limit))
        return await cursor.fetchall()

async def add_active_jail(user_id: int, guild_id: int, release_at: float, password: str, roles_data: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT OR REPLACE INTO active_jails (user_id, guild_id, release_at, password, roles_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, guild_id, release_at, password, roles_data))
        await db.commit()

async def get_active_jail(user_id: int, guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT release_at, password, roles_data FROM active_jails WHERE user_id = ? AND guild_id = ?', (user_id, guild_id))
        return await cursor.fetchone()

async def remove_active_jail(user_id: int, guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM active_jails WHERE user_id = ? AND guild_id = ?', (user_id, guild_id))
        await db.commit()

async def get_expired_jails(current_time: float):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT user_id, guild_id, roles_data FROM active_jails WHERE release_at IS NOT NULL AND release_at <= ?', (current_time,))
        return await cursor.fetchall()

async def set_counting_channel(guild_id: int, channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO counting (guild_id, channel_id, current_count, last_user_id, high_score)
            VALUES (?, ?, 0, 0, 0)
            ON CONFLICT(guild_id) DO UPDATE SET channel_id = ?
        ''', (guild_id, channel_id, channel_id))
        await db.commit()

async def get_counting_data(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT channel_id, current_count, last_user_id, high_score FROM counting WHERE guild_id = ?', (guild_id,))
        return await cursor.fetchone()

async def update_counting_data(guild_id: int, count: int, user_id: int, high_score: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            UPDATE counting 
            SET current_count = ?, last_user_id = ?, high_score = ?
            WHERE guild_id = ?
        ''', (count, user_id, high_score, guild_id))
        await db.commit()

async def get_eyes_index(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT current_index FROM eyes_state WHERE channel_id = ?', (channel_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0

async def update_eyes_index(channel_id: int, index: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO eyes_state (channel_id, current_index)
            VALUES (?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET current_index = ?
        ''', (channel_id, index, index))
        await db.commit()

async def add_user_flag(user_id: int, flag_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT OR IGNORE INTO user_flags (user_id, flag_name) VALUES (?, ?)', (user_id, flag_name))
        await db.commit()

async def has_user_flag(user_id: int, flag_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT 1 FROM user_flags WHERE user_id = ? AND flag_name = ?', (user_id, flag_name))
        return await cursor.fetchone() is not None

async def add_private_channel(channel_id: int, owner_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT INTO private_channels (channel_id, owner_id) VALUES (?, ?)', (channel_id, owner_id))
        await db.commit()

async def get_private_channel_owner(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT owner_id FROM private_channels WHERE channel_id = ?', (channel_id,))
        row = await cursor.fetchone()
        return row[0] if row else None

async def remove_private_channel(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM private_channels WHERE channel_id = ?', (channel_id,))
        await db.commit()

async def get_config(key: str, default: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT value FROM bot_config WHERE key = ?', (key,))
        row = await cursor.fetchone()
        return row[0] if row else default

async def set_config(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO bot_config (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?
        ''', (key, value, value))
        await db.commit()

async def increment_counting_stat(user_id: int, guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO counting_stats (user_id, guild_id, correct_counts)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET correct_counts = correct_counts + 1
        ''', (user_id, guild_id))
        await db.commit()

async def get_top_counters(guild_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT user_id, correct_counts FROM counting_stats WHERE guild_id = ? ORDER BY correct_counts DESC LIMIT ?', (guild_id, limit))
        return await cursor.fetchall()

async def export_data():
    """Exports all database tables to a dictionary."""
    data = {}
    tables = [
        "levels", "reactions", "active_jails", "counting", "counting_stats",
        "eyes_state", "user_flags", "private_channels", "bot_config"
    ]
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        for table in tables:
            try:
                cursor = await db.execute(f"SELECT * FROM {table}")
                rows = await cursor.fetchall()
                # Convert rows to dicts
                data[table] = [dict(row) for row in rows]
            except Exception as e:
                print(f"Error exporting {table}: {e}")
                data[table] = []
    return data

async def import_data(data: dict):
    """Imports data from dictionary, overwriting existing data."""
    async with aiosqlite.connect(DB_PATH) as db:
        for table, rows in data.items():
            if not rows:
                continue
                
            # Get columns from first row
            columns = list(rows[0].keys())
            placeholders = ", ".join(["?"] * len(columns))
            col_names = ", ".join(columns)
            
            # Clear table first? Or Upsert?
            # For a full restore, wiping is cleaner to avoid ghosts.
            await db.execute(f"DELETE FROM {table}")
            
            # Bulk Insert
            for row in rows:
                values = [row[col] for col in columns]
                await db.execute(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", values)
                
        await db.commit()

