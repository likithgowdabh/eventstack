import psycopg2
import psycopg2.extras
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

def get_db_connection():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    return conn

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables for PostgreSQL
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            github_id INTEGER UNIQUE NOT NULL,
            username TEXT NOT NULL,
            email TEXT,
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            location TEXT,
            created_by INTEGER NOT NULL,
            is_finalized BOOLEAN DEFAULT FALSE,
            finalized_slot_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS time_slots (
            id SERIAL PRIMARY KEY,
            event_id TEXT NOT NULL,
            slot_datetime TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id SERIAL PRIMARY KEY,
            event_id TEXT NOT NULL,
            time_slot_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
            FOREIGN KEY (time_slot_id) REFERENCES time_slots (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(event_id, time_slot_id, user_id)
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id SERIAL PRIMARY KEY,
            event_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            comment_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_created_by ON events (created_by);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_time_slots_event_id ON time_slots (event_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_votes_event_id ON votes (event_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_votes_time_slot_id ON votes (time_slot_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_votes_user_id ON votes (user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_event_id ON comments (event_id);")
    
    conn.commit()
    cursor.close()
    conn.close()

def create_user(github_id, username, email, avatar_url):
    """Create or update a user"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE github_id = %s", (github_id,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        # Update existing user
        cursor.execute("""
            UPDATE users 
            SET username = %s, email = %s, avatar_url = %s, updated_at = CURRENT_TIMESTAMP
            WHERE github_id = %s
        """, (username, email, avatar_url, github_id))
        user_id = existing_user["id"]
    else:
        # Create new user
        cursor.execute("""
            INSERT INTO users (github_id, username, email, avatar_url)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (github_id, username, email, avatar_url))
        result = cursor.fetchone()
        user_id = result["id"] if result else None
    
    conn.commit()
    
    # Return user data
    if user_id:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return dict(user) if user else None
    else:
        cursor.close()
        conn.close()
        return None

def get_user_by_github_id(github_id):
    """Get user by GitHub ID"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE github_id = %s", (github_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(user) if user else None

def create_event(event_id, title, description, location, created_by):
    """Create a new event"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO events (id, title, description, location, created_by)
        VALUES (%s, %s, %s, %s, %s)
    """, (event_id, title, description, location, created_by))
    conn.commit()
    cursor.close()
    conn.close()
    return get_event_by_id(event_id)

def get_event_by_id(event_id):
    """Get event by ID"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT e.*, u.username as creator_username, u.avatar_url as creator_avatar
        FROM events e
        JOIN users u ON e.created_by = u.id
        WHERE e.id = %s
    """, (event_id,))
    event = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(event) if event else None

def get_events_by_user(user_id, created_by=True):
    """Get events created by or participated in by user"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    if created_by:
        cursor.execute("""
            SELECT e.*, u.username as creator_username
            FROM events e
            JOIN users u ON e.created_by = u.id
            WHERE e.created_by = %s
            ORDER BY e.created_at DESC
        """, (user_id,))
    else:
        cursor.execute("""
            SELECT DISTINCT e.*, u.username as creator_username
            FROM events e
            JOIN users u ON e.created_by = u.id
            JOIN votes v ON e.id = v.event_id
            WHERE v.user_id = %s AND e.created_by != %s
            ORDER BY e.created_at DESC
        """, (user_id, user_id))
    
    events = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(event) for event in events]

def add_time_slot(event_id, slot_datetime):
    """Add a time slot to an event"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO time_slots (event_id, slot_datetime)
        VALUES (%s, %s)
    """, (event_id, slot_datetime))
    conn.commit()
    cursor.close()
    conn.close()

def get_time_slots_by_event(event_id):
    """Get all time slots for an event"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT * FROM time_slots 
        WHERE event_id = %s 
        ORDER BY slot_datetime
    """, (event_id,))
    slots = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(slot) for slot in slots]

def vote_for_slot(event_id, slot_id, user_id, is_vote=True):
    """Vote for or unvote a time slot"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if is_vote:
        # Add vote (ignore if already exists)
        cursor.execute("""
            INSERT INTO votes (event_id, time_slot_id, user_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (event_id, time_slot_id, user_id) DO NOTHING
        """, (event_id, slot_id, user_id))
    else:
        # Remove vote
        cursor.execute("""
            DELETE FROM votes 
            WHERE event_id = %s AND time_slot_id = %s AND user_id = %s
        """, (event_id, slot_id, user_id))
    
    conn.commit()
    affected_rows = cursor.rowcount
    cursor.close()
    conn.close()
    
    # Broadcast update via WebSocket
    from handlers.websocket import VoteWebSocketHandler
    VoteWebSocketHandler.broadcast_vote_update(event_id)
    
    return affected_rows > 0

def get_votes_by_event(event_id):
    """Get all votes for an event with user info"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT v.*, u.username, u.avatar_url
        FROM votes v
        JOIN users u ON v.user_id = u.id
        WHERE v.event_id = %s
        ORDER BY v.created_at
    """, (event_id,))
    votes = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(vote) for vote in votes]

def add_comment(event_id, user_id, comment_text):
    """Add a comment to an event"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO comments (event_id, user_id, comment_text)
        VALUES (%s, %s, %s)
    """, (event_id, user_id, comment_text))
    conn.commit()
    cursor.close()
    conn.close()

def get_comments_by_event(event_id):
    """Get all comments for an event"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT c.*, u.username, u.avatar_url
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.event_id = %s
        ORDER BY c.created_at
    """, (event_id,))
    comments = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(comment) for comment in comments]

def finalize_event(event_id, slot_id):
    """Finalize an event with selected time slot"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE events 
        SET finalized_slot_id = %s, is_finalized = TRUE
        WHERE id = %s
    """, (slot_id, event_id))
    conn.commit()
    cursor.close()
    conn.close()
