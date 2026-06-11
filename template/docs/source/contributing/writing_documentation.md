<!-- Canonical meta-layer shipped by the update-docs skill. This file is dropped verbatim into docs/source/contributing/. Edit the canonical copy in the skill's assets/meta/, not the per-repo copy. -->

# Writing documentation

The procedure for adding or changing a page under `docs/source/`. Each step
links to the reasoning in the [documentation guide](documentation_guide.md).

1. **Find the page's home.** Place it by audience first, then document type.
   A concept goes in `concepts/`, a task in `guides/`, `operations/`, or
   `contributing/`, exact facts in `reference/` or the glossary. See *How the
   documentation is organized* in the [documentation guide](documentation_guide.md).
2. **Pick the page shape.** Cover the ingredients for that type as flowing
   prose, not a boilerplate with named sections. See *Page shapes* in the
   [documentation guide](documentation_guide.md).
3. **Match the voice.** Follow [Voice and tone](voice.md): sober, direct, no
   second-person familiarity, no marketing.
4. **Ground every claim in code.** Verify architecture and behavior against
   current source. Do not write what cannot be verified.
5. **Label the planned.** Describe what the code does today; mark
   designed-but-unimplemented behavior with a self-contained `{caution}`
   admonition stating what is unbuilt and where the design appears.
6. **Cross-reference correctly.** Link in-tree pages with the MyST `{doc}` role
   and a source-root-absolute docname — `` {doc}`/concepts/cache` `` — and add
   the new page to its section `toctree`.
7. **Verify the build.** Run `make docs-strict` (warnings-as-errors) and
   `make test-docs` before committing; `make docs-linkcheck` when external
   links changed.

For the reasoning behind any step, see the
[documentation guide](documentation_guide.md).
