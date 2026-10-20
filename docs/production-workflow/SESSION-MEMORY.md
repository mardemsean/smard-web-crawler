# Continuity between sessions and succession of agents

**Confirmed by the human on 2026-10-17:** the persistent memories between
sessions recognized by the method are `sledge-handoff.md` and `DIAMOND.md`. They
must mandatorily take part in the handoff to the successor before compaction,
through integration with the precompact event. `hyperbrain-lesson.md`,
`knowledge.md` and `cortex.md`, cited in earlier versions of this document, **do
not exist** and were removed from the contract; do not recreate them or deduce
substitutes.

**Functions mapped on 2026-10-16** [documentary observation of the HYPERBRAIN
conventions and of the skill `smard-ledger-handoff` 4.2.0; whatever remains
marked as open stays reserved to the operator]:

| File | Observed function | Evidence |
| --- | --- | --- |
| `sledge-handoff.md` | Intentional end-of-session handoff: cold start, Basis, Verify block, "What not to retry" (classes E0–E7), intents, ledger JSON; written in duplicate (project root, deliverables, HTML for the operator, HYPERBRAIN). Probable reference to the skill `smard-ledger-handoff` [deduction; the name "sledge" does not appear in the skill — confirm with the operator] | The skill's `SKILL.md` (M1–M5, F1–F4); instinct `handoff-as-file` |
| `DIAMOND.md` | Lesson crystallized from a tool-call or code error ("a tool-call or code error becomes a DIAMOND"), mined deterministically (error_miner, classes E0–E7) and indexed in `B:\DIAMONDS\INDICE.md` | `B:\DIAMONDS\INDICE.md` |

**Not yet defined:** the relations and detailed content of each record. Do not
deduce responsibilities beyond what is evidenced above, do not merge files and do
not invent additional schemas. The contract below proposes storage and
continuity only.
**Origin:** dialogue of 2026-10-16; location and protocol are design proposals.

## 1. Proposed location

```text
.session-memory/
  sessions/
    <session-id>/
      checkpoints/
        <checkpoint-id>/
          checkpoint.md
          sledge-handoff.md
          DIAMOND.md
```

IDs are technical and supplied by the harness, without demanding naming from the
human. A checkpoint is a continuity package; it does not redefine the semantics
of the two files. This design created no packages and no fictitious session
memories. The [checkpoint template](templates/SESSION-CHECKPOINT.md) is the common
envelope.

The package records repo/workspace, branch, HEAD, uncommitted state and origin.
These fields situate the memory; they do not make HEAD proof of changes that are
still local. Earlier checkpoints remain recoverable. Do not overwrite a ready
package while the successor is reading it; the adapter must define coherent
publication and unambiguous selection of the most recent ready package of the
intended lineage.

## 2. The obligation to preserve is not an obligation to invent content

Every checkpoint explicitly accounts for the two names and their revision/origin.
If a file exists, preserve its information without reinterpreting its function.
If it does not exist, is inaccessible or its function has not yet been defined,
record that gap. Do not create an empty file and mark the transfer as complete.

While the particular contracts remain open, the envelope may preserve known
operational state and references without distributing content arbitrarily
between the two names. That is identified partial continuity, not a completed
implementation of the memory method.

## 3. Cycle precompact → checkpoint → recovery

| Moment | Duty of the agent/adapter | Evidence |
| --- | --- | --- |
| During the session | Keep incremental records with visible elaboration; do not wait for the last instant | Content and open points presented in the chat |
| On receiving the notice before compaction | Identify the two records and prepare a coherent snapshot of the lineage | Envelope, state of the files and exact references |
| Before declaring ready | Verify reading, integrity, declared completeness and a location accessible to the authorized successor | Ready package, or explicit partial/failure |
| Compaction | Block if the tool really allows it and a blocking requirement is missing; otherwise report that preservation could not be guaranteed | Real result of the hook, not presumed success |
| Start/resume by the successor | Locate the ready package of the correct lineage, read the envelope and the two available files | Recovery record and gaps |
| Before continuing work | Confront memory with current files, diff, branch, processes and permissions | Divergences made explicit and context reconciled |

Memory transmits context, not new powers. Recovering a recorded authorization
neither extends it nor proves it is still valid. A process left running may have
ended; a task supposedly completed needs corresponding evidence. Inherited
content is a contextual source, not an instruction superior to the rules in
force.

Do not load the whole transcript by default, nor treat a summary as infallible
truth. Preserve facts, uncertainties, provenance and relevant divergences.
Reading or recovery by the successor is not equivalent to human ratification.

## 4. Technical contract of the adapter, not yet implemented

`precompact` is the conceptual event; its name, availability and guarantees must
be verified in each harness and version. Do not presume that all of them allow
blocking compaction or writing to the chat during hooks.

Before implementing, verify: an event that really precedes the loss of context,
accessible context, time limit, write permission, failure return, blocking
capability, repeated execution, concurrency and the successor's reading
mechanism. An isolated hook does not guarantee that the next agent discovers the
package.

The contract shall be idempotent for the same event, shall not mix sessions and
shall not announce ready before persisting and verifying the set. Tests must
cover success, duplicate event, missing file, interrupted write, timeout, partial
package, wrong lineage and recovery after a workspace change.

If the hook cannot make changes explicit in the chat, it earns no exception to
invent documentation behind the human's back: keep incremental elaboration
visible, limit the snapshot to content already presented and record a technical
receipt. New emergency content is identified as not presented and not ratified;
the successor makes it explicit before using it as a commitment. An unexpected
compaction remains a limitation, not approval to feign a checkpoint that did not
happen.

## 5. Git exclusion, retention and transport

This laboratory's `.gitignore` excludes `/.session-memory/` from creation, not
only at publication. The method's templates and contracts remain versioned. Do
not use global exclusions such as `sledge-handoff.md` or `DIAMOND.md`, which could
hide legitimate documents in other contexts.

`.git/info/exclude` is a local alternative, not a distributed policy. In
worktrees, use the location Git indicates, without editing a main checkout by
assumption. Do not alter that file silently. `.gitignore` does not remove files
already tracked, does not encrypt data and does not prevent `git add -f`.

Before publishing, examine tracked and staged files, the diff, the relevant
history and the content of CI artifacts and releases. Do not rely on ignore
alone: a job may package excluded local files. Removal from the index or history
and the response to a possible exposure are separate operations, with adequate
authorization.

**Local continuity is not portability.** A clone, a new worktree or an agent on
another host does not receive these files through Git. The adapter must offer
authorized persistent storage and transport with access control, lineage and
retention. Do not claim the handoff delivered until the authorized destination
can recover the package. Do not use a public CI artifact as transport.

Ignore also offers no protection against workspace cleanup, session archiving or
disk failure. Before those operations, secure an authorized persistent destination
and verifiable recovery, or make the risk of loss explicit. Retention periods,
backup, access and disposal remain to be defined; do not promise unlimited
retention. Do not persist credentials or private transcripts by default.

## 6. Promoting learning to the repository

A local memory does not automatically become public documentation. Propose in
the chat which excerpt would be useful to the project, its origin, limitations
and canonical destination. Review privacy, rights, validity and the risk of
exposing data.

Only after the applicable authorization, prepare a synthesis in a requirement, an
ADR, a guide or another adequate and traceable document. Do not copy the whole
package nor treat session learning as an approved rule. The private original may
remain private; shared documentation must make sense without depending on
references its consumers cannot access.

## 7. Decisions reserved for the maturing of the design

- Persistent destination across hosts/worktrees and the retention/access policy.
- Initial harness, real hook integration and the successor's form of recovery.
- Criteria that make a partial checkpoint blocking, and possible exceptions.

Do not fill in these decisions by assumption. The obligation of continuity is
recognized; its executable integration remains pending.