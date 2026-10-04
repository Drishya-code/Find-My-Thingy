# Find My Thingy architecture

## Overview

Find My Thingy is a local-first, single-user application. The React/Vite frontend calls a FastAPI service on the same machine. Persistent user data is under storage/; the app does not use a hosted database or hosted language-model API.

## Data flow

Browser (React + Vite) → local FastAPI API → file validation and text extraction → overlapping page-aware chunks → local all-MiniLM-L6-v2 embeddings → persistent ChromaDB.

For questions, the API embeds the query and retrieves passages from ChromaDB. It sends only those passages and the question to local Ollama running Gemma 3 4B. The API returns the answer together with citations built from stored passage metadata.

## Document ingestion

1. The API accepts PDF, TXT and Markdown files up to the configured size limit. A SHA-256 digest prevents duplicate uploads.
2. Text is extracted locally. PDF extraction preserves the one-based page number; scanned pages without text are rejected because OCR is not implemented.
3. Text is split into overlapping word chunks. The configured sentence-transformer model embeds the chunks locally.
4. ChromaDB stores vectors with document ID, filename, page and chunk index. SQLite stores document metadata and extracted memories.
5. Gemma memory extraction is optional and best effort; a model extraction failure does not discard an otherwise indexed document.

## Question answering

1. The API embeds the question and queries ChromaDB for the nearest passages.
2. The API reads Chroma's collection metric and converts returned distances accordingly (cosine/inner-product distance or squared L2 distance); a configurable minimum relevance refuses weak matches.
3. Only retrieved excerpts and the question are sent to local Ollama. Excerpts are explicitly treated as untrusted content in the prompt.
4. Gemma is instructed to answer only from those excerpts and cite their bracket numbers. The API strips citation markers outside the retrieved result range.
5. Citation filenames, page numbers and displayed source passages come from ChromaDB metadata and are returned separately from the generated answer.

## Local data and configuration

- storage/uploads/: source files; ignored by Git.
- storage/recall.sqlite3: SQLite database; ignored by Git. The legacy filename is intentionally retained so existing local data remains visible.
- storage/chroma/: vector index; ignored by Git. The collection retains its legacy internal name for compatibility.
- storage/models/: local embedding cache; ignored by Git.
- Root .env: backend settings, described by ../.env.example.
- frontend/.env: optional frontend API URL, described by ../frontend/.env.example.

Never commit local databases, uploaded documents, model caches, virtual environments, dependency folders or real environment files.

## Trust and limitations

The product is for a trusted local device and has no authentication. Do not expose the API to an untrusted network without adding access control and a threat model. Prompt instructions reduce risk from malicious document text but do not make model output a security boundary. Scanned PDFs are unsupported, uploads are indexed synchronously, and chat history is kept only in the browser session.

## Main code areas

- frontend/src/App.tsx: routed screens and user interactions.
- frontend/src/styles.css: dark theme, lime accent and responsive layouts.
- backend/app/api/routes.py: health, upload, document, chat, memory and dashboard API.
- backend/app/services/: extraction, chunking, embeddings, vector search, Ollama and memory extraction.
- backend/app/database/sqlite.py: local SQLite schema and connection helpers.
- backend/app/core/config.py: environment-backed backend configuration.

## Explicit personal memories

An explicit request such as “Remember that I prefer dark mode” is detected before document retrieval. The fact is deduplicated and committed to a dedicated `personal_memories` SQLite table in the existing `recall.sqlite3` database. The confirmation is returned only after the saved row is verified. The Memory Library combines these user facts with optional document-extracted facts, and chat questions matching a personal fact search those saved facts before Chroma document retrieval. Personal memory citations point to the saved fact itself.
