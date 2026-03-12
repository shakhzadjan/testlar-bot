import sqlite3
from config import DB_NAME

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Table for questions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option TEXT NOT NULL,
            language TEXT DEFAULT 'uz'
        )
    ''')
    
    # Table for user results
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT,
            group_name TEXT,
            score INTEGER NOT NULL,
            total_questions INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_result(user_id, full_name, group_name, score, total_questions):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO user_results (user_id, full_name, group_name, score, total_questions) VALUES (?, ?, ?, ?, ?)",
        (user_id, full_name, group_name, score, total_questions)
    )
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT user_id), COUNT(*), AVG(score) FROM user_results")
    stats = cursor.fetchone()
    conn.close()
    return stats

def get_all_results():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, group_name, score, total_questions, timestamp FROM user_results ORDER BY timestamp DESC")
    results = cursor.fetchall()
    conn.close()
    return results

def get_random_questions(limit=50, language='uz'):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM questions WHERE language = ? ORDER BY RANDOM() LIMIT ?", (language, limit))
    questions = cursor.fetchall()
    conn.close()
    return questions

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
