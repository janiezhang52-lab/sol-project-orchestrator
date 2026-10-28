# Sol immutable product contract v1

[简体中文](PRODUCT-CONTRACT.md) | English

Status: `FROZEN_PRODUCT_CONTRACT_V1`

This contract derives from the V9 four-role chain accepted on Windows and macOS, and Sol MVP 0.3, which completed the full chain on both platforms. Git compatibility may extend implementation support but must not change this contract.

This is the public specification of required product behavior. Implementation, independent acceptance, technical closeout, and the user's product decision are separate facts. See [public provenance](../provenance/PUBLIC_PROVENANCE.en.md) for v0.3.3 identity and evidence boundaries. This English explanation does not change the frozen contract.

## Product commitment

The user interacts only with `00｜Sol 项目总控` (Sol Project Controller). In the same saved project, Sol orchestrates three distinct visible role tasks:

1. `01｜任务执行` (Execution): deliver the frozen goal; cannot accept its own work.
2. `02｜独立验收` (Independent Acceptance): independently inspect the goal and real artifacts, read-only; cannot replace technical closeout.
3. `03｜技术收口` (Technical Closeout): check that execution and acceptance concern the same goal, that evidence is complete, and that blockers are honestly recorded; determine whether the workflow can reach the user's product-decision gate.

Fixed sequence:

`立项 → four visible tasks ready in the same project → 去执行 → execution → independent acceptance → technical closeout → user product decision`

## Invariants

- The four visible tasks are controller, execution, independent acceptance, and technical closeout. Do not remove, merge, or replace them with hidden agents.
- `execution=COMPLETE`, `acceptance=PASS`, and `closeout=TECHNICALLY_CLOSED` are three different facts.
- `TECHNICALLY_CLOSED` is not `PRODUCT_ACCEPTED`.
- Only the user's explicit product decision in the controller task can produce `PRODUCT_ACCEPTED`.
- Project binding requires a nonempty real `projectId`, the exact project root, `hostId`, and current controller-task identity. Sharing a working directory alone is insufficient.
- The frozen goal must not trigger product writes before `去执行`.
- Orchestration progress comes from one authoritative local ledger. Requests, chat text, and agent memory cannot become a second state source.
- A Host mutation must have a ledger intent first. An unknown outcome permits reconciliation or stopping, never blind resending.
- The agent executes only the driver's single next action and returns the raw Host observation; it does not select the next stage itself.
- Technical failure, revision required, product rejected, and product accepted remain distinct terminal states. Do not start another revision round automatically.

## Git compatibility boundary

- Sol control state must stay outside the user's project tree.
- Sol and its three roles must not run Git commands or directly modify `.git/**`.
- The normal Git-compatible product gate requires that the working tree contain only product changes allowed by the frozen goal, with no Sol control files.
- Codex Host checkpoints are observed separately by an external black-box harness. Checkpoint paths, object forensics, and actor-attribution rules must not be placed in the runtime Skill or role prompts.
- If a user requires every byte of the Host's `.git/**` to remain unchanged, report honestly that the current Codex saved-project environment cannot guarantee this; do not redefine the goal.

## Change rule

Any change to the role count, role responsibilities, fixed sequence, user's product-decision authority, or Git commitments above is a `PRODUCT` change. Development of such a change must stop without the user's explicit approval of each item.
