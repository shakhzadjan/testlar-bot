import sqlite3
import re
from config import DB_NAME

def import_from_txt(file_path, language='uz'):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Clear existing questions for this language to avoid duplicates during testing
    cursor.execute("DELETE FROM questions WHERE language = ?", (language,))
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by "№" marker since each question starts with it
    blocks = re.split(r'№\s*\d+\.', content)
    
    count = 0
    for block in blocks:
        if not block.strip():
            continue
            
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        
        question = ""
        options = []
        correct = ""
        
        for line in lines:
            if line.startswith("Savol:"):
                question = line.replace("Savol:", "").strip()
            elif line.startswith("-"):
                options.append(line[1:].strip())
            elif line.startswith("To'g'ri:"):
                # Clean up "To'g'ri: C (Izoh: ...)"
                match = re.search(r"To'g'ri:\s*([A-D])", line, re.IGNORECASE)
                if match:
                    correct = match.group(1).upper()
        
        if question and len(options) >= 4 and correct:
            cursor.execute(
                "INSERT INTO questions (question, option_a, option_b, option_c, option_d, correct_option, language) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (question, options[0], options[1], options[2], options[3], correct, language)
            )
            count += 1
            
    conn.commit()
    conn.close()
    print(f"Successfully imported {count} questions for language: {language}")

if __name__ == "__main__":
    import os
    # Initialize database first
    from database import init_db
    init_db()
    
    # Import Uzbek tests
    if os.path.exists("tests.txt"):
        import_from_txt("tests.txt", "uz")
    else:
        print("Uzbek tests file (tests.txt) not found.")

    # Import Russian tests
    if os.path.exists("rus_tests.txt"):
        import_from_txt("rus_tests.txt", "ru")
    else:
        print("Russian tests file (rus_tests.txt) not found.")
