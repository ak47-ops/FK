import os
import csv
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from textstat import flesch_kincaid_grade, flesch_reading_ease, syllable_count
import openai
import json
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load environment variables from a .env file if available
load_dotenv()

# Import CSV logger helpers
from csv_logger import log_to_csv, log_project, register_user, validate_user

app = Flask(__name__)
# In production, use a secure, random value for SECRET_KEY (e.g. via os.urandom)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

# --------------------------------------------------
# Set the OpenAI API key from the environment
# --------------------------------------------------
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("No API key found! Please set the OPENAI_API_KEY environment variable.")
openai.api_key = api_key



def get_reading_ease_descriptor(reading_ease):
    if reading_ease >= 90:
        return "Very Easy (Easily understood by an 11-year-old, simple language)"
    elif reading_ease >= 80:
        return "Easy (Conversational English, good for younger audiences)"
    elif reading_ease >= 70:
        return "Fairly Easy (Standard reading level, easily understood by teenagers)"
    elif reading_ease >= 60:
        return "Standard (Plain English, suitable for most readers)"
    elif reading_ease >= 50:
        return "Fairly Difficult (Somewhat challenging, college-level text)"
    elif reading_ease >= 30:
        return "Difficult (Best for academics and professionals, complex text)"
    else:
        return "Very Difficult (Extremely complex, suitable for specialists)"


def get_readability_descriptor(fk_grade):
    if fk_grade <= 5:
        return "Very Easy (5th grade or below, easily understood by an 11-year-old)"
    elif fk_grade <= 8:
        return "Easy (6th-8th grade, fairly easy to read)"
    elif fk_grade <= 10:
        return "Standard (9th-10th grade, moderately challenging)"
    elif fk_grade <= 12:
        return "Fairly Difficult (11th-12th grade, college level)"
    elif fk_grade <= 15:
        return "Difficult (College level, requires advanced reading skills)"
    else:
        return "Very Difficult (Postgraduate level, highly academic)"


def calculate_text_metrics(text):
    words = text.strip().split()
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    letter_count = sum(c.isalpha() for c in text)
    word_count = len(words)
    sentence_count = len(sentences) if sentences else 1
    avg_word_length = round(letter_count / word_count, 1) if word_count > 0 else 0
    unique_word_count = len(set(w.lower() for w in words))
    total_syllables = syllable_count(text)
    avg_syllables_per_word = round(total_syllables / word_count, 1) if word_count > 0 else 0
    words_three_syllables = sum(1 for w in words if syllable_count(w) == 3)
    perc_words_three_syllables = round((words_three_syllables / word_count) * 100, 1) if word_count > 0 else 0
    longest_sentence = max(sentences, key=lambda s: len(s.split())) if sentences else ""
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    paragraph_count = len(paragraphs) if paragraphs else 1
    avg_speaking_time = round(word_count / 150, 1) if word_count > 0 else 0
    avg_reading_time = round(word_count / 200, 1) if word_count > 0 else 0
    avg_writing_time = round(word_count / 40, 1) if word_count > 0 else 0
    avg_words_per_sentence = round(word_count / sentence_count, 1) if sentence_count > 0 else 0
    avg_words_per_paragraph = round(word_count / paragraph_count, 1) if paragraph_count > 0 else 0
    avg_sentences_per_paragraph = round(sentence_count / paragraph_count, 1) if paragraph_count > 0 else 0
    avg_characters_per_word = round(letter_count / word_count, 1) if word_count > 0 else 0
    words_more_than_4_syllables = sum(1 for w in words if syllable_count(w) > 4)
    perc_words_more_than_4_syllables = round((words_more_than_4_syllables / word_count) * 100, 1) if word_count > 0 else 0
    words_more_than_12_letters = sum(1 for w in words if len(w) > 12)
    perc_words_more_than_12_letters = round((words_more_than_12_letters / word_count) * 100, 1) if word_count > 0 else 0
    word_frequency = {}
    for w in words:
        wl = w.lower()
        word_frequency[wl] = word_frequency.get(wl, 0) + 1
    top_words = sorted(word_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
    flesch_kincaid = flesch_kincaid_grade(text)
    reading_ease = flesch_reading_ease(text)
    reading_time_minutes = round(word_count / 200, 2)
    metrics = {
        "letterCount": letter_count,
        "sentenceCount": sentence_count,
        "wordCount": word_count,
        "uniqueWordCount": unique_word_count,
        "totalSyllables": total_syllables,
        "avgSyllablesPerWord": avg_syllables_per_word,
        "wordsThreeSyllables": words_three_syllables,
        "percWordsThreeSyllables": perc_words_three_syllables,
        "longestSentence": longest_sentence,
        "paragraphCount": paragraph_count,
        "avgSpeakingTime": avg_speaking_time,
        "avgReadingTime": avg_reading_time,
        "avgWritingTime": avg_writing_time,
        "avgWordsPerSentence": avg_words_per_sentence,
        "avgWordsPerParagraph": avg_words_per_paragraph,
        "avgSentencesPerParagraph": avg_sentences_per_paragraph,
        "avgCharactersPerWord": avg_characters_per_word,
        "wordsMoreThan4Syllables": words_more_than_4_syllables,
        "percWordsMoreThan4Syllables": perc_words_more_than_4_syllables,
        "wordsMoreThan12Letters": words_more_than_12_letters,
        "percWordsMoreThan12Letters": perc_words_more_than_12_letters,
        "topWords": top_words,
        "fleschKincaid": flesch_kincaid,
        "readabilityDescriptor": get_readability_descriptor(flesch_kincaid),
        "readingEase": reading_ease,
        "readingEaseDescriptor": get_reading_ease_descriptor(reading_ease),
        "readingTime": reading_time_minutes,
        "averageWordLength": avg_word_length
    }
    return metrics

# --- Home Page ---
@app.route('/')
def home():
    return render_template('home.html')

# --- Analyzer Page (requires login) ---
@app.route('/analyzer')
def analyzer():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'user_email' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    text = request.form.get('text', '')
    if not text.strip():
        return jsonify({"error": "Please provide some text to analyze."}), 400
    metrics = calculate_text_metrics(text)
    return jsonify(metrics)

@app.route('/modify', methods=['POST'])
def modify_text():
    if 'user_email' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    text = data.get('text', '')
    target_score = int(data.get('target_score', 60))
    target_grade = int(data.get('target_grade', 10))
    target_read_time = int(data.get('target_read_time', 3))
    chosen_platform = data.get('platform', 'General')
    chosen_region = data.get('region', 'General')
    chosen_education = data.get('education', 'General')
    chosen_age = data.get('age', 'General')
    if not text.strip():
        return jsonify({"error": "Please provide some text to modify."}), 400
    prompt = (
        f"Adjust the following text to achieve:\n"
        f"- Flesch-Kincaid score of {target_score}\n"
        f"- Grade level of {target_grade}\n"
        f"- Reading time of {target_read_time} minutes\n"
        f"- Appeal to a wide audience\n\n"
        f"Platform context: {chosen_platform}\n"
        f"Region context: {chosen_region}\n"
        f"Education context: {chosen_education}\n"
        f"Age context: {chosen_age}\n\n"
        f"You must always return NON-EMPTY 'modified_text'. "
        f"If no change is needed, just return the same text. Also provide at least one relevant SEO keyword.\n\n"
        f"Respond ONLY in VALID JSON with exactly two keys: 'modified_text' (the updated text) and 'keywords'. "
        f"No extra commentary. Keep the context of the content relevant.\n\n"
        f"Input:\n{text}"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant that returns ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.4
        )
        raw_text = resp.choices[0].message.content.strip()
    except Exception as e:
        return jsonify({"error": f"OpenAI API request failed: {str(e)}"}), 500
    final_text = text
    final_keywords = []
    try:
        parsed = json.loads(raw_text)
        candidate = parsed.get("modified_text", "").strip()
        if candidate:
            final_text = candidate
        final_keywords = parsed.get("keywords", [])
    except json.JSONDecodeError:
        pass
    modified_metrics = calculate_text_metrics(final_text)
    response_data = {
        "originalText": text,
        "modifiedText": final_text,
        "keywords": final_keywords,
        "targetScore": target_score,
        "targetGrade": target_grade,
        "targetReadTime": target_read_time,
        "modifiedMetrics": modified_metrics,
        "chosenPlatform": chosen_platform,
        "chosenRegion": chosen_region,
        "chosenEducation": chosen_education,
        "chosenAge": chosen_age,
        "projectName": session.get("project_name", "Default Project"),
        "userEmail": session.get("user_email")
    }
    log_to_csv(response_data)
    return jsonify(response_data)

# --- Authentication Routes ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        if not email or not password:
            return render_template('register.html', error="Please fill in both fields.")
        if register_user(email, password):
            session["user_email"] = email
            return redirect(url_for('analyzer'))
        else:
            return render_template('register.html', error="User already exists.")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        if validate_user(email, password):
            session["user_email"] = email
            return redirect(url_for('analyzer'))
        else:
            return render_template('login.html', error="Invalid credentials.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# --- Projects Routes ---

@app.route('/projects', methods=['GET'])
def projects_view():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    projects = []
    if os.path.exists("projects.csv"):
        with open("projects.csv", newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get("User Email", "").lower() == session.get("user_email").lower():
                    projects.append(row)
    return render_template('projects.html', projects=projects)

@app.route('/new_project', methods=['POST'])
def new_project():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    project_name = request.form.get("project_name", "").strip()
    if not project_name:
        return redirect(url_for('projects_view'))
    log_project(project_name, session.get("user_email"))
    session["project_name"] = project_name
    return redirect(url_for('analyzer'))

@app.route('/project/<project_name>', methods=['GET'])
def project_detail(project_name):
    if 'user_email' not in session:
        return redirect(url_for('login'))
    logs = []
    if os.path.exists("text_metrics_log.csv"):
        with open("text_metrics_log.csv", newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get("Project Name", "Default Project") == project_name and row.get("User Email", "").lower() == session.get("user_email").lower():
                    logs.append(row)
    return render_template('project_detail.html', project_name=project_name, logs=logs)

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)
