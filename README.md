# StudyBuddy

Turn course PDFs into Anki flashcards, entirely on your own machine.

StudyBuddy reads a PDF or pasted notes, splits the text into chunks, and asks a locally running Gemma model to write flashcards from it.
You review and edit the cards, then export them to Anki or CSV.
Nothing is uploaded anywhere.

## Why local

Course material is often paid content whose terms forbid uploading to third-party services.
Lecture notes are personal.
Running the model locally means the PDF, the extracted text, and the generated cards never leave the laptop.

It also costs nothing to run.
Generating cards for a few hundred pages through a hosted API adds up; here the only cost is CPU time.

And it works offline.
Once the model is pulled, the app runs on a train, in a library, or anywhere else without a connection.

## What it does

Upload a PDF or paste notes.
Pick how many pages to process per batch and optionally a card target to stop at.
Press Start, and the app works through the document batch by batch without further clicks.

Cards accumulate as it goes.
You can pause at any point, or just start editing a card, which pauses generation automatically.

When you are done, review every card, deselect the weak ones, fix the wording, and export.

## Requirements

- Python 3.9 or newer
- [Ollama](https://ollama.com), either installed directly or running in Docker
- Roughly 3 GB of free RAM for the default model

## Setup

Pull the model.

If Ollama runs in Docker:

```bash
docker exec -it ollama ollama pull gemma2:2b
```

If Ollama is installed directly:

```bash
ollama pull gemma2:2b
```

Then install the Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the app:

```bash
streamlit run app.py
```

It opens at `http://localhost:8501`.

## Configuration

Two environment variables, both optional:

| Variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_HOST` | `http://localhost:11434` | Where Ollama is listening |
| `OLLAMA_MODEL` | `gemma2:2b` | Which model to use |

If Ollama runs in Docker on the same machine with port 11434 published, the defaults work unchanged.

If the app itself runs in a container alongside Ollama, set `OLLAMA_HOST=http://ollama:11434`.

## Using the output

### Anki

Install [Anki](https://apps.ankiweb.net), open it, and choose File then Import.
Select the downloaded `.apkg` file.

Do not unzip the `.apkg`.
It is an import package, and its contents are not meant to be read directly.

Anki handles the spaced repetition scheduling from there.
It also syncs to AnkiDroid on Android and AnkiMobile on iOS.

### CSV

The CSV export has one row per card, question first, answer second.
It imports into Quizlet, opens in any spreadsheet, and is readable on a phone as is.

### Study tab

For a quick session without installing anything, the Study tab shows one card at a time with a reveal button.
It is not spaced repetition, just a way to run through the deck immediately after generating it.

## How it works

```
PDF
  -> text extraction (pypdf)
  -> chunking, with low-value chunks filtered out
  -> Gemma via Ollama, one call per chunk
  -> JSON validation and deduplication
  -> review and edit
  -> Anki .apkg (genanki) or CSV
```

| File | Role |
| --- | --- |
| `app.py` | Streamlit UI, batching, review, study mode |
| `extract.py` | Page-level text extraction from PDFs |
| `chunk.py` | Splitting text and filtering out unusable chunks |
| `generate.py` | Prompting Gemma and validating its JSON |
| `export.py` | Anki package and CSV output |

### Chunk filtering

Textbook PDFs carry a lot of text that cannot become a flashcard: tables of contents, reference lists, page headers, figure captions.
Each one of those would otherwise cost a full model call.

`chunk.py` drops chunks that are too short, mostly non-alphabetic, dense with years, or heavy with sentence-final periods relative to word count.
On a real textbook this removes a noticeable share of the work before the model sees anything.

### Handling small-model output

A 2B model is small enough to need help producing usable structured output.

The prompt asks for a JSON object containing a `flashcards` array rather than a bare array, because Ollama's JSON mode biases strongly toward starting with an object and a bare-array request tends to come back as a single card.

The parser accepts several shapes: a bare array, an object under any of a few plausible keys, or a single card object.
Each card is then validated for type, length, and a few known bad patterns, and near-duplicate questions are removed.

If a chunk still yields fewer than two cards, it is split once at a sentence boundary and each half is retried.

## Tuning

If generation is slow, the options in `generate.py` are where to look.
`num_ctx` controls how much context is allocated per call, and larger values cost time even when the input is short.
`num_predict` caps the output; too low and the JSON is truncated mid-array, which produces zero cards rather than fewer.

Larger chunks mean fewer total calls and usually less wall time overall, since each call pays the prompt cost regardless of how much text follows it.

If card quality is poor, the lever is the example in the prompt rather than the rules.
Small models copy the shape of the example far more reliably than they follow instructions about counts.

## Model choice

`gemma2:2b` is the default because it fits comfortably in 8 GB of RAM and produces consistent output for this task.

`gemma3:1b` is faster and smaller but noticeably less stable, with more vague questions and occasional malformed text.

`gemma2:9b` produces better cards but wants more memory than many laptops have free.

Set `OLLAMA_MODEL` to switch, and pull the model first.

## Troubleshooting

**Cannot reach Ollama.**
Check the container is running with `docker ps` and that port 11434 is published.
`curl http://localhost:11434/api/tags` should return JSON.

**Model not found.**
Pull it inside the container, not on the host, if Ollama is containerised.

**Zero cards from a chunk that clearly has content.**
Usually truncated output.
Print `response.get("done_reason")` in `generate.py`; `length` confirms it, and raising `num_predict` fixes it.

**No usable chunks found.**
The chunk filter may be too aggressive for how your PDF extracts.
The trailing-period rule is the usual cause when extraction puts one sentence per line.

## License

This project is released into the public domain under [The Unlicense](https://unlicense.org).