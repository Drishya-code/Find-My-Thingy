# Hackathon submission pack

This is a local draft only. It has not been published or submitted. Replace bracketed placeholders with truthful personal details and links, then review the current challenge rules on DEV before submitting.

## Project details

- **Project:** Find My Thingy
- **Tagline:** Your personal memory, ready when you need it.
- **Short description:** A local-first personal memory assistant that indexes your PDFs, text files and Markdown notes, then uses Gemma 3 4B on your device to answer questions with citations to source passages.
- **Suggested repository description:** A local-first personal memory assistant using Gemma 3 4B, Ollama, FastAPI, React and ChromaDB to answer questions from your own documents with source citations.
- **Suggested article title:** Find My Thingy: a local-first memory assistant powered by Gemma 3 4B
- **Suggested DEV tags:** gemma, ai, python, react, opensource
- **Project links:** GitHub: https://github.com/Drishya-code/Find-My-Thingy (verify repository visibility before sharing); demo video: [ADD REAL VIDEO URL, IF RECORDED]; live demo: [ADD REAL DEPLOYMENT URL, IF ONE EXISTS]. Do not imply a deployment exists; this project is designed to run locally.

## Feature list

- Local PDF, TXT and Markdown ingestion with duplicate detection.
- Page-aware text extraction, chunking and local embeddings.
- Persistent semantic retrieval using ChromaDB.
- Grounded question answering through Ollama and Gemma 3 4B.
- Source passages with filenames and PDF page references.
- Refusal when retrieval does not find sufficiently relevant evidence.
- Best-effort fact and definition extraction into a local memory library.
- Explicit “remember this” personal facts saved to SQLite, searchable in chat and manageable in Memory Library.
- Document filename search and deletion, memory search and deletion, local settings and responsive dark UI.
- No account, subscription, hosted database or hosted LLM API.

## DEV article draft

# Find My Thingy: a local-first memory assistant powered by Gemma 3 4B

> **Before publishing:** Replace the bracketed personal story, identity, consent and link placeholders. Keep only statements you can personally verify. This draft does not claim an outside deployment, user feedback or a finished recording.

### The problem I wanted to address

Notes, course materials and project documents accumulate faster than people can remember where a useful detail was written. Exact-word search can miss a question phrased differently. Sending private notes to a hosted AI service can also be the wrong trade-off for personal material.

**[PERSONAL STORY PLACEHOLDER — Add the real context for why you built this. If the project was prompted by a friend’s needs, describe only what they actually said or experienced, with their permission. Do not add identifying details without consent. If no friend was involved, replace this section with your own truthful motivation.]**

I built Find My Thingy to explore a practical alternative: keep documents and the AI workflow on one trusted computer, retrieve relevant excerpts, and show the source behind an answer.

### Who it is for

Find My Thingy is intended for a single person who wants to organize study notes, research PDFs, reference material or project documents and ask questions across that collection. It is not designed as a team workspace or hosted subscription product.

**[PERSONAL DETAILS PLACEHOLDER — Add your name, location, background, or the specific audience you personally built it for, only if you want to share those details.]**

### What it does

The current app accepts PDF, TXT and Markdown files. It extracts text locally, keeps page numbers for PDFs, breaks text into overlapping passages and creates embeddings with all-MiniLM-L6-v2. ChromaDB stores those vectors and their document metadata. SQLite keeps document records, optional extracted facts and explicit personal facts a user asks the assistant to remember.

When I ask a question about documents, the backend retrieves the nearest passages and filters them by a relevance threshold interpreted using the distance metric configured on the Chroma collection. It sends the question and those excerpts to Gemma 3 4B through Ollama running locally. The model is asked to answer only from those excerpts and use their bracket references. The API returns source filename, passage and page from the index, so displayed source information is not invented by the model. When retrieval finds no sufficiently relevant passage, the app returns an insufficient-information response. Personal questions search the explicit saved-fact library first, and explicit “remember that…” instructions are persisted before the assistant confirms.

### Why local-first AI matters here

Personal documents can include coursework, plans and notes that I do not want to upload to a hosted model just to search them. Local inference gives the user control over where those documents and queries go. It also makes the privacy boundary easier to explain: source files, embeddings, vector search and generation are designed to run on the user’s computer.

“Local” does not mean setup-free. Ollama and Gemma must be installed, and the embedding model may need to be downloaded once. Inference speed and answer quality depend on hardware and the retrieved passages.

### How Gemma 3 4B fits in

Gemma handles language generation after retrieval. It receives a question and a small set of reference excerpts rather than the whole document library. The system prompt tells it to treat document text as untrusted input, answer only from evidence, and decline when evidence is insufficient. Retrieval, source metadata and the refusal threshold are handled by application code around the model.

This arrangement is useful but not a guarantee of correctness. A language model can misread evidence, and a relevance threshold can omit a useful passage. Source inspection and careful review still matter.

### Building the pipeline

The frontend is React, TypeScript and Vite. It calls a FastAPI backend. PyMuPDF extracts text from PDF pages; plain text and Markdown use UTF-8 decoding. The backend chunks extracted text, creates normalized sentence-transformer embeddings and persists them in ChromaDB. SQLite stores local document and memory records. Ollama exposes the local Gemma model over its API.

The project keeps its stages separate so upload, extraction, embedding, retrieval, generation and citation metadata can be inspected independently. A duplicate file is detected by SHA-256. Document deletion removes its uploaded file, vector records and associated memories.

### Challenges and lessons

- **Citations need a trusted source.** Filename and page metadata stay beside each indexed passage and are returned by the backend rather than invented by the model.
- **Retrieval and generation are different failure points.** A fluent answer does not prove that the right evidence was retrieved, so the UI exposes source passages and the backend can decline before generation.
- **A local workflow has setup costs.** Python and Node packages, Ollama, Gemma and the embedding cache all need installation. Pinned frontend dependencies and documented commands make setup more repeatable.
- **Optional extraction should not jeopardize the source.** Memory extraction is best effort; the uploaded document and its index remain the main record.
- **Local-first changes the threat model, not the need for one.** The app has no login and assumes a trusted local device. It is not safe to expose as-is to an untrusted network.

**[PERSONAL LEARNING PLACEHOLDER — Add a specific obstacle you encountered and what you changed, based on your actual development experience.]**

### Current state and limitations

The project currently supports text-based PDFs, TXT and Markdown. Scanned PDFs need OCR, indexing is synchronous, browser chat history is session-only, and the retrieval cutoff is a simple threshold that may need tuning. The optional memory extractor can miss facts or produce imperfect summaries, so source passages should be checked.

**[TEST/DEMO PLACEHOLDER — Add only results you personally rerun and observe. Include your actual device/model setup if helpful. Do not claim a video, screenshots, deployment or external users unless those exist.]**

### What I would add next

Useful next steps include a background indexing flow for larger files, clearer visibility into indexing failures, configurable retrieval behavior, stronger provenance for extracted memories, and optional local OCR. Any future networked version would need a deliberate authentication and security design before deployment.

### Try it

The source and local setup instructions are here: **https://github.com/Drishya-code/Find-My-Thingy**.

To run it, install the documented Python and Node dependencies, start Ollama with Gemma 3 4B available, start the FastAPI backend and Vite frontend, then add a document. No hosted demo is claimed here.

**[CLOSING PLACEHOLDER — Add a short personal reflection or invitation in your own voice.]**

## Final submission checklist

- [ ] Replace every bracketed placeholder with truthful personal details, or remove the section.
- [ ] Confirm any friend’s story is accurate and shared with their consent.
- [ ] Review the current DEV challenge rules, deadline, eligibility, required tags and article format.
- [ ] Run the current code and verify every claim about Gemma, citations and refusal.
- [ ] Capture real screenshots; follow docs/screenshots/README.md and inspect them for private data.
- [ ] Record and watch the real demo video; edit the narration to match actual behavior.
- [ ] Add only real GitHub/video/deployment links. There is no hosted deployment unless you create one.
- [ ] Inspect Git status and ensure no personal documents, databases, caches, secrets or credentials are included.
- [ ] Review GitHub repository description and visibility yourself. Ask for approval before making it public.
- [ ] Proofread and submit the article personally on DEV. This draft has not been published or submitted.
