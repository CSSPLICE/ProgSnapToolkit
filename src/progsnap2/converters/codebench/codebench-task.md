The Codebnech dataset is located in sample_data/codebench, with the following structure:
* Codebench.pdf: A paper describing the dataset and how it was collected.
* ProgSnap2 Protocol - V1: The ProgSnap2 space (draft for v1.0, not fully released)
* f24: a ProgSnap2-formated codebench dataset
* raw/: a folder with raw datasets, one folder per semester, already extracted (e.g. 2024-1)
* raw/codebench.md: a description of the raw data format

Your job is to create a script that will convert a CodeBench dataset from its original format to the ProgSnap2 format and to write a series of tests that ensure that the conversion is complete.

Notes:
* The ProgSnap2 format is described in the src/progsnap2/spec/versions/progsnap2-v1.0.yaml file, and in the spec pdf above.
* The already f24 dataset has not been released in the raw format, so there is no direct comparison.
* Generally, the format of the f24 dataset should be considered that target with a few exceptions:
  * The output datasets should use SQLite rather than CSV for performance.
  * The output datasets should use a tabular CodeState representation rather than a .git-based representation.
* Output the PS2 formatted datasets in the main codebench data folder, next to f24
* This repository contains tools for reading and writing ProgSnap2 in various formats, so it should be used to write the output. It may have issues and bugs that should be identified along the way. The fixes will need to live in the main branch and should be submitted as PRs.

---

# Findings from exploration (2026-11-13)

## Resources

* **Codebench.pdf** is Pereira et al. (2020), BJET 51(4), "Using learning analytics in the Amazonas".
  * It is a clustering study, not a dataset paper.
  * It says **nothing** about the raw file layout, the execution log format, or the `<assessment>_<exercise>` naming. All parsing rules must come from the sample files and `raw/codebench.md`.
  * Useful context: the course is CS1 in Python for non-CS majors, with 7 modules. Each module has a homework list and a partial exam. Presentation errors count as wrong. The data is described as "completely anonymised".
* **ProgSnap2 Protocol - V1.pdf** is the 41-page draft spec. Relevant points beyond the YAML:
  * **Packaging:** one SQLite `.db` holding `DatasetMetadata`, `MainTable`, `CodeStates`, and `Link*` tables, plus `README.md` and an optional `Resources/`.
  * **Table CodeStates:** `CodeStateID` plus `Code` (full text), with optional multiple rows per ID keyed by `CodeStateSection`.
  * **Internal contradictions:**
    * Whether CodeStateSection may be used in Table format.
    * The `X-` prefix: the changelog says it is "no longer encouraged".
    * Timestamp timezones: the changelog says to include an offset (Manaus is UTC-04:00).
  * **SourceLocation** is `Text:line[:col]`, **1-based**; CodeMirror positions are 0-based.
  * **URL columns** (ProgramInput, ProgramOutput, ProgramErrorOutput) should hold `file:Resources/...` paths.
  * **Keystrokes:** the PDF has **no** InsertText/DeleteText columns and no Keystroke representation. The YAML spec does have them (`InsertText`, `DeleteText`, `DeleteLength`, `CodeStateRepresentation: Keystroke`).
* **Existing code in the repo:**
  * `converters/codebench.ipynb` analyzes f24; it is *not* a converter.
  * `converters/falconcode.ipynb` is the most recent converter. It writes pandas DataFrames straight to SQLite with `to_sql` (MainTable, CodeStates, Link*, and a `Metadata` table), then indexes CodeStateID. It does **not** use the repo's writer.
  * `datasets/codebench.py` and `analytics/preprocessors/codebench.py` define the F24 AnalyticsConfig. The preprocessors:
    * link Run.Test to Submit via (SubjectID, AssignmentID, ServerTimestamp);
    * drop small classes;
    * flatten YAML link tables.
  * `database/writer/db_writer_factory.py` (`SQLIOFactory.create_writer`) → `SQLWriter` + `SQLWriterTableManager` + `SQLTableCodeStateWriter` is the repo's write path. Gaps likely to hit with CodeBench:
    * **Schema comes only from the spec.** The MainTable has spec columns only, and link tables come from `spec.link_tables`, which is empty in v1.0. Custom columns (e.g. `X-ExecutionTime`, `X-ProgramCorrectOutput`) and Link tables therefore need a CodeBench-specific spec YAML, loaded via `ProgSnap2Spec.from_yaml`. There is no extend/merge helper.
    * **Row-by-row work.** `SQLTableCodeStateWriter` does a SELECT and then an INSERT per CodeState, in its own transaction. `add_link_table_entry` commits per row. Both will likely be too slow for millions of rows, and are candidates for upstream PRs.
    * **Metadata table naming.** `SQLWriterTableManager` creates the metadata table as `CoreTables.Metadata`. The spec PDF says `DatasetMetadata`, and falconcode used `Metadata`. This needs checking.
  * `database/codestate/keystroke_codestate_writer.py` (read-only) rebuilds code from `SourceLocation` (an absolute character offset) plus `InsertText`/`DeleteText`.

## Raw data (`raw/2023-1`, `raw/2023-2`, `raw/2024-1`)

Layout: `<semester>/<classID>/{assessments/<assessmentID>.data, users/<userID>/...}`. Raw IDs are small integers:

| ID | Approximate range |
|---|---|
| class | 523–597 |
| user | 3000–6500 |
| assessment | 4800–5900 |
| exercise/problem | 600–5000 |

Counts per semester:

| Semester | Classes | Users | codemirror logs | code files | execution logs |
|---|---|---|---|---|---|
| 2023-1 (2.6 GB) | 7 | 270 | 24,739 | 24,806 | 24,806 |
| 2023-2 (2.2 GB) | 7 | 230 | 22,663 | 22,810 | 22,810 |
| 2024-1 (2.6 GB) | 8 (7–52 users each) | 241 | 25,300 | 25,458 | 25,502 |

For comparison, f24 is 2.8 GB on disk.

* **Users span classes and semesters.**
  * There are 664 distinct user IDs. 62 appear in more than one class, and 42 in more than one semester.
  * User IDs appear stable across semesters, so any SubjectID scheme must stay consistent if datasets are combined.
* **Per-user files:** `user.data`, `logins.log`, `eventos.log`, `codemirror/`, `codes/`, `executions/`, `grades/`, and sometimes `mousemove/`.
  * `eventos.log` and `mousemove/` are **not described** in `raw/codebench.md`.
  * `mousemove/` is almost always empty: 5 files in 2023-2, 258 in 2024-1.
* **`logins.log` and `eventos.log` are user-wide, not scoped to a class.** For one 2024-1 user they run from 2022-01 to 2024-08, so events must be filtered by date or class, or attributed by overlap.
  * `logins.log` holds `user/login.` and `user/logout.` lines. Logouts are much rarer than logins; f24 has 19.7k Session.Start but only 6.2k Session.End.
  * `eventos.log` holds JSON-ish lines recording page navigation, e.g. `{"date":"D/M/YYYY@H:M:S:ms","page":"turma/view","turma":"372","trabalho":..,"exercicio":..,"evento":"acesso|clickTabExercicio"}`. The `turma` field is a class ID and could help scope these events.
* **Assessments** (`.data` files) carry title, class, start/end, language (always "Python 3"), type (`homework` or `exam`), weight (sometimes 0), and the exercise list.
  * 55–61 exams per semester define an exercise as `A or B or C`; each student gets a random variant.
* **`codemirror/<assess>_<exercise>.log`** has lines of the form `YYYY-M-D H:M:S.ms#<event>#<payload>`.
  * Event types:
    * Keys: keydown, keyup, keypress (newer logs add `{"key":..}`), keyHandled.
    * Edits: `change`.
    * Mouse and touch: mousedown, dblclick, touchstart, contextmenu.
    * Editor: focus, blur, viewportChange, copy.
    * Navigation: `tab-click:<exerciseID>`.
    * Program: `saida_testar`, `submit`, `kill_program`.
  * `change` payloads are `{from:{line,ch},to:{line,ch},text:[...],removed:[...],origin}`. Origins seen: `+input`, `+delete`, `undo`, `paste`, `*compose`, `cut`, `redo`, `drag`, and None.
  * **Payloads can span multiple lines.** About 5% of physical lines don't start with a timestamp:
    * `saida_testar` ("test output") holds `$ python3 main.py` followed by the program's console output.
    * `submit` holds the feedback message.
    * The parser must join continuation lines onto the preceding event.
* **`codes/<assess>_<exercise>.py`** holds the final code only. 351 code files have no codemirror log, and 121 logs have no code file.
* **`executions/<assess>_<exercise>.log`** holds blocks separated by `*-*-*...`. There are two block types:
  * **Runs:** `== TEST (ts)` blocks contain `CODE`, then `OUTPUT` or `ERROR`. The sample has about 13k of these, while all of f24 has only **800 Run.Program events**.
  * **Submissions:** `== SUBMITION (ts)` blocks contain `CODE`, `EXECUTION TIME`, `TEST CASE n` (input / correct output / user output), then `GRADE n%`. Some submissions end in `ERROR` with no GRADE.

  Other notes on execution logs:
  * Timestamps have second precision and differ by a few seconds from the codemirror `submit` and `saida_testar` events.
  * **Every run and submission includes a full code snapshot**, so CodeStates for Run and Submit events are straightforward.
  * Tracebacks are mostly anonymized as `File "XXXX"`, but some leak paths such as `/home/codebench/codes/<assess>/<exercise>/main.py`.
* **Grades:**
  * `grades/<assess>.log` holds the assessment grade (0–10) plus counts of correct, incorrect, and blank.
  * `grades/final_grade.data` holds a single final course grade.
* **`user.data`** holds sociodemographic data: degree course, school type, PC access, prior programming experience, work, sex, birth year, etc.
* **The raw data has no problem descriptions, difficulty, or topic metadata.** f24's `Problem` link table has these, so they came from elsewhere.

## f24 target (`sample_data/codebench/f24`)

* **Format:** CSV MainTable (866 MB, 4.94M rows, 24 columns); Git CodeStates (one repo per Subject/Project); LinkTables pointing at YAML/TXT files in `Resources/`; an `analysis/` folder.
* **Term:** the README says the term is "2024/2", and timestamps run from 2024-05-12 to 2024-11-15. It **does not overlap any raw semester**.
* **IDs** are hashed integers (e.g. raw user 6303 becomes something like 1837898832). `ProjectID = "{AssignmentID}_{ProblemID}"`. There are 3 CourseIDs and 10 CourseSectionIDs.
* **Event counts:**

  | Event type | Count |
  |---|---|
  | File.Edit | 4.28M |
  | Run.Test | 189k |
  | File.Focus | 188k |
  | X-File.Blur | 186k |
  | Submit | 67.5k |
  | Session.Start | 19.7k |
  | Session.End | 6.2k |
  | Run.Program | 800 |

* **Columns by event type:**
  * **File.Edit:**
    * EditType is one of Insert, Delete, Undo, GenericEdit, Redo, Move. It is blank for 13% of edits.
    * `X-InsertText` is filled in for 75%.
    * `SourceLocation` is `Text:N` (looks like an absolute offset; base unclear).
    * `CodeStateSection` is `main.py`.
    * There is **no CodeStateID and no deleted text or length**, so code cannot be reconstructed from f24 edits.
  * **Submit:** CodeStateID (git hash), ProjectID, Score (0–1), Attempt, ExecutionID, `X-ExecutionTime`.
  * **Run.Test:**
    * Shares its Submit's ExecutionID and has an ExecutionResult.
    * ProgramInput, ProgramOutput, `X-ProgramCorrectOutput`, and ProgramErrorOutput hold URLs of the form `Resources/<Kind>/{Problem}_{Subject}_{n}.txt`.
    * There is **no TestID and no Score**.
  * **Run.Program:** CodeStateID and `X-ExecutionTime` only, with no output and no ExecutionResult.
  * **Session.\*:** no SessionID, no AssignmentID, and CourseSectionID only sometimes.
  * **All events:** `ToolInstances` = "Python 3.8.5; CodeMirror 6". `Order` is a global ordering. Metadata has `EventOrderScope=Global` and `Version=8`.
* **Known f24 defects (do not replicate):**
  * **None of the Run.Test Resource URLs resolve.** There is no `Resources/CorrectOutput/` folder, and the Input/Output/ErrorOutput files on disk are named `{a}_{b}.txt`, not `{Problem}_{Subject}_{n}.txt`.
  * ExecutionResult has a `' Error'` value with a leading space.
  * Run.Test is missing TestID, which the spec requires.
  * Session.* events are missing SessionID, which the spec requires.
* **f24 link tables** (ID columns + a URL pointing to YAML):

  | Link table | Content |
  |---|---|
  | Assignment | title, class, start/end, language, type, weight, exercises |
  | AssignmentSubject | grade per assessment |
  | CourseSubject, CourseCourseSectionSubject | final grade, approved |
  | Problem | difficulty, topic |
  | Subject | sociodemographics |

## User-wide logs are not course-scoped (verified 2026-11-13)

* `logins.log` and `eventos.log` are exports of a user's **entire** CodeBench history. They are copied into every class folder the user is enrolled in.
  * **Within a semester**, the copies for a user in several classes are byte-identical.
  * **Across semesters**, they are different exports. For example, user 1059's 2023-1 copy covers 2017-02 to 2023-11, and their 2023-2 copy covers 2021-06 to 2024-09.
* `logins.log` lines carry **no class information**.
* `eventos.log` lines carry a `turma` (class) field. In a 200-user sample:

  | `turma` value | Share of lines |
  |---|---|
  | This class folder's class | 67% |
  | Another class in the same raw data | 1% |
  | A class not in the raw data (e.g. 385, 414, older terms) | 31% |

* **`user.data` copies:**
  * **Within a semester**, all 35 multi-class pairs are identical. Each DB is one semester, so a plain `LinkSubject` per DB is sufficient; SubjectCourseTerm is not needed.
  * **Across semesters**, 35 of 64 pairs differ. Some later copies have most fields missing (e.g. user 1059), and some values are implausible (year of birth 2023). This should be noted in the README as a data-quality caveat.
* **Semester windows**, from the earliest assessment start to the latest assessment end:

  | Semester | Window |
  |---|---|
  | 2023-1 | 2023-07-24 to 2023-11-14 |
  | 2023-2 | 2023-12-03 to 2024-04-02 |
  | 2024-1 | 2024-04-14 to 2024-08-07 |

* **Date filter vs. class filter on `eventos.log`** (users deduplicated per semester). The two filters mostly agree:

  | Semester | Both keep | Both drop | In window, class not in data | Out of window, class in data |
  |---|---|---|---|---|
  | 2023-1 | 374k | 129k | 6.9k | 200 |
  | 2023-2 | 284k | 109k | 3.4k | 1.7k |
  | 2024-1 | 323k | 97k | 12.4k | 906 |

  The two disagreement columns:
  * *In window, class not in data* (1–4%) is activity in other CodeBench classes the student took at the same time (e.g. 537, 600, 585), or in an earlier class (e.g. 523 viewed during 2023-2).
  * *Out of window, class in data* (<1%) is activity in a dataset class after its last assessment deadline. It is concentrated in the months just after the window (e.g. 2023-2 classes viewed 2024-04 to 2024-07).
  * A handful of lines (≤12 per semester) have a missing or unparseable date.

## Conversion design decisions to document in the README (TODO at the end)

* Logins and page navigation are user-wide exports, and duplicate copies across class folders are collapsed.
  * Events with a known class are kept if that class is in the dataset, whatever their date.
  * Logins have no class, so they are kept only inside the semester date window.
* Logins carry no CourseSectionID, since a student may be in two classes. Page-navigation events take their CourseSectionID from `turma`.
* Filtering rules and the exact semester windows (see above), including how the filter disagreements were resolved.
* `LinkSubject` is per semester. Survey answers can change between semesters.
* Data-quality caveats: implausible survey values; tracebacks that leak paths; code files without logs and logs without code files.
* (Add every other conversion decision here as it is made.)

## Decisions (from Thomas, 2026-11-13)

1. **One SQLite DB per semester** (2023-1, 2023-2, 2024-1), written next to f24.
2. **Keep the raw IDs.** They are already de-identified.
3. **CodeStates** (metadata simply says `CodeStateRepresentation=Table`; no extra flag, since the InsertText/DeleteText columns make the keystroke edits evident):
   * File.Edit events carry an InsertText/DeleteText history that can reproduce code.
   * Run and Submit events also carry ground-truth snapshots in a CodeStates table. These come from the `CODE` sections in `executions/`, plus the final `codes/*.py`.
   * The spec needs updating to allow both at once. This goes in the custom spec, and as a proposal upstream.
4. **Capture everything in the raw data**, including run output, SessionID, TestID, page navigation (`eventos.log`), copy, paste, kill_program, and execution time.
   * Do not use the `X-` prefix. Use plain column names from the raw data, or propose clearer ones.
   * Inputs and outputs go in files under `Resources/` and are referenced by URL. Reuse one file when the content is identical (e.g. the same test input across a problem).
   * Run-log extras, such as execution time and correct output, become dataset-specific columns.
5. **Writing:** build the tables in memory and write them with sqlite3 or pandas.
   * **Reading** must go through the library, so it validates the data. This needs a custom CodeBench spec YAML.
   * Use the generated enums for existing columns, and constants or a custom enum for new ones.
6. **Link tables:** flatten the YAML-style data into columns with composite names, as `YAMLLinkURLPreprocessor.flatten_object` does. The nesting is one level deep.
7. **CourseID** is a numeric ID; the class name goes in a link table. CourseSectionID is the class number.
   * **Don't assign an ID when unsure.** Logins get no CourseSectionID. Page navigation takes it from `turma`.
   * **Which filter applies depends on whether the event's class is known:**
     * **Class known** (page navigation via `turma`; codemirror and executions via their folder): keep the event if the class is in the dataset, regardless of date. This keeps activity after the deadline in dataset classes, and drops activity in other classes.
     * **Class unknown** (logins): keep the event only if it falls within that semester's date window.
   * Report the counts kept and dropped by each filter in the README.
8. **Tests** are pytest, reading both the raw and converted datasets and comparing values or metrics computed from each.
   * Do not hard-code dataset values.
   * Skip, rather than fail, when the data is missing.

## Draft raw → PS2 mapping (to be confirmed)

| Raw source | PS2 |
|---|---|
| user dir | SubjectID |
| class dir | CourseSectionID (CourseID from class name?) |
| semester folder | TermID |
| assessment `.data` | AssignmentID + LinkAssignment; `type` → AssignmentIsGraded / column |
| exercise ID (from file name, `tab-click`) | ProblemID |
| `logins.log` | Session.Start / Session.End (+ SessionID) |
| codemirror `focus` / `blur` / `tab-click` | File.Focus / X-File.Blur |
| codemirror `change` | File.Edit (EditType from `origin`, SourceLocation, InsertText/DeleteText) |
| executions `TEST` (+ codemirror `saida_testar`) | Run.Program (CodeState, output, ExecutionResult) |
| executions `SUBMITION` | Submit (Score = GRADE/100, CodeState) + one Run.Test per TEST CASE |
| code snapshots in executions | CodeStates table (dedup by hash) |
| `grades/*.log`, `final_grade.data` | LinkAssignmentSubject, LinkCourseSectionSubject |
| `user.data` | LinkSubject |
