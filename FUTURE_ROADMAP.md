Yes. Treat TN3270 as a structured UI, not a keyboard. Use a layered stack where intents compile to terminal actions through a typed screen model.

**1) Fundamental architecture**

* Layers:

  1. **Device**: s3270 session pool. One job per process. Idempotent connect, reset, close.
  2. **Terminal model**: parse 3270 data stream to fields with coords, length, protection, attrs. Expose a 24x80 “virtual DOM”.
  3. **Screen types**: classifier maps a raw buffer to a typed `Screen{type, fields, actions, anchors, message_line}` with confidence.
  4. **Navigator**: action library with preconditions and effects. Compiles `Intent` → `{fill fields, AID}`.
  5. **Planner**: goal stack, checkpoints, rollback, human escalation.
  6. **Telemetry**: event-sourced traces for replay and learning.
* Never script keys directly at the planner. Only call typed actions on recognized screens.

**2) State machine complexity**

* Build a **probabilistic screen classifier**. Inputs: protected field layout, input field layout, attribute bytes, PF legend positions, title anchors, message line regex. Ignore volatile text.
* Create a **layout signature**: a 24x80 mask of P/U/H attributes plus field spans. Hash it. Use LSH for nearest neighbor. Keep per-type regex on title or message lines to raise confidence.
* Maintain an **open-world screen graph**. Unknown screens get clustered online. Human labels seed new types. Version screen types by signature hash.
* Transitions are `ScreenType × AID → ScreenType’` with probabilities and expected message regex.

**3) Reliability vs speed**

* Use **checkpoints** only at decision points. Fill all fields on a screen, send one AID, then verify.
* Use **cheap guards**: wait for keyboard unlock, then check message line or a single anchor field. Full re-parse only on mismatch.
* **Session pool**: keep warm TSO/CICS sessions to amortize logon cost. Health-check with a 1-field ping.
* **Speculative fast path**: if screen confidence > τ and transition likelihood high, skip deep verification. Fall back on mismatch.
* **Host pacing**: always `Wait(Unlock)` not fixed sleeps. Bound with adaptive timeouts from latency histograms.

**4) Learning and adaptation**

* Record **demonstrations**: `{buffer_before, action, buffer_after}` with human intent labels. Build a transition graph automatically.
* Learn **screen extractors** by weak supervision: anchors + heuristics + CRFs or simple CNN over 24x80 tokens. Promote to rules once stable.
* Synthesize **skills** from traces: mine frequent path templates with variable slots. Emit DSL snippets instead of hand-written YAML.
* Active learning loop: low-confidence screens prompt a one-click label in a reviewer UI, then retrain the classifier.

**5) Error recovery philosophy**

* Model **modal error states** explicitly as types with allowed actions: `KEYBOARD_LOCK`, `PROT_FIELD_ERR`, `SESSION_TIMED_OUT`, `INVALID_PF`, `NOT_AUTHORIZED`.
* Each has a **recovery policy** with preconditions, ranked actions, and success tests. Example: `KEYBOARD_LOCK → {Reset, Clear, PF3, PF12}`, stop when unlock and anchor visible.
* Use **constraint-based planning**: at runtime solve for an action that satisfies current mode constraints and goal invariants. If unsat, run the global reset macro to a safe home.

**6) Testing without the real thing**

* Build a **deterministic replayer** from captured s3270 traces. Reproduce buffers, locks, and timings.
* Add a **chaos shim**: inject random delays, spurious message lines, intermittent locks, stale screens, and AID drops to match P95 latency and failure distributions.
* Create **contract tests** per skill: preconditions, expected anchors, and invariants on parsed values. Run nightly against emulator plus chaos.
* If you can get any production PCAPs or logs, sanitize and replay to tune distributions. If not, calibrate with SMEs.

**7) Human‑AI collaboration model**

* Use **ask-on-ambiguity**. When classification or option parsing confidence < τ, render the screen, highlight parsed options, and request a choice. Store the selection to train the extractor.
* Support **partial automation**: AI fills fields and proposes the AID. Human confirms. Escalation SLA should be visible to the caller.
* Allow **policy knobs** per flow: fully automatic, ask on risk, or always confirm at high-impact steps.

**8) Fundamental value**

* Highest leverage: create a **stable API facade** over key flows now, and capture telemetry to guide decommission later.
* Dual track:

  * **Near term**: wrap critical, high-volume, stable screens as REST skills.
  * **Long term**: use traces and field semantics to spec real host APIs or migration targets. Prioritize by volume × pain.

**9) Observability**

* **Event sourcing**: every step logs `{ts, session_id, screen_hash, screen_type, anchors, fields_changed, action, aid, unlock_ms, parse_conf, transition_prob, error_mode}`.
* Store **raw buffers** and an **image snapshot** for each step. Keep **datastream hex** behind a feature flag for deep forensics.
* Provide a **timeline viewer** with play, step, diff of fields, and mode overlays. Deterministic replay from logs is mandatory.
* Add **counters**: locks per 100 actions, time in error modes, unknown screen rate, rollback rate.

**10) Success metrics**

* **Outcome**: tasks completed per hour, automation coverage by flow, first-pass success rate, human escalation rate, business handle time.
* **Reliability**: P50/P95 time to goal, rollback count per task, keyboard locks per task, session resets per day, unknown screen discoveries per 1k steps.
* **Learning**: mean time to add a new screen type, label-to-production latency, classifier accuracy on holdout traces.
* **Economics**: cost per completed task vs manual baseline, developer-hours saved, rework avoided, incidents avoided.

**Minimal DSL sketch**

```yaml
screen_type: TSO_LOGON_1
signature: a1f3c9e2   # hash of layout mask
anchors:
  - {text: "TSO/E LOGON", row: 1, col: 30, regex: true}
fields:
  USERID:  {row: 6, col: 15, len: 8,  type: text, protected: false}
  PASSWORD:{row: 7, col: 15, len: 8,  type: secret, protected: false}
message_line: {row: 23, col: 2, len: 76}
actions:
  login:
    fill: [USERID, PASSWORD]
    aid: Enter
    expect:
      next_types: [TSO_LOGON_2, TSO_READY]
      reject_regex: ["invalid", "not authorized"]
    checkpoints:
      - {anchor: {text: "READY"}, timeout_ms: 1500}
recovery:
  mode: KEYBOARD_LOCK
  policy: [Reset, Clear, PF3, PF12]
```

**Implementation notes**

* Use `Wait(Unlock)` and `ReadBuffer` consistently. Avoid sleeps.
* Build the layout mask from field attributes, not characters. Hash that for identity.
* Keep a **global reset** to a known home. Make it idempotent.
* Do not share sessions across requests unless flows are strictly serialized. Use a pool keyed by tenant.

This keeps the robot off the typewriter and on a typed UI with goals, guards, and learning.

