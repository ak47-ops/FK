import os
import csv
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

CSV_FILE = 'text_metrics_log.csv'
PROJECTS_CSV = 'projects.csv'
USERS_CSV = 'registered_users.csv'

# Updated headers: Removed 'Target Grade'
HEADERS = [
    'Timestamp', 'Project Name', 'User Email', 'Original Text', 'Modified Text', 'Keywords',
    'Target Score', 'Target Read Time',
    'Chosen Platform', 'Chosen Region', 'Chosen Education', 'Chosen Age',
    'Letter Count', 'Sentence Count', 'Word Count', 'Unique Word Count', 'Total Syllables',
    'Avg Syllables per Word', 'Words Three Syllables', '% Words Three Syllables',
    'Longest Sentence', 'Paragraph Count', 'Avg Speaking Time', 'Avg Reading Time',
    'Avg Writing Time', 'Avg Words per Sentence', 'Avg Words per Paragraph',
    'Avg Sentences per Paragraph', 'Avg Characters per Word', 'Words >4 Syllables',
    '% Words >4 Syllables', 'Words >12 Letters', '% Words >12 Letters',
    'Flesch-Kincaid', 'Reading Ease', 'Average Word Length'
]

def log_to_csv(data):
    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data.get("projectName", "Default Project"),
        data.get("userEmail", ""),
        data.get("originalText", ""),
        data.get("modifiedText", ""),
        ", ".join(data.get("keywords", [])) if isinstance(data.get("keywords"), list) else data.get("keywords", ""),
        data.get("targetScore", ""),
        data.get("targetReadTime", ""),
        data.get("chosenPlatform", ""),
        data.get("chosenRegion", ""),
        data.get("chosenEducation", ""),
        data.get("chosenAge", "")
    ]
    metrics = data.get("modifiedMetrics", {})
    row.extend([
        metrics.get("letterCount", ""),
        metrics.get("sentenceCount", ""),
        metrics.get("wordCount", ""),
        metrics.get("uniqueWordCount", ""),
        metrics.get("totalSyllables", ""),
        metrics.get("avgSyllablesPerWord", ""),
        metrics.get("wordsThreeSyllables", ""),
        metrics.get("percWordsThreeSyllables", ""),
        metrics.get("longestSentence", ""),
        metrics.get("paragraphCount", ""),
        metrics.get("avgSpeakingTime", ""),
        metrics.get("avgReadingTime", ""),
        metrics.get("avgWritingTime", ""),
        metrics.get("avgWordsPerSentence", ""),
        metrics.get("avgWordsPerParagraph", ""),
        metrics.get("avgSentencesPerParagraph", ""),
        metrics.get("avgCharactersPerWord", ""),
        metrics.get("wordsMoreThan4Syllables", ""),
        metrics.get("percWordsMoreThan4Syllables", ""),
        metrics.get("wordsMoreThan12Letters", ""),
        metrics.get("percWordsMoreThan12Letters", ""),
        metrics.get("fleschKincaid", ""),
        metrics.get("readingEase", ""),
        metrics.get("averageWordLength", "")
    ])
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(HEADERS)
        writer.writerow(row)

def log_project(project_name, user_email):
    headers = ['Timestamp', 'Project Name', 'User Email']
    row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), project_name, user_email]
    file_exists = os.path.exists(PROJECTS_CSV)
    with open(PROJECTS_CSV, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(headers)
        writer.writerow(row)

def register_user(email, password):
    file_exists = os.path.exists(USERS_CSV)
    if file_exists:
        with open(USERS_CSV, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get("Email", "").lower() == email.lower():
                    return False  # User already exists
    headers = ["Timestamp", "Email", "Password"]
    hashed = generate_password_hash(password)
    row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), email, hashed]
    with open(USERS_CSV, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(headers)
        writer.writerow(row)
    return True

def validate_user(email, password):
    if os.path.exists(USERS_CSV):
        with open(USERS_CSV, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get("Email", "").lower() == email.lower():
                    stored_hash = row.get("Password", "")
                    if check_password_hash(stored_hash, password):
                        return True
    return False
