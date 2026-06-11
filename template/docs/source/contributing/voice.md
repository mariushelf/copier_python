<!-- Canonical meta-layer shipped by the update-docs skill. This file is dropped verbatim into docs/source/contributing/. Edit the canonical copy in the skill's assets/meta/, not the per-repo copy. -->

# Voice and tone

The authoritative voice register for all documentation under `docs/source/`.
The [documentation guide](documentation_guide.md) — and the repository's agent
instructions (`AGENTS.md` or similar), where present — defer to this file: the
guide covers structure and conventions, this file covers voice.
It is the long-term home for voice policy — recurring voice issues found in
review are resolved by updating the rules here.

## Purpose

Documentation is read by library or service users, maintainers, and AI
agents — three audiences that share one thing: they need to act on what is
written, not be entertained by it. The voice is tuned for that: a sober
technical register that does not waste words and does not adopt false
familiarity with the reader.

## The dial

The target is roughly the temperature of the Stripe API docs or the Polars
user guide. Not corporate-stiff, not chatty.

Concretely, voice that is in-band:

- Direct definitions and pointers (*"This section covers X."*).
- Noun-heavy constructions for invariants (*"Each page is self-contained."*).
- Passive voice where the library is the actor and the reader is not
  (*"the invariants that must hold"*, not *"the invariants you must not break"*).
- One short, specific verb where a longer phrase would tempt cute connectors.

Voice that is out of band:

- Familiarity tics: *"your code does the math"*, *"jump straight to"*,
  *"from there you can browse"*, *"learn how to"*.
- Collective-noun warmth: *"two big ideas"*, *"a few moving parts"*,
  *"the library handles everything"*.
- Colloquial replacements for technical terms: *"gotchas"* (use "edge cases"
  or "common pitfalls"), *"goes red"* (use "fails"), *"folks"* (do not use).
- Cheerleading: *"This is where the magic happens."* Documentation describes;
  it does not sell.

## Rules

### 1. Do not use the word "people"

In an audience-framing sentence, replace *"people who maintain the library"*
with *"library maintainers"*, *"anyone maintaining the library"*, or
*"those maintaining the library"*. The noun form ("maintainers", "authors",
"developers") is preferred when it exists; "anyone who" / "those who" are
the fallbacks.

### 2. Avoid second-person familiarity

Second person ("you", "your") implies a personal relationship the
documentation does not have. Most second-person sentences can be rewritten
in passive voice or in terms of the actor:

- *"You can read about what those ideas mean in Philosophy."* →
  *"Philosophy explains the reasoning."*
- *"Your code decides which records to process."* →
  *"Callers decide which records to process."*
- *"If you are new to the library, start with X."* →
  *"X is the recommended starting point."*
- *"The invariants you must not break."* →
  *"The invariants that must hold."*

Exception: how-to instructions that genuinely address the reader as a
guide author may use second person ("you can override the default by
…"). Even there, prefer imperative forms ("override the default by…") where
they read naturally.

### 3. Cut familiarity tics

Phrases that read as a podcaster speaking to a listener should be cut:

- *"From there, you can…"* → *"The remaining pages cover…"*.
- *"Jump straight to…"* → *"… is the entry point for…"*.
- *"Browse the catalog of…"* → *"… catalog of…"* or *"covers the…"*.
- *"Learn how to…"* → *"… how to…"* or just describe the page contents.
- *"Reading order is loose."* → *"Each page is self-contained."*.

### 4. No colloquial substitutes for technical terms

- *"gotchas"* → *"common pitfalls"* or *"edge cases"*.
- *"the job goes red"* → *"the job fails"*.
- *"a hairy edge case"* → *"a non-trivial edge case"* or just *"an edge case"*.
- *"under the hood"* → *"internally"* or *"in the implementation"*.

### 5. No marketing/cheerleading

The documentation does not motivate the reader to use the library. It
describes what the library is and how to use it. Sentences that read as
trying to *convince* the reader belong on a marketing page, not in
reference documentation.

- *"The library's two big ideas: caching and processing."* →
  *"The library draws a hard line between two responsibilities."*
- *"Everything else, the library handles."* →
  *"… sit on the library side of that line."*

### 6. Italics for definitional emphasis only

Italics emphasize the *what* of a concept the first time it is introduced,
or call out a positional metaphor ("link *up* to concept pages"). Italics
are not used for general emphasis ("this is *very* important") — if a
sentence needs that kind of emphasis, rewrite it.

### 7. Direct readers without leading them

Documentation routes readers to other pages by stating what the page covers,
not by inviting them with second-person verbs:

- *"You'll want to read X next."* → *"X covers …"*.
- *"Check out Y for more."* → *"Y enumerates …"*.
- *"See Z if you're curious about W."* → *"Z explains W."*.

## Worked examples

Each row pairs a before/after rewrite with the rules it invokes.

| File | Before | After | Rules invoked |
|---|---|---|---|
| `docs/source/index.md` | *"The library's two big ideas: your code does the math."* | *"The library draws a hard line between two responsibilities. **Adapters** connect: sources, sinks, and transforms."* | 2, 3, 5 |
| `docs/source/concepts/index.md` | *"If you are orienting for the first time, X and Y are good entry points."* | *"X and Y are the recommended starting points."* | 2, 3 |
| `docs/source/guides/index.md` | *"people who write adapters and configs … not people maintaining the library itself"* | *"anyone authoring adapters and configurations … as distinct from maintaining the library itself"* | 1, 2 |
| `docs/source/architecture/index.md` | *"people who maintain the library"* | *"library maintainers"* | 1 |
| `docs/source/reference/index.md` | *"common gotchas"* | *"common questions and edge cases"* | 4 |
| `docs/source/architecture/implementation/index.md` | *"the invariants you must not break"* | *"the invariants that must hold"* | 2 |

## When to break a rule

Rules 1–7 describe the default register. They are not a uniform. Three
situations override them:

1. **The user-facing CLI**: terminal output, error messages, and short hints
   may use second person if it makes the message clearer (*"You must specify
   a config file."*). Reference documentation about the CLI follows the
   default register.

2. **Quickstart and tutorial pages**: when the reader is being walked
   through a concrete sequence of steps, second-person imperatives ("now
   call `process_records()`") are sometimes the most direct form.
   Even then, prefer imperatives over "you can".

3. **A figurative phrase that earns its place**: if a sentence is concretely
   improved by one figurative phrase that no rewrite captures, keep it. Be
   ready to defend the choice in review.

The principle: when in doubt, sober wins.
