# ISKA: Intelligent Standing Kiosk for Annnouncements and Inquiries
### *A Sovereign, Semantic AI Kiosk*

**ISKA** is an offline-first, intelligent information kiosk designed to provide students with near-instant access to campus information, announcements, and FAQs. Built specifically for the **Raspberry Pi 4 Model B**, it leverages a sophisticated "Sovereign AI" architecture that operates entirely without an internet connection.

---

## 🚀 Key Features

*   **Sovereign Intelligence:** Powered by **Ollama (Gemma 2B)** running 100% locally. No cloud APIs, no data leaks, and zero operational costs.
*   **Semantic RAG (Retrieval-Augmented Generation):** Uses vector embeddings (`all-MiniLM-L6-v2`) to find the *intent* behind questions. Grounded in a local SQLite database to ensure zero-hallucination responses.
*   **Localized Voice Interface:** Includes a custom "Filipino Fix" using the **Vosk engine** and phonetic overrides to accurately handle local accents and campus-specific terms (e.g., "ISKA," "PUP," "Biñan").
*   **Student Analytics Suite:** A dedicated administrative portal to review session transcripts, track usage density (UTC +8 timezone), and audit AI performance through messaging-style modals.
*   **Hardware-Resilient Engineering:** Implements a **Persistent Microphone Architecture** and a **Vosk-to-STT Handshake** to prevent hardware collisions on the Raspberry Pi audio bus.

---

## 🛠️ The Tech Stack

| Component              | Technology                                   |
| :--------------------- | :------------------------------------------- |
| **Edge AI Engine**      | Ollama (Gemma 2B)                            |
| **Semantic Search**     | SentenceTransformers (`all-MiniLM-L6-v2`)    |
| **Speech-to-Text**      | Vosk (Offline Inference)                     |
| **Text-to-Speech**      | Edge-TTS (with Phonetic Interceptor)         |
| **Backend**             | Python 3.11 / Flask                          |
| **Database**            | SQLite3                                      |
| **Admin UI**            | Bootstrap 5 / JavaScript                     |
| **Kiosk UI**            | Python Tkinter                               |

---

## 📂 Project Structure

*   `main.py` - The primary Kiosk UI and hardware lifecycle manager.
*   `backend.py` - The "Brain" containing Semantic RAG, AI logic, and jailbreak protection.
*   `admin.py` - The Flask-based server for the CMS and Analytics portal.
*   `iska_database.db` - The source of truth for campus data and interaction logs.
*   `templates/` - HTML templates for the administrative dashboard.
*   `CHANGELOG.md` - Detailed history of technical milestones and versioning.

---

## ⚙️ Installation & Usage

### 1. Prerequisite: Ollama
Install Ollama and pull the Gemma 2B model:
```bash
curl -fsSL [https://ollama.com/install.sh](https://ollama.com/install.sh)
ollama pull gemma:2b
```

### 2. Install Dependencies

```bash
pip install Flask ollama sentence-transformers vosk edge-tts pygame pyaudio
```

To launch the ISKA interface.
```bash 
python main.py
```
To launch the Administrative CMS (Accessible via localhost:5000):
```bash 
python admin.py
```

### 3. Database Setup
Before the kiosk for the first time, initialize the local database:<br>
```bash 
python db_setup.py
```
<br>

This will automatically generate the following tables:<br>
*   **`announcements`**: For campus news.
*   **`kiosk_info`**: For FAQ triggers.
*   **`query_logs`**: For student analytics.
*   **`users`**: For secure admin login.

## 📜 Development Philosophy
ISKA follows the YAGNI (You Aren't Gonna Need It) principle and Semantic Versioning. It was developed iteratively, evolving from a simple database manager (v1.0.0) to a fully sovereign semantic assistant (v2.5.0).

Current Version: 2.5.0 "Sovereign Semantic"



Authors:
Amado, Arwel Daylan S.<br>
Bermudez, John Carlo B.<br>
Espino, Raeh Manart H.<br>
Gerobin, Clarence D.<br>
Reyes, Mariel !.<br>
Manabat, Kristine Heart A.