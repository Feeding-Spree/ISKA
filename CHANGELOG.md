# Change Log

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.6.1] - 2026-05-13
### ISKA UI Hotfix — BMO Face Scaling

### Fixed

* **ISKA-UI-7025 PATCH** Resolved BMO face horizontal stretching caused by mismatched FACE_W and FACE_H dimensions — corrected from 340x300 to match the natural 5:3 aspect ratio of the PNG assets (800x480).
* **ISKA-UI-7026 PATCH** Scaled BMO face display size from 300x300 (square, distorted) → 310x186 (correct ratio) → 370x222 (final size) for better visual presence in the left panel.


### Changed

* **ISKA-UI-7027 MINOR** FACE_W and FACE_H constants are now ratio-correct at 370x222 (5:3). Formula documented in code: FACE_H = FACE_W × 0.6 for future scaling.

## [2.6.0] - 2026-05-13

### ISKA Frontend Integration & Stability Hardening
This milestone introduces the animated "BMO" frontend, resolves critical hardware race conditions in the Vosk/STT pipeline, and hardens the system for live kiosk deployment on the Raspberry Pi 4.

#### Added
* **ISKA-UI-7001 MAJOR** Integrated animated **BmoFaceWidget** with 13 distinct PNG states (idle, listening, thinking, etc.) and per-state frame delay cycling.
* **ISKA-UI-7002 MAJOR** Implemented **ChatMessage bubble system** — user queries appear right-aligned (Maroon), ISKA responses left-aligned (Gold), with synchronized timestamps.
* **ISKA-UI-7003 MINOR** Added full UI layout: PUP topbar with seal, welcome banner with accent bar, left panel, right chat panel, quick-topic chips, search input bar, and footer help button.
* **ISKA-UI-7004 MINOR** Added **2×2 Quick Info Cards** (Library, Registrar, Enrollment, Student Portal) — each fully clickable and dispatches queries directly to the backend.
* **ISKA-UI-7005 MINOR** Added **TAP TO SPEAK** button redesign featuring a gold background and mic emoji to match reference designs.
* **ISKA-UI-7006 MINOR** Added **EN/FIL language toggle** with visual active state on the left panel.
* **ISKA-CORE-7008 MINOR** Added `iska.service` systemd unit file for Raspberry Pi 4 auto-start on boot and auto-restart on crash.
* **ISKA-BACKEND-7009 MINOR** Added **Small Talk Interceptor** in `backend.py` — greetings and capability questions return hardcoded responses instantly, bypassing Ollama for higher speed.
* **ISKA-CORE-7010 MINOR** Added `_clear_chat()` — wipes all chat bubbles and restores greeting after farewell sequence, archiving the session to `query_logs`.

#### Changed
* **ISKA-CORE-7011 MAJOR** **Code Unification:** Merged `frontend.py` and `main.py` into a single unified ISKA class for cleaner kiosk deployment.
* **ISKA-CORE-7012 MAJOR** Replaced fixed 0.3s sleep with event-based threading (`_mic_released`) for more reliable device handoff.
* **ISKA-CORE-7013 MINOR** Optimized `KaldiRecognizer` initialization to run once at startup instead of per-interaction.
* **ISKA-BACKEND-7014 MINOR** Rewrote Augmented Path prompts with explicit negative examples to prevent Gemma 2B hallucinations.
* **ISKA-BACKEND-7015 MINOR** Implemented a **30-second Ollama timeout** using `threading.Event` to prevent indefinite kiosk freezes.

#### Fixed
* **ISKA-CORE-7018 PATCH** Resolved state-stuck issues where "Speaking..." remained after STT errors; all error paths now trigger `_reset()`.
* **ISKA-CORE-7019 PATCH** Fixed **Vosk/STT device deadlock** by pausing Vosk before STT listens and resuming via event signal.
* **ISKA-CORE-7020 PATCH** Fixed query pile-up from rapid taps using a `_query_lock` and background thread speaking.
* **ISKA-BACKEND-7021 PATCH** Corrected hallucinated fallback responses caused by model misinterpretation of topic guards.

#### Removed
* **ISKA-CORE-7023 MINOR** Removed legacy `ISKA_Core_Test` UI code and standalone `setup_raw_ui()`.
* **ISKA-CORE-7024 MINOR** Removed redundant search and generation logic from `main.py`.

---

## [2.5.0] - 2026-05-09

### ISKA Core & Backend: Semantic Rewrite & Hardware Optimization
This milestone represents a total architectural overhaul, moving from keyword matching to **Semantic Vector Search**. By decoupling logic from the UI and optimizing hardware persistence, the system now offers near-instant response times.

#### Added
* **ISKA-BACKEND-6001 MAJOR** Implement **Semantic Vector Search** using `SentenceTransformer (all-MiniLM-L6-v2)` for RAG and jailbreak detection.
* **ISKA-BACKEND-6002 MAJOR** Introduce **Adaptive Response Layer** with a three-path decision flow (Fast/Augmented/Fallback).
* **ISKA-BACKEND-6003 MINOR** Implement **Background Embedder Loading** and a "Layer 0" warmup guard to prevent startup freezes.
* **ISKA-CORE-6004 MINOR** Implement **Persistent Microphone Architecture** to eliminate "per-tap" latency and calibration delays.
* **ISKA-CORE-6005 MINOR** Added **Query Lock** threading to prevent race conditions during rapid user interactions.

#### Changed
* **ISKA-BACKEND-6006 MAJOR** **Full Separation of Concerns:** Moved AI/RAG/Jailbreak logic from `main.py` into a dedicated `IskaBackend` class.
* **ISKA-BACKEND-6007 MINOR** Refined **Jailbreak Detection** to use semantic intent (cosine similarity) instead of hardcoded keywords.
* **ISKA-BACKEND-6008 MINOR** Optimized Ollama: 60-token hard cap and temperature of 0.2 for deterministic answers.
* **ISKA-CORE-6009 MINOR** Reduced mic calibration to 0.5s and moved it to a one-time startup "warmup" phase.

#### Fixed
* **ISKA-CORE-6011 PATCH** Resolve **Vosk/STT Device Conflict** via a 0.3s hardware "handshake" sleep.
* **ISKA-BACKEND-6013 PATCH** Implemented `_db_cache` to ensure embeddings rebuild only when database schema changes.
* **ISKA-CORE-6014 PATCH** Fixed display bugs where successive queries would overlap in the Tkinter UI.

---

## [2.1.0] - 2026-04-24

### ISKA Core & Admin: Analytics & Session Intelligence
Introduced Student Analytics to monitor usage and review conversation transcripts through session-based tracking.

#### Added
* **ISKA-CORE-5001 MINOR** Implement `query_logs` table for full-transcript logging of STT and AI responses.
* **ISKA-CORE-5002 MINOR** Integrate **Session Tracking** using unique, timestamped IDs to group interactions.
* **ISKA-CORE-5003 MINOR** Implement **"Sleep Cues" (Manual Kill-Switch)** to instantly reset the kiosk on sign-off phrases.
* **ISKA-CMS-5004 MINOR** Introduce **"Student Analytics" Dashboard** with messaging-style Modals for session reviews.

---

## [2.0.0] - 2026-04-23

### ISKA Core System: Local Edge Inference & RAG Architecture
Transition to a fully sovereign, 100% offline AI system using Ollama and the Gemma 2B model.

#### Added
* **ISKA-CORE-4001 MAJOR** Perform **Full Offline Migration** using Ollama and Gemma 2B.
* **ISKA-CORE-4002 MAJOR** Implement direct **SQLite-to-LLM RAG pipeline**.
* **ISKA-CORE-4005 MINOR** Integrate **Real-Time Word Streaming** (threading) to prevent hardware freezes.

---

## [1.5.0] - 2026-04-17

### ISKA Core System: Vosk Integration & Hardware Optimization
Stabilizing audio hardware lifecycle and shifting to offline wake-word detection.

#### Added
* **ISKA-CORE-3001 MAJOR** Integrate **Vosk engine** as primary offline listener.
* **ISKA-CORE-3002 MINOR** Implement **"Filipino Fix"** via Vocabulary Locking.

---

## [1.1.0] - 2026-04-12

### ISKA Core System: Hybrid Architecture Implementation
Initial implementation of "ISKA" persona and neural voice interface.

#### Added
* **ISKA-CORE-2001 MAJOR** Implement **Hybrid RAG** with cloud fallback.
* **ISKA-CORE-2004 MINOR** Implement **Phonetic Dictionary** (`make_natural()`) for campus terminology.

---

## [1.0.0] - 2026-03-11

### ISKA Local Content Management System (CMS)
Establishment of the administrative hub for Raspberry Pi 4.

#### Added
* **ISKA-CMS-1001 MAJOR** Implement file-based **SQLite architecture**.
* **ISKA-CMS-1002 MINOR** Develop **Flask-based CRUD endpoints**.
* **ISKA-CMS-1004 MINOR** Build **Bilingual (English/Filipino)** management interface.