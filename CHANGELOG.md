# Change Log

All notable changes to this project will be documented in this file. This project adheres to a **Domain-Based Versioning** system to track the independent evolution of the Kiosk subsystems.

---

# Release Summary

| Project Version | Release Date |  CMS (Admin) | Core (System) | Backend (AI) | Frontend (UI) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **v1.6.0** | 2026-05-14 | v1.1.0 | v2.5.0 | v3.3.0 | v4.2.0 | 
| **v1.5.0** | 2026-05-14 | v1.1.0 | v2.4.0 | v3.2.0 | v4.1.0 | 
| **v1.4.0** | 2026-05-13 | v1.1.0 | v2.4.0 | v3.2.0 | v4.0.1 | 
| **v1.3.0** | 2026-05-13 | v1.1.0 | v2.3.0 | v3.2.0 | v4.0.0 | 
| **v1.2.0** | 2026-05-09 | v1.1.0 | v2.2.0 | v3.1.0 |  :---  | 
| **v1.1.0** | 2026-04-24 | v1.1.0 | v2.1.0 | v3.0.0 |  :---  | 
| **v1.0.0** | 2026-03-11 | v1.0.0 |  :---  |  :---  |  :---  |


---

## [4.x.x] — FRONTEND (UI/UX)
*Focuses on the animated UI/UX interface, layout design, and student-facing chat components.*

### [4.2.0] - 2026-05-16
* **ISKA-UI-8003 MINOR** **Backend UI Hookup:** Integrated the BMO chat interface with the new Adaptive Response Layer to seamlessly handle alternating fast-track and streamed AI responses.

### [4.1.0] - 2026-05-14
* **ISKA-UI-7031 MINOR** Added **Logo image support** in the topbar, replacing the gold text badge with `logo.png`.
* **ISKA-UI-7032 PATCH** Refined **BMO face scaling** to 370x222 (5:3 ratio) to prevent visual distortion and horizontal stretching.
* **ISKA-UI-7033 MINOR** **UI De-cluttering:** Reduced online status indicators to a single state pill and badge per designer feedback.
* **ISKA-UI-7034 MINOR** Integrated **Network Monitor** with the UI badge to display a red "ISKA OFFLINE" alert upon connection loss.

### [4.0.1] - 2026-05-13
* **ISKA-UI-7025 PATCH** Resolved BMO face stretching by correcting dimensions to match the 5:3 aspect ratio of the assets.
* **ISKA-UI-7027 MINOR** Standardized `FACE_H = FACE_W × 0.6` formula in code for future responsive scaling.

### [4.0.0] - 2026-05-13
* **ISKA-UI-7001 MAJOR** Integrated animated **BmoFaceWidget** with 13 distinct PNG states (idle, listening, thinking, etc.).
* **ISKA-UI-7002 MAJOR** Implemented **ChatMessage bubble system** featuring maroon user queries and gold ISKA responses.
* **ISKA-UI-7003 MINOR** Built full UI layout including PUP topbar, welcome banner, quick-topic chips, and footer help button.
* **ISKA-UI-7004 MINOR** Added **2×2 Quick Info Cards** for registrar, library, and enrollment inquiries.
* **ISKA-UI-7006 MINOR** Added **EN/FIL language toggle** with visual active states on the left panel.

---

## [3.x.x] — BACKEND (AI & S-RAG)
*Focuses on Semantic Vector Search, LLM integration, and intelligent response routing.*

### [3.3.0] - 2026-05-16
* **ISKA-BACKEND-8001 MAJOR** Completed a comprehensive **Semantic RAG Rewrite**, completely replacing legacy keyword matching with deep semantic intent parsing via `all-MiniLM-L6-v2` vector embeddings.
* **ISKA-BACKEND-8002 MAJOR** Engineered the **Adaptive Response Layer** to dynamically intercept, classify, and route incoming student inquiries across Fast (Cached), Augmented (RAG), or Fallback paths.

### [3.2.0] - 2026-05-13
* **ISKA-BACKEND-7009 MINOR** Added **Small Talk Interceptor** to bypass Ollama for greetings and capability questions.
* **ISKA-BACKEND-7014 MINOR** Rewrote Augmented Path prompts with negative examples to prevent Gemma 2B hallucinations.
* **ISKA-BACKEND-7015 MINOR** Implemented a **30-second Ollama timeout** using `threading.Event` to prevent indefinite freezes.

### [3.1.0] - 2026-05-09
* **ISKA-BACKEND-6001 MAJOR** Implemented **Semantic Vector Search** using `SentenceTransformer (all-MiniLM-L6-v2)`.
* **ISKA-BACKEND-6002 MAJOR** Introduced the **Adaptive Response Layer** (Fast, Augmented, and Fallback paths).
* **ISKA-BACKEND-6006 MAJOR** **Separation of Concerns:** Migrated AI and RAG logic into a dedicated `IskaBackend` class.
* **ISKA-BACKEND-6013 PATCH** Integrated `_db_cache` to prevent redundant embedding rebuilds unless the schema changes.

### [3.0.0] - 2026-04-23
* **ISKA-CORE-4001 MAJOR** Completed **Full Offline Migration** to Ollama and the Gemma 2B model.
* **ISKA-CORE-4002 MAJOR** Implemented the initial **SQLite-to-LLM RAG pipeline**.

---

## [2.x.x] — CORE (System & Hardware)
*Focuses on hardware lifecycle management, kiosk security, and system stability.*

### [2.5.0] - 2026-05-16
* **ISKA-CORE-8004 MINOR** **Session Auto-Reset:** Implemented an automated session tear-down sequence triggered by gratitude/farewell semantic intents (e.g., "thank you").
* **ISKA-CORE-8005 MINOR** **Synchronized Context Flush:** Configured the session reset state machine to delay memory buffer clearing and chat history flushes until *after* the Text-to-Speech (TTS) engine fully renders the AI's final response, ensuring a clean transition for the next student.

### [2.4.0] - 2026-05-14
* **ISKA-CORE-7028 MINOR** **Kiosk Hardening:** Implemented a hidden exit mechanism (5-tap sequence on PUP seal) triggering a staff PIN dialog.
* **ISKA-CORE-7029 MINOR** Added `EXIT_PIN` configuration constant for centralized PIN management.
* **ISKA-CORE-7030 MINOR** **Anti-Brute Force:** Implemented a 3-attempt lockout with a 30-second cooldown on the PIN dialog.
* **ISKA-CORE-7035 PATCH** Fixed **AttributeError** in `_mic_released` caused by a threading declaration collision during state variable insertion.

### [2.3.0] - 2026-05-13
* **ISKA-CORE-7008 MINOR** Added `iska.service` **systemd unit file** for Raspberry Pi 4 auto-start and crash recovery.
* **ISKA-CORE-7012 MAJOR** Replaced fixed 0.3s sleep with event-based threading (`_mic_released`) for reliable device handoff.
* **ISKA-CORE-7019 PATCH** Fixed **Vosk/STT device deadlock** via a pause-and-resume signal system.
* **ISKA-CORE-7020 PATCH** Resolved query pile-up from rapid taps using a `_query_lock` and background thread speaking.

### [2.2.0] - 2026-05-09
* **ISKA-CORE-6004 MINOR** Implemented **Persistent Microphone Architecture** to remove interaction latency.
* **ISKA-CORE-6009 MINOR** Reduced mic calibration to 0.5s and moved it to a one-time startup "warmup" phase.
* **ISKA-CORE-6011 PATCH** Resolved **Vosk/STT Device Conflict** via a hardware "handshake" sleep.

### [2.1.0] - 2026-04-17
* **ISKA-CORE-3001 MAJOR** Migrated to the **Vosk engine** for 100% offline edge-inference listening.
* **ISKA-CORE-3002 MINOR** Implemented the **"Filipino Fix"** vocabulary locking for local phonetic signatures.

---

## [1.x.x] — CMS (Content Management)
*Focuses on the administrative dashboard, analytics logs, and database management.*

### [1.1.0] - 2026-04-24
* **ISKA-CORE-5001 MINOR** Implemented `query_logs` for **Full-Transcript Logging** of student interactions.
* **ISKA-CORE-5002 MINOR** Integrated **Session Tracking** using unique, timestamped IDs to group inquiries.
* **ISKA-CMS-5004 MINOR** Developed the **Student Analytics Dashboard** with messaging-style transcript modals.

### [1.0.0] - 2026-03-11
* **ISKA-CMS-1001 MAJOR** Built the file-based **SQLite architecture** for standalone campus operation.
* **ISKA-CMS-1002 MINOR** Developed **Flask-based CRUD endpoints** for kiosk data management.
* **ISKA-CMS-1004 MINOR** Built the **Bilingual (English/Filipino)** management interface.