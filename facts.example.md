# My flashcards

<!--
Copy this file to facts.md (next to recall_widget.pyw or recall-widget.exe) and edit it.

Format:
  - Each "## " heading is one card. The heading is the question (shown first).
  - Everything under it, up to the next "## ", is the answer.
  - Text in `backticks` is shown in a code font. Other markdown is shown as plain text.
  - This comment block and the "# " title above are ignored.
Save the file and the widget picks up the changes on the next card. No restart needed.
-->

## What does active recall mean
Trying to pull an answer from memory before looking at it.
It strengthens memory more than rereading, which is why the widget shows the question first and waits before revealing the answer.

## What does `git status` show
Which files changed since the last commit, which are staged, and which git isn't tracking yet.

## `cp -r src dst` vs `cp -r src/. dst/`
`cp -r src dst` (when `dst` exists) copies the folder itself, giving `dst/src/`
`cp -r src/. dst/` copies only what's inside `src` into `dst`

## How do you write a card with a multi-line answer
Just keep writing lines under the heading.
Every line until the next `## ` belongs to this card's answer.
