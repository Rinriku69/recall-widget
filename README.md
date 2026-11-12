# recall-widget

A small, always-on-top flashcard window for Windows. It shows a question, gives you a few seconds to recall the answer yourself, then reveals it and moves on to the next card. Cards live in a plain markdown file you edit with any text editor.

It's built for things you keep forgetting: command flags, config rules, syntax. Keep it in a corner of the screen and let it quiz you while you work.

## Features

- **Active recall cycle**: question for 10 seconds, then the answer for 20 seconds, then the next card. Click to skip ahead.
- **Shuffled deck**: every card is shown once before the order is reshuffled, so nothing repeats back to back.
- **Live reload**: save `facts.md` and the new cards show up on the next card. No restart.
- **Code formatting**: text in `backticks` is shown in a code font.
- **Stays out of the way**: borderless, no taskbar button, remembers where you left it.
- **Global hotkey**: `Ctrl+Alt+N` brings the window to the front from any program.
- **Single instance**: launching it again brings up the running window instead of opening a second one.

## Requirements

- Windows 10 or 11
- To run from source: Python 3.10 or newer, with tkinter (included in the python.org installer). No other dependencies.
- To run the exe: nothing.

## Getting started

### Option 1: the exe (no Python needed)

1. Download `recall-widget.exe` from the [Releases](../../releases) page.
2. Put `facts.example.md` from this repo in the same folder as the exe, and rename it to `facts.md`.
3. Double-click `recall-widget.exe`.

Windows SmartScreen may warn that the app is from an unknown publisher, because the exe isn't code-signed. Choose "More info", then "Run anyway".

### Option 2: from source

```
git clone https://github.com/<your-username>/recall-widget.git
cd recall-widget
copy facts.example.md facts.md
```

Then double-click `recall_widget.pyw`. The `.pyw` extension runs it with `pythonw`, so no console window opens.

## Controls

| Action | What it does |
|---|---|
| Left-click | Reveal the answer, or go to the next card |
| Left-drag | Move the window (the position is saved) |
| Right-click | Menu: Next, Open notes file, Always on top, Close |
| `Ctrl+Alt+N` | Bring the window to the front from anywhere |

## Writing cards

Cards go in `facts.md`, next to `recall_widget.pyw` (or next to the exe).

```markdown
# My flashcards

## What does `git status` show
Which files changed since the last commit, which are staged,
and which git isn't tracking yet.

## Another question
Its answer. Every line until the next "## " belongs to this card.
```

- Each `## ` heading is one card. The heading is the question.
- Everything under it, up to the next `## `, is the answer.
- Text in `backticks` is shown in a code font. Other markdown (bold, lists, links) is shown as plain text.
- The `# ` title and HTML comments (`<!-- ... -->`) are ignored, so you can leave notes to yourself in the file.

`facts.md` is in `.gitignore`, so your own cards stay out of the repo.

## Settings

Timing and size are constants near the top of `recall_widget.pyw`:

| Constant | Default | Meaning |
|---|---|---|
| `QUESTION_SECONDS` | `10` | How long the question is shown before the answer |
| `ANSWER_SECONDS` | `20` | How long the answer is shown before the next card |
| `WIDTH` | `380` | Window width in pixels |
| `SINGLE_INSTANCE_PORT` | `47613` | Local port used to detect a running instance |

The window position and the "Always on top" setting are saved in `.recall_widget_state.json`.

## Building the exe

```
pip install pyinstaller
python -m PyInstaller --noconsole --onefile --name recall-widget recall_widget.pyw
```

The result is `dist/recall-widget.exe`. It looks for `facts.md` in its own folder, so ship the two together.
