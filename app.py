from flask import Flask, render_template, request
import smtplib
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet
from nltk.stem import PorterStemmer, WordNetLemmatizer
import contractions
import re
from googleapiclient.discovery import build

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

app = Flask(__name__)

# Your YouTube API key
API_KEY = "AIzaSyDh4cprQD50Y9Jn0L-b_6HkRzi694z6mTc"

youtube = build('youtube', 'v3', developerKey=API_KEY)

# Convert text to lowercase
def lowercase(text):
    return text.lower()

# Tokenization
def tokenize(text):
    return word_tokenize(text)

# Stopword removal
def remove_stopwords(tokens):
    stop_words = set(stopwords.words('english'))
    return [word for word in tokens if word not in stop_words]

# Punctuation and special character removal
def remove_punctuation(tokens):
    return [word for word in tokens if word.isalnum()]

# Stemming using Porter Stemmer
def stem(tokens):
    stemmer = PorterStemmer()
    return [stemmer.stem(word) for word in tokens]

# Lemmatization using WordNet Lemmatizer
def lemmatize(tokens):
    lemmatizer = WordNetLemmatizer()
    return [lemmatizer.lemmatize(word) for word in tokens]

# Contraction expansion
def expand_contractions(tokens):
    expanded_tokens = []
    for token in tokens:
        expanded_token = contractions.fix(token)
        expanded_tokens.append(expanded_token)
    return expanded_tokens

# Normalization (Synonym mapping)
def normalize(tokens):
    normalized_tokens = []
    for token in tokens:
        synonyms = wordnet.synsets(token)
        if synonyms:
            normalized_tokens.append(synonyms[0].lemmas()[0].name())
        else:
            normalized_tokens.append(token)
    return normalized_tokens

# Function to read abusive keywords from a text file
def read_abusive_keywords(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        keywords = [line.strip() for line in file]
    return keywords

# Function to check if a comment is abusive based on keywords
def is_abusive_keywords(comment_tokens, abusive_keywords):
    return any(token in abusive_keywords for token in comment_tokens)

# Function to preprocess a comment (remove URL links)
def preprocess_comment(comment):
    # Remove URLs from the comment
    comment = re.sub(r'http\S+', '', comment)
    return comment

def get_all_comments(video_id):
    comments = []

    try:
        next_page_token = None

        while True:
            response = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                textFormat="plainText",
                order="time",
                maxResults=100,  # Set the desired number of results per page
                pageToken=next_page_token
            ).execute()

            for item in response["items"]:
                comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                comments.append(comment)

            if "nextPageToken" in response:
                next_page_token = response["nextPageToken"]
            else:
                break

    except Exception as e:
        print("An error occurred while fetching comments:", str(e))

    return comments

def preprocess_and_detect_abusive_comments(video_id):
    comments = get_all_comments(video_id)
    abusive_comments = []

    # Read abusive keywords from text file
    abusive_keywords = read_abusive_keywords('abusive_keywords.txt')

    for i, comment in enumerate(comments):
        # Preprocess the comment (remove URLs)
        comment = preprocess_comment(comment)

        # Convert to lowercase
        comment = lowercase(comment)

        # Tokenization
        tokens = tokenize(comment)

        # Stopword removal
        tokens = remove_stopwords(tokens)

        # Punctuation and special character removal
        tokens = remove_punctuation(tokens)

        # Stemming
        tokens = stem(tokens)

        # Lemmatization
        tokens = lemmatize(tokens)

        # Contraction expansion
        tokens = expand_contractions(tokens)

        # Normalization
        tokens = normalize(tokens)

        # Check if the comment is abusive
        abusive = is_abusive_keywords(tokens, abusive_keywords)

        # Store comment data in a dictionary
        comment_data = {
            'comment': comment,
            'preprocessed_tokens': tokens,
            'abusive': abusive
        }

        # Append comment data to the list of abusive comments
        abusive_comments.append(comment_data)

        # Print the results of preprocessing and abusive detection
        print(f"Processed Comment {i + 1}: {comment}")
        print(f"Preprocessed Tokens: {tokens}")
        print(f"Abusive: {abusive}")
        print()

    return abusive_comments


# Define the /analyze route for comment analysis
@app.route('/analyze', methods=['POST'])
def analyze():
    if request.method == 'POST':
        video_link = request.form['video_link']
        video_id = extract_video_id(video_link)

        if video_id:
            comments_data = preprocess_and_detect_abusive_comments(video_id)
            return render_template('result.html', comments_data=comments_data)
        else:
            error_message = "Invalid video link. Please provide a valid YouTube video link."
            return render_template('index.html', error_message=error_message)

# Route for homepage and form submission
@app.route('/', methods=['GET', 'POST'])
def index():
    video_id = None  # Initialize video_id as None
    if request.method == 'POST':
        video_link = request.form['video_link']
        video_id = extract_video_id(video_link)

        if video_id:
            comments_data = preprocess_and_detect_abusive_comments(video_id)
            return render_template('result.html', comments_data=comments_data,video_id=video_id)
        else:
            error_message = "Invalid video link. Please provide a valid YouTube video link."
            return render_template('index.html', error_message=error_message,video_id=video_id)
    return render_template('index.html', video_id=video_id)

# Route for team page
@app.route('/team')
def team():
    return render_template('team.html')

# Route for about page
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        # Email configuration
        smtp_server = 'your_smtp_server'
        smtp_port = 587
        sender_email = 'your_sender_email@example.com'
        recipient_email = 'your_recipient_email@example.com'
        smtp_username = 'your_smtp_username'
        smtp_password = 'your_smtp_password'

        # Create the email message
        subject = f"Contact Form Submission from {name}"
        body = f"Name: {name}\nEmail: {email}\nMessage: {message}"
        email_message = f'Subject: {subject}\n\n{body}'

        # Send the email
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, recipient_email, email_message)
            server.quit()
            success_message = "Message sent successfully!"
            return render_template('contact.html', success_message=success_message)
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            return render_template('contact.html', error_message=error_message)
    
    return render_template('contact.html')

# Function to extract video ID from YouTube link
def extract_video_id(video_link):
    patterns = [
        r'^https?:\/\/(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)',
        r'^https?:\/\/(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]+)',
    ]

    for pattern in patterns:
        match = re.match(pattern, video_link)
        if match:
            return match.group(1)

    return None



# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
