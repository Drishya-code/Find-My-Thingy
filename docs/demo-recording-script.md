# 60–90 second demo recording plan

Use the synthetic [demo sample](demo-sample.md). Capture a real run of the app; do not present these steps as completed until you have recorded them.

## Before recording

- Start Ollama and confirm the model list includes gemma3:4b.
- Double-click `Start-FindMyThingy.bat`; wait for model status to say **ready**.
- Use an empty or disposable local data directory. Do not show personal files, terminal secrets or unrelated documents.
- Upload demo-sample.md and confirm it is indexed before starting the timed take.
- Record at a readable desktop resolution.

## Script and shot list

| Time | Screen/action | Narration |
|---|---|---|
| 0–10 s | Show Overview with local Gemma readiness. | “Find My Thingy is a local-first memory assistant. It turns documents you choose into a searchable personal library.” |
| 10–24 s | Open Documents and add demo-sample.md; show the success result and indexed entry. | “Documents are extracted and indexed on this computer. The sample contains a study schedule and an explanation of binary search.” |
| 24–40 s | Open Ask; ask “How does binary search work?” Expand the returned source citation. | “For a question, the app retrieves relevant passages, then asks local Gemma 3 4B to answer from those passages. Source metadata comes from the index.” |
| 40–53 s | Ask “What is the capital of Iceland?” Show the insufficient-information response. | “When the saved library does not contain an answer, retrieval can decline instead of pretending it found evidence.” |
| 53–66 s | In Ask, say “Remember that my demo project codename is Test Nebula.” Then open Memory library and show the persisted fact. | “I can save a personal fact directly to local memory, then manage it in the memory library.” |
| 66–78 s | Open Settings and show local model/storage information. | “Documents, vectors and structured memories remain in local storage. There is no account flow.” |
| 78–90 s | Hold on the interface and end. | “Find My Thingy helps make personal notes easier to find, while keeping retrieval and the model workflow on the device.” |

If any step fails, stop and fix the local setup or edit the narration to match real behavior. Do not present a simulated answer as a live Gemma result.
