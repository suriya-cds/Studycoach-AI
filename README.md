StudyCoach AI 🎓

An AI-powered personal study assistant designed to help students learn concepts, practise questions, manage study sessions, and track their learning progress.

✨ Features

- AI Teacher: Get explanations for topics and concepts.
- AI Study Coach: Get personalized study guidance.
- AI Quiz: Generate practice questions to test your understanding.
- Study Timer: Organize focused study sessions.
- Progress Tracking: Review your learning progress.
- Local Data Storage: Store app data locally using JSON.
- Privacy-Focused AI: Uses a locally running Ollama model for AI responses.

🛠️ Tech Stack

- Python
- Streamlit
- Ollama
- Large Language Models (LLMs)
- JSON

🚀 Getting Started

Prerequisites

Install Python and Ollama. Download the Ollama application from:

https://ollama.com/

1. Clone the repository

git clone YOUR_GITHUB_REPOSITORY_URL
cd Studycoach

Replace "YOUR_GITHUB_REPOSITORY_URL" with your actual GitHub repository URL.

2. Install dependencies

python -m pip install streamlit requests

If your project has a "requirements.txt" file, you can instead install the listed dependencies using:

python -m pip install -r requirements.txt

3. Download the AI model

ollama pull llama3.2:3b

4. Start Ollama

Make sure Ollama is running on your computer.

5. Run the application

streamlit run app.py

The application should open in your browser.

📂 Project Structure

Studycoach/
├── app.py
├── README.md
├── requirements.txt
├── .gitignore
└── studycoach_data.json

The JSON data file is created or used by the application to store local study information. Your exact project files may differ.

🔒 Privacy

The application is designed to use a local Ollama model for AI generation. AI requests are processed locally when configured to use your local Ollama instance. Avoid uploading personal study data, credentials, or private information to a public repository.

🎯 Project Goal

StudyCoach AI aims to make self-study more organized, interactive, and accessible through AI-assisted learning.

🛣️ Future Improvements

- Flashcards and spaced repetition
- Weak-topic identification
- Personalized revision schedules
- Improved quiz analytics
- Study streaks and goal tracking
- Automated testing

👨‍💻 Author

Developed as a personal learning and portfolio project.