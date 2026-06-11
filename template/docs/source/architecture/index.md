# Architecture

How the project is built — its structure, key components, and the reasoning
behind major design decisions. This section is aimed at maintainers and
contributors who need to understand the internals.

```{toctree}
:maxdepth: 2

implementation/index
```

## Overview

<!-- EDIT: Replace the placeholder diagram below with one that reflects the
actual system. Add prose describing the components and their interactions. -->

```{mermaid}
graph TD
    A[Entry point] --> B[Core]
    B --> C[Adapter A]
    B --> D[Adapter B]
```
