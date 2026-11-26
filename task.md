# TASK: Build the `ssjs-frmk` AI Skills Package (npm) with Orchestrator

> **Audience:** an autonomous coding agent (Qwen via OpenCode) with read access to the `ssjs-frmk` source repository.
> **Goal:** scan the repository, learn the framework, and produce an installable npm package of agent skills plus a small deterministic CLI and an orchestrator skill. Developers use it to build `coras-*` based Angular screens from text requirements or Figma exports, using TDD (Jest), and the agent must verify the app runs and iterate until it does.
> **Read this whole file once before starting. Then work phase by phase. Never skip the checkpoints.**

---

## 0. Rules of engagement (MUST follow throughout)

### 0.1 Safety and scope
1. **The framework repository is READ-ONLY.** Never edit, format, commit to, or delete anything inside it. Work only in the new output directory `./ssjs-ai-pack/` (create it next to the repo, not inside it).
2. **No secrets.** Never print, store, or copy tokens, client secrets, `.env` values, Apigee keys, git tokens or SSO config values into any generated file. Record only the *names/shape* of config (e.g. `apigee.baseUrl: string`), never real values. If a file contains secrets, note its path in `discovery/secret-locations.md` (path only) and move on.
3. **No network use** other than the internal npm registry if explicitly configured. Do not download anything from the internet. If something cannot be done offline, write it under "Blocked items" in `PROGRESS.md` and continue.
4. **Do not invent.** Every fact about the framework (selector, input name, type, default, service method, provider name) must come from a source file you actually read. Each catalog entry must carry a `source` field (file path + line range). If you cannot find something, write `"unknown"` and add it to `discovery/open-questions.md`. A wrong catalog entry is worse than a missing one.
5. Framework name is `ssjs-frmk`. Component selectors use the prefix `coras-` (e.g. `coras-input`, `coras-dropdown`). Verify the actual prefix in code; if it differs in places, record every variant.

### 0.2 Working method (you have limited context, so work in small, persistent steps)
1. After every unit of work, **write results to disk** (never keep large results only in your context).
2. Maintain `ssjs-ai-pack/PROGRESS.md`: a checklist of every phase and sub-task with status `[ ]`, `[~]`, `[x]`, and notes. Update it after every sub-task. If you are restarted, read `PROGRESS.md` first and resume from the first unchecked item.
3. For bulk work (50+ components), **write and run scripts** (Node + `ts-morph`/TypeScript compiler API, or `grep`/`find`) to extract facts, then **manually verify a sample**. Do not hand-read 50 components into context.
4. Process components in **batches of 5**. After each batch: write the catalog entries, run the schema validator (Phase 2), fix errors, tick the checklist.
5. Prefer **short, example-heavy** skill text. Your target models are small; long prose degrades results.
6. When blocked or ambiguous: choose the most conservative option, record the assumption in `ASSUMPTIONS.md`, and continue. Do not stop to ask unless every remaining task depends on the answer.

### 0.3 Definition of Done (global)
- [ ] `ssjs-ai-pack/` contains a publishable npm package (Phase 10) and `npm pack --dry-run` succeeds.
- [ ] All catalogs validate against their JSON schemas with zero errors.
- [ ] All skills pass the skill linter (Phase 9) with zero errors.
- [ ] The 12 acceptance scenarios in Phase 11 are written, and each has a recorded dry-run result.
- [ ] `PROGRESS.md`, `ASSUMPTIONS.md`, `discovery/open-questions.md` are complete and current.
- [ ] No secrets, no absolute local paths, no references to files outside the package.

---

## 1. Output layout (create exactly this skeleton first)

```
ssjs-ai-pack/
├─ PROGRESS.md
├─ ASSUMPTIONS.md
├─ discovery/                    # Phase 1 outputs (internal notes, not shipped)
│  ├─ repo-map.md
│  ├─ environment.md
│  ├─ conventions.md
│  ├─ secret-locations.md
│  └─ open-questions.md
├─ package/                      # THE npm package (everything shipped lives here)
│  ├─ package.json
│  ├─ README.md
│  ├─ CHANGELOG.md
│  ├─ bin/ssjs-ai.js             # CLI entry
│  ├─ cli/                       # CLI command implementations (plain Node, minimal deps)
│  ├─ schemas/                   # JSON Schemas (catalogs, screen-spec, skill-lint)
│  ├─ catalog/                   # generated knowledge (Phases 2–5)
│  │  ├─ components.json
│  │  ├─ services.json
│  │  ├─ guards-interceptors.json
│  │  ├─ tokens.json
│  │  ├─ mapping.json            # design-node -> coras component rules
│  │  └─ archetypes.json
│  ├─ templates/                 # code templates with {{placeholders}}
│  │  ├─ archetypes/             # list-filter, form, master-detail, wizard, dialog, detail
│  │  ├─ tests/                  # Jest spec templates
│  │  └─ snippets/               # per-component usage snippets
│  └─ skills/                    # shipped skills (Phase 7–8)
│     ├─ ssjs-orchestrator/
│     ├─ ssjs-discovery/
│     ├─ ssjs-component-usage/
│     ├─ ssjs-screen-from-spec/
│     ├─ ssjs-screen-from-figma-json/    # TWO separate design-input skills (see 8.5a / 8.5b)
│     ├─ ssjs-screen-from-image/
│     ├─ ssjs-forms-validation/
│     ├─ ssjs-grid-filter/
│     ├─ ssjs-auth-api/          # SSO/OIDC, Apigee, interceptors
│     ├─ ssjs-guards-routing/    # canActivate and friends
│     ├─ ssjs-tdd-jest/
│     ├─ ssjs-run-and-fix/
│     └─ ssjs-component-authoring/   # (only if repo supports adding new coras components)
└─ eval/                         # Phase 11: scenarios, fixtures, results (not shipped)
```

Create the directories and empty `PROGRESS.md` (with the full checklist from this file) **before doing anything else**.

---

## PHASE 1 — Repository discovery

**Goal:** understand how `ssjs-frmk` is built, structured, tested, served and consumed.
**Output:** files in `discovery/`. No code generation yet.

### 1.1 Locate and map the repo
Tasks:
1. List the top-level structure (2 levels deep). Identify: workspace type (Angular CLI workspace, Nx, plain library, monorepo), `projects/` or `libs/` and `apps/`.
2. Identify the **library project(s)** that contain the `coras-*` components, the **public API entry** (`public-api.ts` / `index.ts`), and any **demo/showcase/sample app** (very valuable; treat it as the best source of real usage).
3. Write `discovery/repo-map.md` containing: a tree, a one-line purpose for each important folder, and the path to each of: public API, components root, services root, styles/tokens root, demo app, stories (Storybook) if any, docs if any.

### 1.2 Detect the environment
Read `package.json`, `angular.json`/`project.json`, `tsconfig*.json`, lock files, `.nvmrc`, `.npmrc` (never copy tokens; record only registry host names), and CI files. Record in `discovery/environment.md`:
- Angular version, TypeScript version, Node version required, package manager.
- **Module style:** standalone components vs `NgModule`s (or mixed). State how a consumer imports a component (which module/standalone import symbol).
- **Change detection / reactivity style:** signals, RxJS, `@Input()` decorators vs `input()` functions, new control flow (`@if/@for`) vs `*ngIf`.
- **Forms style:** reactive forms, template-driven, signal forms. Which coras components implement `ControlValueAccessor`.
- **Test runner:** Jest or Karma/Jasmine (look for `jest.config.*`, `jest-preset-angular`, `karma.conf.js`, `test` target in angular.json). Record the exact command to run **all tests** and **a single spec**.
- **Lint/format:** ESLint config, custom rules, Prettier, stylelint.
- **Build/serve commands:** exact commands to build and serve; default port; any proxy config (`proxy.conf.json`: record targets as variable names only).
- **Styling:** SCSS/CSS, how tokens are consumed (CSS variables, SCSS maps), theme entry file, typography classes.
- **Config/environment pattern:** how apps configure SSO/Apigee (environment files, runtime config JSON, injection tokens).
- **Mock capability:** any existing mock server, MSW, in-memory API, or "mock mode" for auth. If none, record "none" (a later phase will define a convention).

### 1.3 Detect conventions
In `discovery/conventions.md` record, with example file paths:
- File and folder naming for components, services, models, routes, feature modules.
- Naming of selectors, classes, spec files, test describe blocks.
- Folder layout of a typical feature in the demo app (e.g. `feature/pages`, `feature/components`, `feature/services`, `feature/models`).
- Lazy-loading and routing conventions, guard locations, how routes declare `canActivate`.
- Error handling and loading-state conventions; i18n approach; accessibility conventions.
- Import path aliases (`@ssjs/...`) and the consumer-side import statement for the framework.

### 1.4 Secrets scan (paths only)
Search for `.env*`, `environment*.ts`, `*secret*`, `*token*`, `*.pem`. Record paths only in `discovery/secret-locations.md`.

### Phase 1 checkpoint
- [ ] `repo-map.md`, `environment.md`, `conventions.md` exist and every claim cites a file path.
- [ ] You can state in one sentence each: how to run tests, how to serve the app, how a component is imported.
- [ ] `open-questions.md` lists every unknown.

---

## PHASE 2 — Component inventory (`catalog/components.json`)

**Goal:** a complete, accurate, machine-readable list of all `coras-*` components (expected 50+).

### 2.1 Build the extractor script (do not extract by hand)
Create `package/cli/extract/components.js` (Node; may use `typescript` or `ts-morph` as a **devDependency of the pack**, not a runtime dependency of consumers) that:
1. Finds every class decorated with `@Component` / `@Directive` / `@Pipe` in the component root(s) and exports in the public API.
2. For each, extracts: `selector`, class name, file path, `standalone` flag, `changeDetection`, and the module that declares/exports it (if NgModule style).
3. Extracts **inputs** (`@Input()` and `input()/input.required()`), **outputs** (`@Output()` and `output()`), `model()` signals, two-way bindings, with: name, alias, TypeScript type (as written), default value (as written), required flag, and the JSDoc description if present.
4. Detects `ControlValueAccessor` implementation (form-control capable) and `NG_VALUE_ACCESSOR` provider.
5. Detects **content projection slots** (`<ng-content select="...">`) by reading the template (inline or `templateUrl`).
6. Detects **injected dependencies** that matter to consumers (services, injection tokens, `DIALOG_DATA`, etc.).
7. Emits `catalog/components.json` conforming to the schema in Appendix B.
8. Is **idempotent** and prints a summary: number of components found, number with missing descriptions, number with unknown types.

If the extractor misses things (dynamic selectors, inheritance), extend it (handle `extends` by merging inherited inputs/outputs from the base class) rather than hand-patching.

### 2.2 Enrich with usage examples
For each component, find real usage:
- Search the demo app, stories, spec files, and docs for `<coras-xxx` usages.
- Capture 1–3 **minimal, verified** examples per component: template snippet + required imports + required component-class setup (e.g. form group). Store under `examples` in the catalog and as files in `templates/snippets/<component>.md`.
- An example is "verified" only if you copied it from real code; record its `source`. If no real usage exists, set `examples: []` and `status: "undocumented"`. Do **not** write an example from imagination.

### 2.3 Classify
For each component add `category`: `input`, `selection`, `form-container`, `layout`, `navigation`, `data-display`, `grid`, `feedback`, `overlay`, `filter`, `misc` (extend if needed, but document it). Add `aliases` (what developers or designers might call it: e.g. "select", "combo", "picklist" for dropdown, "textbox", "text field" for input). Aliases feed the mapping rules in Phase 5.

### 2.4 Validate
Create `package/cli/validate/catalog.js` that validates all catalogs against `schemas/*.json` (use `ajv` or a hand-rolled checker) and also checks: unique selectors, every selector starts with the detected prefix, every `source` path exists in the repo, no empty `inputs` name.

### Phase 2 checkpoint
- [ ] `components.json` count matches the number of exported coras components found by an independent `grep` count (record both numbers in `PROGRESS.md`).
- [ ] Manual verification of **5 randomly chosen components** against source: record the check in `PROGRESS.md`.
- [ ] Validator passes.

---

## PHASE 3 — Services, guards, interceptors (`catalog/services.json`, `catalog/guards-interceptors.json`)

**Goal:** capture everything cross-cutting so generated screens never reimplement it.

Tasks:
1. **SSO/OIDC service(s):** class, file, public methods (name, signature, purpose), how it is provided (`provideX()`, module `forRoot`, injection token), required configuration shape (keys and types only), login/logout/token-refresh flows, events/observables exposed, and how routes are protected today.
2. **Apigee:** service(s) and configuration shape, how a gateway key/token is attached, base-URL handling, and any API client wrapper.
3. **Interceptors:** each interceptor class/function, order, which requests it applies to, **how it decides SSO token vs Apigee token** (document the rule precisely, e.g. URL pattern, header, context token), how to opt a request in/out, error handling and retry behaviour.
4. **Guards:** all existing `canActivate`/`canMatch`/`canDeactivate` guards (functional or class-based): purpose, config, how applied in a route. If a guard does not exist for a need (e.g. role-based), note it; the skill will say how to *add* one following the same pattern.
5. **Other shared services:** notification/toast, dialog, loader, i18n, storage, error handler, logging, grid/filter state services.
6. Per entry include: `kind`, `class`, `file`, `providedIn`/`provideFunction`, `methods[]`, `config[]`, `usage_example` (copied from real code with source), `dont_do` (e.g. "do not call HttpClient with manual Authorization header").
7. For each service document a **testing recipe**: how to mock it in Jest (`TestBed.configureTestingModule` providers, spies). Prefer copying from existing spec files.
8. Define the project's **mock mode convention**: if the repo has one, document it. If not, propose (in `ASSUMPTIONS.md`) a mock approach for local running without SSO/Apigee (e.g. a `MockAuthProvider` + a mock interceptor or a tiny `json-server`/express mock script under `cli/mock-server`). Do not modify the framework repo; the pack ships the mock as a template.

### Phase 3 checkpoint
- [ ] Each service entry has `source`, methods, provider instructions, and a Jest mocking recipe.
- [ ] "Token selection rule" is documented in one unambiguous paragraph, with source citations.

---

## PHASE 4 — Design tokens and typography (`catalog/tokens.json`)

Tasks:
1. Find where tokens live (SCSS maps, CSS custom properties, TS constants).
2. Extract: colors (name → value → semantic role), typography scale (name, size, weight, line-height, class/mixin to apply), spacing, radius, elevation/shadow, breakpoints, z-index layers.
3. Record **how to consume** each (CSS variable `var(--...)`, SCSS mixin, utility class). Provide a "never hardcode" list: any hex colour, px font size, etc. found in components should map to a token.
4. Build a reverse lookup: `hex → token name` and `font-size/weight → typography class`, used later to convert design exports into tokens (Phase 6).

Checkpoint: `tokens.json` validates; at least one reverse lookup test case works (write `eval/token-lookup.test.js`).

---

## PHASE 5 — Archetypes, templates, and mapping rules

### 5.1 Archetypes (`catalog/archetypes.json`, `templates/archetypes/*`)
From the demo app and real feature code, define reusable screen archetypes. Minimum set: **list-with-filter-and-grid**, **create/edit form**, **master-detail**, **wizard/stepper**, **dialog/modal form**, **read-only detail**, **dashboard (cards)**. Only include archetypes you can ground in real code; mark others `status: "proposed"`.

For each archetype:
- `id`, `description`, `when_to_use`, `required_components`, `required_services`.
- A **template folder** with placeholder files, using `{{Name}}`, `{{name}}`, `{{kebab}}`, `{{route}}`, `{{apiBase}}` placeholders: component `.ts`, `.html`, `.scss`, `.spec.ts` (Jest), routing snippet, model/interface file, API service file, and mock data file.
- A `README.md` per template describing what to replace and what must not change.
- Every template **must compile and pass its own spec** when instantiated into a scratch Angular workspace/the demo app copy. (Test instantiation in Phase 11.)

### 5.2 Mapping rules (`catalog/mapping.json`)
Rules that convert a **design node description** (from Figma export/spec) into a `coras-*` component. Structure per rule:
```json
{
  "id": "map-dropdown",
  "match": { "design_names": ["Dropdown","Select","Combobox"], "shape_hints": ["text+chevron","list-below"], "figma_component_keys": [] },
  "component": "coras-dropdown",
  "prop_mapping": { "label": "label", "placeholder": "placeholder", "options": "options", "disabled": "disabled" },
  "variant_mapping": { "state=error": {"invalid": true}, "size=small": {"size": "sm"} },
  "children_rule": "options come from list items",
  "confidence": "high|medium|low",
  "source": "path or 'derived-from-aliases'"
}
```
Create at least one rule per component. Derive `design_names` from `aliases` (Phase 2.3). Rules with no real evidence of how design variants map must be `confidence: "low"` and flagged so the orchestrator asks for confirmation.

### Phase 5 checkpoint
- [ ] Every archetype template instantiates, compiles and its spec passes in a scratch copy (record commands and result).
- [ ] `mapping.json` covers 100% of components in `components.json` (script check).

---

## PHASE 6 — Screen Spec: the universal intermediate format

**Rationale:** the organization cannot provide an SSO token for Figma, so the agent never calls Figma. Designs arrive as **files**. The pipeline is:

```
(design export file | text requirement)  --adapter-->  screen-spec.json  --skills-->  Angular code + Jest tests
```

### 6.1 Define `schemas/screen-spec.schema.json`
A screen spec is JSON with: `meta` (name, route, archetype, source type, confidence), `layout` (tree of containers: `row`, `column`, `grid`, `section`, `card`, with gap/align/padding as **token names**), `nodes` (component nodes with `component`, `props`, `bind`, `events`, `children`, `a11y`), `data` (mock datasets and entity models), `behaviors` (validation rules, navigation, API calls, guards), `states` (loading, empty, error variants), `confidence` per node, and `unmapped` (nodes the adapter could not map). Include a full example in `eval/fixtures/specs/` for each archetype.

### 6.2 Input adapters (`package/cli/adapters/`)
Implement in this priority order; document honestly what each can and cannot do.

| Adapter | Input | Fidelity | Notes |
|---|---|---|---|
| `figma-json` | Figma REST-format JSON exported via a designer-run plugin or "save as JSON" | **High** (component names, variants, auto-layout, variables survive) | Preferred. Detect and report detached instances and non-library frames. |
| `svg` | SVG export | Medium-low | Text, positions, colours only; no component identity. Use heuristics + mapping `shape_hints`; mark confidence low. |
| `pdf` | PDF export | Low-medium | Extract text blocks with positions (`pdftotext -bbox` or `pdf-parse` if available offline). If vector, geometry may also be available. |
| `image` | PNG/JPG, manually created mock-ups | Low-medium | Tiered best-effort pipeline (vision model → OCR+heuristics → guided draft) plus a compare-and-improve loop: see 6.3 and 6.3a. **Must always produce a draft.** |
| `text` | Plain-language requirement | n/a | Produces a spec via the archetype + clarifying defaults. |

Each adapter command: `ssjs-ai spec --from <type> <file> -o specs/<name>.json`. Output **must validate** against the schema. `figma-json` details:
1. Walk the node tree; ignore hidden nodes; resolve component instances to their main component **name and variant properties**.
2. Convert auto-layout (direction, spacing, padding, alignment) to layout descriptors using the nearest **spacing token**.
3. Convert fills/typography via the reverse lookup in `tokens.json` (Phase 4). Unknown values → keep literal in `unmapped_styles` (never silently hardcode).
4. Apply `mapping.json` rules; unmatched nodes go to `unmapped`.
5. Extract text content as labels/placeholders; repeated list-like structures → candidate data rows (feeds mock data).
6. Emit a **human-readable summary** (`specs/<name>.summary.md`) listing mapped components with confidence, and the unmapped list.

### 6.3 Image input: ALWAYS attempt a best-effort result, then improve it
The user will supply either (a) a Figma JSON export or (b) a manually created image (screenshot, mock-up, hand-made PNG/JPG). **Both must work.** Image results may be lower quality, but the agent must still produce a usable first draft and improve it, never refuse and never stop at a worksheet alone.

The `image` adapter (`ssjs-ai spec --from image <file>`) runs a **tiered pipeline**; use the best tier available and record which tier was used in `meta.extraction_tier`:

| Tier | Requires | What it does |
|---|---|---|
| **T1 Vision model** | env `SSJS_VISION_MODEL` (+ endpoint env var; never hardcode) is set and reachable | Sends the image with a strict prompt template (`templates/prompts/image-to-spec.md`) that lists **only** the catalog's components/aliases and the spec schema, and asks for JSON only. Validates against the schema; on invalid JSON retries up to 3 times with the validator error. |
| **T2 OCR + layout heuristics** | Offline tools available in the environment (e.g. `tesseract`, Python `Pillow`/`opencv`); the adapter must detect availability and degrade gracefully | OCR extracts text with bounding boxes. Heuristics segment regions (header, sidebar, toolbar, form rows, table/grid, buttons) from rows/columns of text and edges, then apply `mapping.json` `shape_hints` (e.g. text + chevron → dropdown, a repeated row grid with header → `coras-grid`, a rounded rectangle with a label → button). |
| **T3 Guided draft** | Nothing (always available) | Builds a **skeleton spec** from the chosen archetype (default: infer from text content such as "Search", "Save", "Cancel", table headers) with all nodes `confidence: "low"`, AND writes a **review sheet** (`specs/<name>.review.md`) listing every guessed component with a one-line question to confirm or correct. |

Rules for all tiers:
1. **Always** emit a valid `screen-spec.json`, plus `specs/<name>.summary.md` (mapped components, confidence, unmapped regions) and `specs/<name>.annotated.png` if an imaging tool exists (draw boxes with labels over the source image so a human can see how the image was interpreted).
2. Every node carries `confidence` and `evidence` (e.g. `"ocr text 'Department' + chevron icon"`), so wrong guesses can be diagnosed.
3. Visible text (labels, button captions, table headers, placeholders) is extracted literally; do not "fix" or translate it.
4. Colours and font sizes are resolved to **tokens** using the reverse lookup (nearest token, with a recorded distance); never emit raw hex into generated code.
5. Never fabricate content that is not visible (e.g. extra columns); if something looks cut off or illegible, add it to `unmapped` with a note.

### 6.3a The image improvement loop (how the agent gets better on images)
Image fidelity is improved by **comparing the built screen back to the image**, not by trusting the first extraction.
1. After the screen compiles and is served (Phase 8B), take a screenshot of the new route (headless browser if available; else ask the user to attach a screenshot and state that the loop is manual).
2. Run `ssjs-ai compare --design <image> --actual <screenshot> -o .ssjs-ai/compare/`, which produces: a side-by-side image, a diff heatmap, and a JSON of region-level differences (missing element, misplaced element, size difference, text mismatch, colour/token mismatch) with a **similarity score** (e.g. SSIM or pixel-diff after resizing to the same width; state the metric used).
3. The agent fixes the **largest differences first** (text mismatch and missing components before spacing), re-runs, and re-compares. **Max 4 improvement rounds**; stop earlier if the score stops improving by ≥ 2% or reaches the target (default 0.85, configurable). Report the score per round.
4. Structural differences (wrong component chosen) are corrected in the **spec** first (so the spec stays the source of truth), then code is regenerated/edited; do not hand-patch markup that contradicts the spec.
5. **Learn from corrections:** when the user corrects a mapping ("that is a coras-multiselect, not a dropdown") append a record to `.ssjs-ai/corrections.jsonl` (`evidence`, `wrong`, `right`, `date`). `ssjs-ai corrections:export` produces a patch proposal for `catalog/mapping.json` (new `shape_hints`/`design_names`) for maintainers to review and release. The skill must tell the agent to check `corrections.jsonl` before mapping.
6. Keep a small **image fixture set** under `eval/fixtures/images/` (at least 5 images of different archetypes, with hand-written expected specs) and an `ssjs-ai eval:image` command that reports extraction accuracy (component match rate, text match rate). Use it to measure whether changes to heuristics/prompts actually improve results.

### 6.4 Confidence policy (used by the orchestrator)
- **Figma JSON:** `high` → proceed automatically; `medium` → proceed, list assumptions in the final report; `low` or any `unmapped` → ask the user to confirm the mapping table before generating code.
- **Image:** because image input is inherently lower confidence, do **not** block on everything being confirmed. Instead: (1) build the first draft immediately using the best guess, (2) show the user the mapping table with confidence and evidence, and (3) run the improvement loop (6.3a). Ask the user **before building** only if the overall confidence is below 0.4, or the archetype cannot be inferred at all, or more than 30% of regions are unmapped; in that case ask at most **one** consolidated question listing the uncertain items with suggested options.
- In every final report, state the input type, extraction tier, similarity score (images), and the list of low-confidence nodes.

### Phase 6 checkpoint
- [ ] Schema + 7 example specs (one per archetype) validate.
- [ ] `figma-json` adapter tested against at least 2 hand-built fixture exports (create small fixtures; do not require real Figma access). Tests live in `package/cli/adapters/__tests__/`.
- [ ] The image adapter always emits a valid spec (every tier tested, including the no-vision, no-OCR T3 fallback) with per-node `confidence` and `evidence`; the `compare` command works on a sample pair.
- [ ] At least 5 image fixtures with expected specs exist and `eval:image` reports a baseline score in `eval/RESULTS.md`.

---

## PHASE 7 — Skill authoring standard (applies to EVERY skill)

### 7.1 Directory and naming rules
- Skill directory name: lowercase letters, digits, single hyphens; **must equal** the `name` in frontmatter; prefix `ssjs-`. Do not start/end with `-`, no `--`.
- File name is exactly `SKILL.md` (uppercase). Optional folders: `references/`, `scripts/`, `templates/`, `examples/`.
- Frontmatter must contain at minimum `name` and `description`. Optional per Agent Skills convention: `license`, `compatibility`, `metadata` (string key/value pairs). **Verify against the OpenCode and Claude Code versions in use; put every additional section in the body, not in unrecognised frontmatter keys.**
- `description` (target 150–400 chars): *what it does* + *when to use it* + trigger phrases ("use when the user asks to …"). This is what the model sees when choosing skills; make it specific.
- Keep `SKILL.md` under ~250 lines. Move catalogs/long examples into `references/` and tell the agent exactly **when** to read each file.

### 7.2 Mandatory SKILL.md structure
Every skill uses **exactly** these sections, in this order:

```markdown
---
name: ssjs-<topic>
description: <what + when + triggers>
license: <org license or UNLICENSED>
compatibility: opencode, claude-code
metadata:
  version: "1.0.0"
  framework: "ssjs-frmk"
  framework_version: "<detected>"
  angular_version: "<detected>"
  owner: "<team>"
  category: "<orchestration|build|test|auth|run>"
---

# <Human title>

## Purpose
One paragraph: the outcome this skill guarantees.

## When to use / When NOT to use
Bulleted triggers and explicit non-triggers (with the skill to use instead).

## Inputs
Table: name | type | required | source (user text / file / spec) | validation.

## Outputs
Files created/changed, commands run, and the final report format.

## Preconditions
What must be true before starting (repo type, installed deps, discovery run, etc.) and how to check each.

## What this skill does
Short numbered list of responsibilities (the scope).

## Procedure
Numbered, imperative, deterministic steps. Each step: action → exact command/tool → expected result → what to do on failure.
Reference scripts as `npx ssjs-ai <command>` rather than describing logic in prose.

## What must NOT be done
Hard prohibitions (e.g. never use raw <input>, never hardcode colors, never call HttpClient with manual Authorization header, never edit framework sources, never skip tests, never print secrets).

## Validation (how to verify the output)
Checklist with exact commands and pass criteria (tests, lint, build, serve health check, catalog checks).

## Boundary conditions & edge cases
Unknown component, version mismatch, missing demo app, no Jest config, port in use, auth unavailable, low-confidence design input, etc., each with the required behaviour.

## Failure handling & escalation
Retry limits, what to log, when to stop and ask the user.

## Examples
2 short, realistic input → action → output examples (copied or adapted from catalog; mark `source`).

## References
Files in this skill's `references/` and when to read them.
```

### 7.3 Writing rules for small models
1. Use imperative verbs; one action per step; no ambiguous words ("appropriately", "as needed").
2. Every rule that matters appears as a **checkable** item in Validation.
3. Prefer commands (`npx ssjs-ai verify`) over prose algorithms.
4. Give **exact file paths** and **exact import symbols** from the catalog, never "the dropdown module".
5. Include at least one **negative example** ("Wrong → Right") where mistakes are likely.
6. Never copy long code into SKILL.md; reference `templates/` and `catalog/`.

---

## PHASE 8 — The skills to write

Write each skill using the Phase 7 template. Content requirements per skill:

### 8.1 `ssjs-orchestrator` (entry point; see Phase 8A for the full state machine)
Routes a free-text request or attached design file to the right sub-skills and drives the build → test → run → fix loop.

### 8.2 `ssjs-discovery`
Runs `ssjs-ai doctor` and `ssjs-ai discover` in the **consumer** repo (not the framework repo): detects Angular version, module style, test runner, serve command, ssjs-frmk version, presence of the interceptor/SSO setup, and writes `.ssjs-ai/project-profile.json`. Compares framework version vs the pack's `framework_version` and warns on mismatch. Every other skill reads this profile instead of re-detecting.

### 8.3 `ssjs-component-usage`
For requests like "add a coras-dropdown with options in the current screen". Procedure: identify the target screen (current file or path), look up the component in `catalog/components.json` via aliases, confirm required inputs, add the import (module or standalone as per profile), insert template markup from verified snippets, add component-class state/FormControl, write/extend the Jest spec **first** (red), implement (green), run tests. Must handle: component already used, name conflict, form vs non-form usage, missing form group, options source (static vs API), a11y label requirement.

### 8.4 `ssjs-screen-from-spec`
Builds a full screen from a validated `screen-spec.json` and/or text requirement with **mock values**. Procedure: select archetype → instantiate template via `ssjs-ai scaffold --spec` → generate mock data file from spec `data` → replace placeholders → register route → write specs first (TDD) → implement → verify. Must keep generated mock API behind a service interface so it can later be swapped for the real API.

### 8.5a `ssjs-screen-from-figma-json`
Skill for **Figma JSON export** input (high-fidelity path). Inputs: path to the JSON (and optional frame/page name if the file has several). Procedure: validate it is Figma-style JSON (else stop and tell the user which skill to use) → select the target frame(s) (ask only if more than one top-level frame and none named) → `ssjs-ai spec --from figma-json` → read `summary.md` (detached instances, unmapped nodes, unmapped styles) → apply the Phase 6.4 Figma policy → hand off to `ssjs-screen-from-spec` → in the report, list design nodes → `coras-*` mapping. Boundary conditions: very large JSON (process by frame via script; never load the whole file into the model context), missing component names, multiple variants, hidden layers, components not in the catalog, prototype interactions/links (map to routes/navigation only if the spec supports it; else list as follow-ups).

### 8.5b `ssjs-screen-from-image`
Skill for **manually created images** (low-fidelity path). Inputs: image path(s) (PNG/JPG/SVG/PDF page), optional hints from the user (screen name, archetype, "this is a list screen", which table columns exist). Procedure: check the file is readable and note resolution (very small or blurry images: tell the user the expected quality, then continue anyway) → read `.ssjs-ai/corrections.jsonl` → run `ssjs-ai spec --from image` (tiered pipeline, Phase 6.3) → review `summary.md`/annotated image → apply the image confidence policy (6.4) → hand off to `ssjs-screen-from-spec` to build a first draft with **mock values** → run the **improvement loop** (6.3a) → final report with similarity score per round, remaining low-confidence nodes and the questions the user can answer to improve it. Must **not** stop at a worksheet or refuse because the model lacks vision: it must use the fallback tiers. Must not invent content not visible in the image, and must say clearly which parts are guesses. Include the user-correction workflow ("tell me what is wrong, and I will update the spec and record the correction").

Both design-input skills **only produce/validate the spec and orchestrate hand-off**; they must not contain screen-generation logic of their own (that lives in `ssjs-screen-from-spec`), so both inputs converge on one tested build path.

### 8.6 `ssjs-forms-validation`
Reactive-form patterns with coras form components: building `FormGroup`, validators, error message display via the framework's pattern, disabled/readonly states, dependent fields, submit handling, dirty/unsaved-changes guard. Include the **per-component form-binding table** from the catalog (which are CVA-capable).

### 8.7 `ssjs-grid-filter`
Grid + filter system: columns definition, server vs client paging/sort, filter component wiring, state persistence (if the framework provides), empty/loading/error states, row actions, selection. Use only APIs present in `components.json`.

### 8.8 `ssjs-auth-api`
How to call backends: always through the framework's API/HTTP layer so the interceptor applies the correct token (SSO vs Apigee per the documented rule). How to add a new API service, how to opt out/in, how to mock auth in Jest and in local run. **Prohibit** manual token handling.

### 8.9 `ssjs-guards-routing`
For "append the canActivate service": add or reuse a guard following the repo's pattern (functional vs class), register in route config, handle redirect/unauthorized, write guard unit tests (authorized, unauthorized, loading/unknown), integrate with the SSO service from the catalog. Must check whether an existing guard already covers the need before creating one.

### 8.10 `ssjs-tdd-jest`
The TDD protocol the orchestrator enforces: Red → Green → Refactor. Test-file placement and naming from conventions; `TestBed` setup for coras components (imports, providers, mocks from the services catalog); what to assert (rendered selector, input bindings, emitted events, form validity, service calls); how to run a single spec; coverage threshold if the repo defines one. If the repo uses Karma instead of Jest: **do not silently switch**; follow the detected runner and note it (or, if Jest is requested, provide the migration steps as a separate opt-in task, not automatic).

### 8.11 `ssjs-run-and-fix`
The server verification loop (details in Phase 8B).

### 8.12 `ssjs-component-authoring` (optional, only if repo structure supports it)
How to add a **new** `coras-*` component to the framework itself per repo conventions. Write it only if discovery shows a clear pattern; otherwise write a stub skill that says "not supported; open an issue with the framework team" and list it under open questions.

Each skill also needs a `references/` folder with the **relevant slice** of the catalogs (do not tell the agent to load the whole 50-component catalog; use `npx ssjs-ai lookup component <name>` to fetch one entry).

---

## PHASE 8A — Orchestrator design (`ssjs-orchestrator`)

### 8A.1 Intent classification
Classify the user's request into one or more **intents** using this table (keyword hints are examples; the agent should also use meaning):

| Intent | Example requests | Skill chain |
|---|---|---|
| `ADD_COMPONENT` | "build a coras-dropdown with options in current screen" | discovery → component-usage → tdd-jest → run-and-fix |
| `BUILD_SCREEN_FROM_FIGMA_JSON` | "build the attached screen with mock values" + a `.json` Figma export | discovery → screen-from-figma-json → screen-from-spec → tdd-jest → run-and-fix |
| `BUILD_SCREEN_FROM_IMAGE` | "build this screen from the attached image/mock-up" + png/jpg/svg/pdf | discovery → screen-from-image → screen-from-spec → tdd-jest → run-and-fix → **image improvement loop** |
| `BUILD_SCREEN_FROM_TEXT` | "create an employee list screen with filters" | discovery → screen-from-spec → tdd-jest → run-and-fix |
| `ADD_GUARD` | "append the canActivate service to this route" | discovery → guards-routing → tdd-jest → run-and-fix |
| `WIRE_API` | "call the orders API on submit" | discovery → auth-api → tdd-jest → run-and-fix |
| `ADD_FORM_VALIDATION` / `ADD_GRID_FILTER` | … | discovery → forms-validation / grid-filter → tdd-jest → run-and-fix |
| `UNKNOWN` | ambiguous | ask **one** clarifying question with options |

Compound requests are split into ordered sub-tasks; each sub-task runs the full loop below.

### 8A.2 State machine (the orchestrator MUST follow these states in order)
```
S0 INTAKE        -> parse request; find attachments; classify intent(s)
S1 PROFILE       -> run `ssjs-ai doctor`; read/create .ssjs-ai/project-profile.json
S2 CLARIFY       -> only if blocking ambiguity or low-confidence design (Phase 6.4); else skip
S3 PLAN          -> write .ssjs-ai/plan.md: files to create/change, components used (from catalog), tests to write, risks
S4 RED           -> write failing Jest specs first; run them; confirm they FAIL for the right reason
S5 GREEN         -> implement minimum code to pass; run specs until green
S6 REFACTOR      -> remove duplication, apply tokens/conventions; run lint + specs
S7 INTEGRATE     -> register route/module/import; ensure the screen is reachable
S8 RUN           -> build + serve + health check (see 8B); capture logs
S9 FIX LOOP      -> on any failure in S4–S8: diagnose from logs, minimal fix, re-run from the failing state (max iterations below)
S10 REPORT       -> final report (format below)
```
**Iteration limits:** max 5 fix iterations per failing state, max 15 total per request. On exceeding a limit: stop, summarise the root-cause hypothesis, the last error, and what was tried, and ask the user. Never loop silently.

**Non-negotiables:** no code before a failing test exists (S4 before S5) unless the change is pure config/routing, in which case state that in the plan. Never delete or weaken a test to make it pass. Never edit the framework repo or `node_modules`.

### 8A.3 Plan file (`.ssjs-ai/plan.md`) must contain
Request (verbatim), intent(s), target files, `coras-*` components to be used (each with catalog entry reference), services/guards, tests to write (names), mock data approach, assumptions, and risks.

### 8A.4 Final report format (S10)
```
## Result: <SUCCESS | PARTIAL | BLOCKED>
- What was built (files, route)
- Components used (coras-*) and where
- Tests: <n written> / <n passing>, command used
- Server: started on <url>, health check <pass|fail>, evidence (HTTP status / log line)
- Assumptions made & items needing human confirmation
- Not done / follow-ups
```

---

## PHASE 8B — Run-and-fix loop (`ssjs-run-and-fix`)

Deterministic script `ssjs-ai run-check` (implement in `package/cli/run/`) does the mechanical parts; the skill tells the agent how to interpret and fix.

### 8B.1 Steps
1. **Preflight:** read the profile; check Node version, dependencies installed (`node_modules` present; else `npm ci`/`install` per profile **only if the registry is configured**; otherwise stop and report), free port (default from profile; if busy, pick next free and report).
2. **Static checks:** type-check/build (`ng build` or `tsc --noEmit -p`), lint, then the Jest run (full or affected specs).
3. **Serve:** start the dev server **in the background**, redirecting logs to `.ssjs-ai/logs/serve.log`, saving PID.
4. **Wait for ready:** poll for a "compiled successfully"/"Local: http://…" log line **and** an HTTP GET on `/` returning 200 (timeout default 180 s; configurable).
5. **Route check:** HTTP GET the new route (SPA returns index; so additionally confirm there is **no** compile error in the log and, if a headless browser is available offline, load the route and assert no console errors and that the expected `coras-*` selectors are present). If no headless browser: state this limitation in the report.
6. **Report:** write `.ssjs-ai/logs/run-summary.json` (status, url, errors[], warnings[]).
7. **Cleanup:** stop the server (kill by PID) unless the user asked to keep it running.

### 8B.2 Error classification and standard fixes
The skill must contain a table (error pattern → likely cause → fix procedure), seeded from real framework experience. Minimum rows:
- `NG8001 'coras-xxx' is not a known element` → missing import/module; fix from catalog `import` info.
- `NG8002 Can't bind to 'x' since it isn't a known property of 'coras-xxx'` → wrong input name; re-check catalog.
- `NG0201 No provider for X` → missing provider; use `services.json` provider recipe (SSO/Apigee/interceptor setup).
- `NullInjectorError` in Jest → add mock provider from services testing recipe.
- Template type errors (strict templates) → fix types; never cast to `any` unless the catalog documents it.
- Port in use → choose the next port.
- `Cannot find module '@ssjs/…'` → path alias/tsconfig or missing dependency; check profile.
- Auth redirect loop locally → switch to mock auth mode; do not disable the guard in the framework.
- CORS/proxy failures → use or create a **local proxy config template** (host names as variables only).

### 8B.3 Rules
- Fix the **first** error first; re-run; do not batch speculative fixes.
- Do not suppress errors (`// @ts-ignore`, `skipLibCheck` changes, disabling lint rules) without recording an assumption and telling the user.
- Do not modify global config files (`angular.json`, `tsconfig`, `jest.config`) unless the plan lists it and the fix cannot be done elsewhere.

---

## PHASE 9 — CLI, scripts, and linters

Implement `package/bin/ssjs-ai.js` (Node ≥ the version in the profile; **no heavy runtime dependencies**; use only what is available offline; list every dependency and why in `package/README.md`).

Commands:
| Command | Purpose |
|---|---|
| `ssjs-ai init [--target claude\|opencode\|agents\|all] [--force]` | Copies skills to `.claude/skills/` (default; read by both Claude Code and OpenCode), or `.opencode/skills/`, or `.agents/skills/`. Never overwrites modified skills without `--force`; writes `.ssjs-ai/installed.json` with version and checksums. |
| `ssjs-ai doctor` | Checks Node, Angular, ssjs-frmk version vs pack, test runner, serve command, writes `.ssjs-ai/project-profile.json`. |
| `ssjs-ai lookup component <name\|alias>` | Prints one catalog entry (inputs, outputs, import, example). Fuzzy-match aliases; if multiple, list candidates. |
| `ssjs-ai lookup service <name>` / `token <value>` | Same for services/tokens. |
| `ssjs-ai spec --from <figma-json\|svg\|pdf\|image\|worksheet\|text> <input> -o <out>` | Phase 6 adapters. |
| `ssjs-ai spec:validate <file>` | Validate a spec. |
| `ssjs-ai compare --design <img> --actual <img> -o <dir>` | Image improvement loop: side-by-side, diff heatmap, region-level differences JSON, similarity score. |
| `ssjs-ai eval:image` | Runs the image fixture set and reports extraction accuracy. |
| `ssjs-ai corrections:export` | Turns `.ssjs-ai/corrections.jsonl` into a reviewable patch for `mapping.json`. |
| `ssjs-ai scaffold --archetype <id> --spec <file> [--dry-run]` | Instantiate templates; `--dry-run` prints file list. |
| `ssjs-ai verify` | Static checks + Jest (+ lint) with machine-readable summary. |
| `ssjs-ai run-check [--keep]` | Phase 8B. |
| `ssjs-ai lint:skills` | Skill linter (below). |
| `ssjs-ai catalog:validate` | Phase 2.4 validator. |
| `ssjs-ai update-check` | Compares installed pack/skills version vs package version; reports drift. |

### Skill linter rules (`lint:skills`) — fail the build on any violation
1. Directory name equals frontmatter `name`; name matches `^[a-z0-9]+(-[a-z0-9]+)*$`.
2. `description` present, 50–1024 chars, includes "use when" (or equivalent) trigger wording.
3. All mandatory sections from 7.2 present, in order, non-empty.
4. "What must NOT be done" has ≥ 3 items; "Validation" has ≥ 3 checkable items; "Boundary conditions" has ≥ 4 items.
5. Every file path referenced in the body exists in the package; every `npx ssjs-ai <cmd>` referenced is a real command.
6. Every component/service name mentioned exists in the catalogs.
7. `SKILL.md` ≤ 250 lines; no secrets patterns (token-like strings, URLs containing credentials).
8. No absolute local paths (`/home/`, `C:\`).

---

## PHASE 10 — npm packaging

1. `package.json`: name `@<org>/ssjs-frmk-ai` (confirm the org scope in `open-questions.md`; use a placeholder if unknown), `version` `1.0.0`, `bin: { "ssjs-ai": "bin/ssjs-ai.js" }`, `files` whitelist (`bin`, `cli`, `catalog`, `schemas`, `skills`, `templates`, `README.md`, `CHANGELOG.md`), `engines.node`, `license`, `publishConfig.registry` set to a **placeholder** for the internal registry, **no `postinstall` script that writes into the user's project** (installation of skills is explicit via `ssjs-ai init`; document why).
2. Optional OpenCode plugin entry (only if the OpenCode plugin API is confirmed in the installed version): expose custom tools (`ssjs_lookup_component`, `ssjs_verify`, `ssjs_run_check`) that call the CLI. Keep it in a separate file/entry so skills work without it.
3. Version coupling: put `frameworkVersion` and `angularVersion` in `catalog/meta.json`; `doctor` warns on mismatch.
4. `README.md`: install, `init`, usage examples for each intent, how to update, how to report bad output, limitations (esp. image/PDF).
5. `CHANGELOG.md` and a release procedure (bump version → regenerate catalogs → lint → pack → publish).
6. CI recipe (as a file in `package/ci/`): regenerate catalogs from the framework repo on every framework release, run validators and eval scenarios, fail on drift, publish.
7. Run `npm pack --dry-run`; record the file list in `PROGRESS.md`. Confirm the tarball excludes `discovery/` and `eval/`.

---

## PHASE 11 — Evaluation (acceptance scenarios; write fixtures and dry-run results in `eval/`)

For each scenario create `eval/scenarios/<id>.md` with: request text, fixture project state, expected plan, expected files, expected tests, expected run result. Use a **copy of the demo app** (or a minimal consumer app created from a local template) as the fixture; never the framework repo itself.

1. **S01** "build a coras-dropdown with options in current screen" (static options, reactive form).
2. **S02** Same but options from API through the interceptor layer (verifies no manual tokens).
3. **S03** "build the attached screen with mock values" using a `figma-json` fixture → list+filter+grid screen.
4. **S04** Attached manually created PNG, **vision model available (T1)** → draft built, mapping table shown, improvement loop runs, similarity score reported per round.
5. **S05** Attached manually created PNG, **no vision model (T2/T3 fallback)** → agent must still produce a draft screen with mock values, mark low-confidence nodes, show the review sheet, and improve via the compare loop; it must NOT stop at a worksheet or refuse.
5b. **S05b** Very low-quality/blurry image or illegible text → agent builds what is legible, lists unreadable regions as `unmapped`, asks at most one consolidated question; no invented content.
5c. **S05c** User correction after an image build ("that is a coras-multiselect") → spec updated, code regenerated, correction written to `corrections.jsonl`, and the next run on the same image uses it.
6. **S06** "append the canActivate service to this route" with an existing guard available (reuse expected).
7. **S07** Same where no guard fits (create a new guard following the pattern; tests for 3 cases).
8. **S08** Create/edit form with validation and unsaved-changes guard.
9. **S09** Server fails to start due to a missing import → fix loop resolves in ≤ 3 iterations.
10. **S10** Jest failure due to missing provider (`NullInjectorError`) → mock from services recipe.
11. **S11** Unknown component requested ("coras-carousel" that doesn't exist) → agent must say it doesn't exist, suggest closest aliases, not invent.
12. **S12** Version mismatch (framework version in project ≠ pack) → warns and proceeds conservatively or stops per policy.

For each scenario, run the **procedure by hand/script** (dry-run) and record: pass/fail, what the skill text failed to prevent, and fix the skill. Iterate until all 12 are consistent. Add a final table to `eval/RESULTS.md`.

---

## PHASE 12 — Handoff documents

Create `package/docs/` (shipped) and `discovery/` (internal):
1. `docs/GETTING-STARTED.md` — 10-minute setup for developers with OpenCode (Qwen) and with Claude Code; example prompts for each intent.
2. `docs/FOR-DESIGNERS.md` — (a) how to export design JSON (what to include, naming rules: use the ssjs library components, avoid detached instances, use variables for colours/typography/spacing, name frames as screens) and how the `spec` output summary reports problems; (b) **tips for better image inputs** (export at 2x, one screen per image, no overlapping annotations, readable text, label states, keep standard component shapes, add a short text note listing table columns and actions).
3. `docs/MAINTAINERS.md` — how catalogs are regenerated, how to add a mapping rule, how to add an archetype, how to add/modify a skill, how to run eval, versioning/release.
4. `docs/LIMITATIONS.md` — honest list (image/PDF fidelity, vision dependency, headless-browser availability, unsupported components, runner assumptions).

---

## Appendix A — Skill quality checklist (run on every skill before ticking it off)
- [ ] Name = directory = lint-valid; description has "use when".
- [ ] All 11 mandatory sections present and specific to **ssjs-frmk** (no generic Angular filler).
- [ ] Every command exists; every path exists; every component/service exists in catalogs.
- [ ] At least one **Wrong → Right** example and one verified real example with `source`.
- [ ] Validation contains exact commands and pass criteria.
- [ ] Boundary conditions include: missing catalog entry, version mismatch, no test runner/Jest absent, low-confidence design, auth unavailable, port busy.
- [ ] Under 250 lines; heavy content moved to `references/`.
- [ ] Dry-run against at least one Phase 11 scenario.

## Appendix B — Catalog schemas (minimum fields; formalize as JSON Schema in `schemas/`)

`components.json` entry:
```json
{
  "id": "coras-dropdown",
  "selector": "coras-dropdown",
  "className": "CorasDropdownComponent",
  "category": "selection",
  "aliases": ["select", "combobox", "picklist"],
  "source": { "file": "projects/lib/src/dropdown/dropdown.component.ts", "lines": "12-140" },
  "import": { "style": "standalone|module", "symbol": "CorasDropdownComponent", "from": "@ssjs/frmk" },
  "formControl": { "cva": true, "notes": "use formControlName or [(ngModel)]" },
  "inputs": [{ "name": "options", "alias": null, "type": "DropdownOption[]", "default": "[]", "required": true, "description": "…", "source": "…" }],
  "outputs": [{ "name": "selectionChange", "type": "EventEmitter<DropdownOption>", "description": "…" }],
  "slots": [{ "select": "[prefix]", "description": "…" }],
  "dependencies": ["CorasThemeService"],
  "examples": [{ "title": "Basic", "template": "…", "classSetup": "…", "source": "…" }],
  "a11y": "label required; …",
  "dont": ["do not wrap in native <select>"],
  "status": "documented|undocumented|deprecated"
}
```

`services.json` entry: `id`, `kind` (`sso|apigee|interceptor|guard|util`), `class`, `source`, `provide` (`how`, `symbol`, `config[]`), `methods[]` (name, signature, description), `usage` (with source), `testingRecipe`, `dont`.

`tokens.json`: `colors[]` (name, value, role, cssVar), `typography[]` (name, size, weight, lineHeight, how), `spacing[]`, `radius[]`, `shadow[]`, `breakpoints[]`, `reverse` (maps value → token).

`mapping.json`: as defined in 5.2.

## Appendix C — Final-answer checklist for YOU (the building agent)
Before saying you are done:
1. Re-open `PROGRESS.md`; every box ticked or explained under "Blocked items".
2. Run `ssjs-ai catalog:validate`, `ssjs-ai lint:skills`, `npm pack --dry-run`; paste the three summaries in `PROGRESS.md`.
3. List all assumptions and open questions at the top of your final message.
4. State what you could **not** verify (e.g. headless browser unavailable, no real Figma export available, vision model absent).
5. Do not claim anything works unless you ran it and recorded the output.
