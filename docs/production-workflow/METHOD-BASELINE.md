# Methodological baseline and integrations

**State:** operational proposal of the design authorized for elaboration.
**Origin:** discussion of 2026-10-16 on governance documents, agent instructions
and executor adaptation. It does not prove the deployment of any tool.

## 1. Infrastructure before the product

The method may live in its own workspace or repository, with rules, prompts and
templates. That does not oblige a person in exploration to create a repo, name a
product or decide on branches. A mature product may incorporate the
infrastructure directly, preserving pre-existing documents and policies.

In this laboratory the entry files sit at the root. In an adopting product their
paths must be defined and indexed without overwriting existing rules. Use
`AGENTS.md`, with this spelling, as the method's convention; adapt location and
discovery to the real tool, without presuming that every tool reads the same file.

## 2. Three sets, not one package demanded in the first conversation

| Set | Content | Trigger |
| --- | --- | --- |
| Method infrastructure | METHODOLOGY, RULES, INDEX, prompt and template library | Adoption/implementation of the method; reusable before the product repo |
| Baseline of the adopting repo | Contextualized README, methodological entries or canonical references, AGENTS when there is delegated execution, applicability inventory | Constitution/incorporation of the repo and activation of the pertinent activities |
| Conditional complements | Adapters, skills, MCPs, CI, community, licenses, web publication, operation | Real need and the corresponding authorization; not mere presence in the catalog |

The index is mandatory as the map of this method's documentary baseline. A
section with references may suffice in a small adoption, provided it is an
explicitly identified canonical source; do not duplicate the index and divergent
inventories.

An available library does not mean an executed prompt. An available template does
not mean an instantiated product document. A proposed inventory does not mean an
installation. Every document remains subject to presentation in the chat.

## 3. Prompts, templates, skills and MCPs have different contracts

| Type | Defines | Does not demonstrate by itself |
| --- | --- | --- |
| Prompt | How to conduct an interaction and which context to use | Installed capability, consensus or external authorization |
| Template | Structure of a record, its fields and its trigger | Correct filling or approval |
| Skill | Reusable procedure, inputs, limits and evidence | Availability in every tool or permission for any action |
| MCP | Interface of tools/resources with defined access and effects | Unrestricted trust in the server or authorization of each operation |
| Agent adapter | Discovery, format and routing to canonical sources | Independent policy or untested compatibility |
| Specs/tasks executor | Translation and execution of contracts in its own format | Power to invent intent or ratify its own work |

Record adoptions in the [capabilities inventory](templates/CAPABILITIES-INTEGRATIONS.md).
Use real sources, versions and states. Do not catalog as "installed and
authorized" something merely cited in the conversation or found in the
environment.

## 4. Adapters and publication for machines

`CLAUDE.md` is conditional on the chosen integration. If adopted, it must route
to the canonical rules and add only verified particularities of the tool,
including scope, discovery and maintenance. Other agents may need other files. Do
not create them all preemptively, nor overwrite existing configuration.

Skills and MCPs have no universal installation path. Document scope (project,
user, session or another supported one), origin, access, secrets by secure
reference, external effects, install/removal and the person responsible.

`llms.txt`, if adopted, guides consumption of the published documentation.
`robots.txt` expresses web crawling rules. They are not interchangeable with
AGENTS or execution rules, they are not access control, and they need not be born
in a repo without a site. Their adoption requires a verified purpose and verified
consumer behavior.

## 5. Future bridge with Specify / Spec Kit

The [corrected preflight](SPECKIT-ADAPTATION.md) documents the later inspection of
files from the local snapshot and the proposed passage between conversation,
revision, ratification and execution. It distinguishes evidence read from
decisions reported, and does not yet confirm package integrity, runtime
compatibility or installation. In any divergence between this repository and
earlier external maps (such as `SPECS-TASKS-BRIDGE--smard-agent-flow-kit.md`),
the contract of [SPECKIT-ADAPTATION.md](SPECKIT-ADAPTATION.md) prevails.

The user brought the following conditional readings of the project as design
references. They must be located and verified in the chosen version before any
integration is implemented:

| Surface altered | Technical reading indicated | Contract to verify |
| --- | --- | --- |
| CLI | Shared Command Application Architecture; Specify CLI Command Architecture | Shared boundary, registration, modules and mirrored tests |
| Command MCP | Shared Command Application Architecture; Specify MCP Command Architecture | Types, inventory, effects and local protocol |
| Agent integration | Agent Integration Design | Delivery routes, formats, registration, install and removal |
| Workflow step | Workflow Step Design | Registration, validation, execution, resume and packages |
| Deterministic behavior | Testing deterministic behavior | Positive/negative cases and regression evidence |

These titles were initially supplied in the conversation. The later inspection
recorded in the preflight covers part of these sources; the remaining contracts
still await specific reading. No executable compatibility has been confirmed.

Before choosing a supported extension, an external complement or a modification
of the executor, record: version and source; available mechanism; inputs and
outputs; ownership of generated files; resume; removal; tests; update risks. Do
not duplicate the native source of specs and tasks.

The integration contract must preserve the ZERO and the requirements as the
origin of intent, pass traceable decisions and criteria, and present every
generated document in the chat. Automatic generation creates no exception to the
dialogue and does not authorize execution of an unratified commitment.

## 6. What was not activated

Persistent memory and succession have their own contract in
[SESSION-MEMORY.md](SESSION-MEMORY.md). The two records live, by proposal, in a
local space excluded from Git. The precompact event requires a verified adapter;
no hook or transport between hosts was activated by this baseline.

This baseline adds documentary guidance. It installs no skills or MCPs, creates
no CLAUDE.md, llms.txt or robots.txt, enables no new jobs, alters no remote rules
and implements no Specify commands. The need for and authorization of those
actions will be decided when their triggers occur.