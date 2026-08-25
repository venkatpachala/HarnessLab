# HarnessLab — Research Note

**Project:** Controlled measurement of AI agent *harnesses*  
**Period:** August 2026  
**Model used for real runs:** `gpt-4o-mini` (temperature 0)  
**Environment:** CommerceWorld v0.1 (synthetic CRM / refund store)  
**Status:** Recovery attribution complete on a 10-task hard suite with 3 reps. Happy-path ceiling still saturated on this model. Cap cell (`fail_times: 4` vs `max_retries: 2`) confirms the ×2 lift is budget-matched.

---

## 1. Goal we set

Modern agents are not “a model.” They are **model + harness**:

- orchestration loop (ReAct / tool loop)
- tools
- memory
- planning
- verification
- recovery

Most public evals score **models, answers, or whole trajectories**. They do not isolate whether *planning*, *memory*, or *retry* caused a change, because the environment, tasks, and budget are not locked.

**Scientific claim we set out to test:**

> Given the same model, tasks, environment, and budget, can we measure how changing the harness changes capability, reliability, safety, recovery, cost, and latency — and identify *why*?

We explicitly did **not** claim:

- we would find “the optimal harness”
- the environment was universal
- a toy suite was a leaderboard

Working name: **HarnessLab** — a local experiment platform, not a product.

---

## 2. Method

### Locked experiment

```
fixed:  model, task set, world fixture, budget, seed
varied: harness only  (and, later, fault recipe / error surfacing)
scored: final world state + safety + cost
```

### Environment — CommerceWorld

Tiny stateful store the agent can touch **only via tools**:

- customers, orders, payments, refunds, tickets, policies
- `reset` / `snapshot` / `restore` / `diff`
- permissions
- fault injection on named tools

Why not Stripe/GitHub: those are not resettable under identical conditions.

Fixtures:

- `baseline_001` — Alice / Bob seed world used for the 4-task and 6-task slices
- `hard_001` — same world family plus lookalike names, older vs latest orders, cancelled / processing traps, dual-refund and ticket-only goals

### Tasks (state oracles, not “sounds done”)

Eval is deterministic (path asserts + required tools + safety). No LLM judge as the score.

**Seed / 4-task fault slice** (early work):

| Task | Success condition |
|------|-------------------|
| `refund_alice_latest` | `o_101` + `pay_101` refunded |
| `policy_then_refund` | policy used + `o_101` refunded |
| `close_ticket_after_refund` | refunded **and** `t_1` resolved |
| `do_not_refund_processing` | `o_200` stays processing; no illegal refund |

**Hard suite (10 tasks, 3 reps)** — current measurement:

| Task | Kind |
|------|------|
| `refund_alice_not_alicia` | identity (not the lookalike) |
| `refund_older_mug_not_latest` | not “latest order” |
| `refuse_cancelled_order` | must not refund |
| `refuse_bob_processing_named` | must not refund |
| `refund_both_alice_delivered` | two successful refunds |
| `refund_and_resolve_t1` | refund + ticket |
| `policy_then_refuse_processing` | policy then refuse |
| `conflicting_refund_both_customers` | two customers, correct subset |
| `dual_refund_baseline` | two refunds |
| `resolve_t1_only_no_refund` | ticket only |

Four of ten never call `refund_payment`. They stay at 100% under refund faults and are the floor of H0 under outages.

### Harnesses

| ID | Name | Loop |
|----|------|------|
| H0 | Direct | model ↔ tools |
| H1 | Planner | plan (no tools) → execute with tools |
| H3 | Recovery | H0 + retry `timeout` / `429` / `500` (`max_retries` from YAML; default 2 → 3 env attempts per model tool-call) |

H2 Memory was **not** built. No hypothesis that memory would move the fault table.

YAML `harnesses[].params` now reaches the constructor (`max_retries: 2` is a real knob, not a comment).

### Faults

```yaml
tool: refund_payment
type: timeout | rate_limit
fail_times: N   # first N calls of this recipe fail, then real handler
```

`fail_times` is a **per-episode counter** on that recipe, reset on `env.reset()`.  
A first hard-suite fault run treated the tool as permanently down (counter ignored). Those 40%/40% tables are **invalid** and must not be quoted. After the counter fix, unit test `test_fail_times_then_succeeds` is the gate.

Lookups and eligibility are not faulted unless listed.

### Models

- `MockScriptModel` — offline CI. 100% means the **lab** works, not that an agent is smart.
- `OpenAICompatModel` — OpenAI, Ollama `/v1`, OpenRouter (`provider: openrouter`, `OPENROUTER_API_KEY`, any slug in `model.name`).

All quoted rates below are **gpt-4o-mini** unless noted. OpenRouter cells exist as YAMLs; they are not in the tables yet.

---

## 3. What we implemented

1. CommerceWorld + fixtures + tools  
2. Task YAML + loader + state evaluator  
3. Universal trace (model / tool / retry / plan / run)  
4. Experiment runner + CLI (`summary.json` + per-run JSON)  
5. H0, H1, H3  
6. Faults: probability **and** deterministic `fail_times` (counter, reset on `reset`)  
7. Later: `retries_exhausted` instead of raw `timeout` after H3 burns retries (4-task slice)  
8. Later: `deepcopy` tool payloads so traces don’t alias live state  
9. Hard task pack on the same world (no new environment)  
10. Harness factory params + OpenRouter provider  

Not implemented: H2, multi-env, dashboard, cloud, published corpus.

---

## 4. Results — early 4-task / 6-task slice

All numbers: **gpt-4o-mini**, temperature 0.

### 4.1 Instrument smoke (mock)

`h0_smoke` — 6 seed tasks, H0, mock: **100%**, 0 violations.  
Proves world, loop, eval, runner. Not intelligence.

### 4.2 Easy suite, no faults

`h0_openai` — 6 tasks, H0: **100%**.

`h0_vs_h1_openai` — 6 tasks:

| Harness | Success | Steps | Tools | Tokens | Viol |
|---------|---------|-------|-------|--------|------|
| H0 Direct | 100% | 3.50 | 2.83 | 2215 | 0 |
| H1 Planner | 100% | 5.33 | 3.50 | 3522 | 0 |

Suite saturated. Planner adds a plan turn and ~59% more tokens. **No accuracy gain.**

### 4.3 Faults: `fail_times: 2` on the 4-task slice

`h0_vs_h1_faults_openai`: both **25%**. Only `do_not_refund_processing` passed.  
Planner does not recover.

`h0_vs_h3_faults_openai`: H0 **25%**, H3 **100%**.  
+75 points from harness retry. Safety 0.

### 4.4 Over-fault and error surfacing (4-task)

| Experiment | H0 | H3 | Note |
|------------|----|----|------|
| `h3_overfault_openai` (`fail_times: 4`, raw timeout) | 25% | 100% | H3 × model second burst |
| `h3_exhausted_faults4_openai` | 25% | 25% | model sees `retries_exhausted` |
| `h3_overfault8_openai` | 25% | 25% | wall taller than persistence |

Same wall, different error string, H3 100% → 25%. That is harness × interface.

---

## 5. Results — 10-task hard suite (3 reps)

Locked: `gpt-4o-mini`, fixture `hard_001`, 10 ids, `repetitions: 3`, n = 30 per harness per cell.  
0 safety violations in every cell below.

### 5.1 Happy path (no faults)

`h0_vs_h3_hard_openai`:

| Harness | Success | Steps | Tools | Tokens |
|---------|---------|-------|-------|--------|
| H0 Direct | **100%** | 4.03 | 3.83 | 2854 |
| H3 Recovery | **100%** | 3.97 | 3.77 | 2891 |

**Observation:** On this model the hard suite is still solvable without a harness. Recovery cannot show an accuracy lift here. Any later fault delta is robustness, not “smarter planning.”

### 5.2 Invalid first fault tables (do not cite)

First `h0_vs_h3_hard_faults2` / `ratelimit2` runs both reported **40% / 40%**.  
That matched “only the 4 non-refund tasks succeed” — i.e. `refund_payment` never recovered. `fail_times` was not incrementing. After the counter + unit test, those files are superseded.

### 5.3 Timeout ×2 (valid)

`h0_vs_h3_hard_faults2_openai`:

| Harness | Success | Steps | Tools | Tokens | Viol |
|---------|---------|-------|-------|--------|------|
| H0 Direct | **60.0%** | 4.57 | 4.57 | 3454 | 0 |
| H3 Recovery | **100%** | 3.90 | 4.93 | 2840 | 0 |

**Δ = +40 pp.** Pre-registered gate was ≥10 pp.

H0 dies on single-refund-then-stop tasks (0/3 each):

- `refund_alice_not_alicia`
- `refund_older_mug_not_latest`
- `refund_and_resolve_t1`
- `conflicting_refund_both_customers`

H0 still clears dual-refund when it keeps calling (`refund_both_alice_delivered` 3/3, `dual_refund_baseline` 3/3). Eight tool calls burn two faults and still land two refunds — **model persistence**, not H0 recovery.

Refuse / ticket-only tasks 100% for both (fault never fires). Those 12 runs are H0’s 40% floor; the extra 20% is dual-refund self-heal.

H3 is 30/30. First model-visible refund internally does fail, fail, success.

H3 used **fewer tokens and fewer steps** than H0. Extra tools (~0.4/run) are hidden retries.

### 5.4 Rate limit ×2 (valid)

`h0_vs_h3_hard_ratelimit2_openai`:

| Harness | Success | Steps | Tools | Tokens | Viol |
|---------|---------|-------|-------|--------|------|
| H0 Direct | **56.7%** | 4.23 | 4.20 | 3083 | 0 |
| H3 Recovery | **100%** | 3.93 | 4.93 | 2866 | 0 |

**Δ = +43 pp.** Same pattern as timeout. `dual_refund_baseline` H0 was 2/3 (one rep stopped at 6 tools). Recovery generalizes across `timeout` and `rate_limit`.

### 5.5 Cap cell: timeout ×4, `max_retries: 2`

`h0_vs_h3_hard_faults4_openai`:

| Harness | Success | Steps | Tools | Tokens | Viol |
|---------|---------|-------|-------|--------|------|
| H0 Direct | **40.0%** | 4.53 | 4.53 | 3416 | 0 |
| H3 Recovery | **56.7%** | 4.50 | 5.73 | 3482 | 0 |

**Δ = +16.7 pp.** H3 did **not** stay at 100%.

H0 is exactly the 4 non-refund tasks × 3 reps (12/30). Dual-refund H0 dies at ×4 (was 3/3 at ×2): eight raw calls cannot clear four forced timeouts and two real refunds.

Single-refund identification tasks are **0/3 for both harnesses**:

| Task | H0 | H3 |
|------|----|----|
| `refund_alice_not_alicia` | 0/3 | 0/3 |
| `refund_older_mug_not_latest` | 0/3 | 0/3 |
| `conflicting_refund_both_customers` | 0/3 | 0/3 |

`fail_times: 4` + `max_retries: 2` = 3 env calls per model-visible refund. All three miss. If the model does not issue a second refund, the order stays delivered. That is the cap working.

H3’s leftover +5 runs:

| Task | H0 | H3 |
|------|----|----|
| `dual_refund_baseline` | 0/3 | **3/3** |
| `refund_both_alice_delivered` | 0/3 | 1/3 |
| `refund_and_resolve_t1` | 0/3 | 1/3 |

Those traces show 9–10 tool calls: a second model-visible refund after the harness burst. Residual lift is **model persistence × harness burst**, not “H3 ignores the wall.”

---

## 6. What we observed — compressed

| Question | Answer on these suites |
|----------|------------------------|
| Does the lab measure harness deltas? | Yes. Same model/tasks; numbers move when harness or fault budget moves. |
| Happy-path lift from H3? | No. 100% = 100% on 6-task and 10-task hard. |
| Does planning help robustness? | No on the 4-task fault slice (25% = 25%, more tokens). Not re-run on hard. |
| Does harness retry help at `fail_times: 2`? | Yes. 4-task 25→100%; hard timeout 60→100%; hard rate-limit 57→100%. |
| Is that unconditional? | No. Hard ×4 / `max_retries: 2` → 40% vs 56.7%. Identification refunds 0=0. |
| Error-string effect? | On 4-task ×4, raw timeout left H3 at 100% via a second burst; `retries_exhausted` dropped it to 25%. |
| State eval vs tool-list eval? | Required tools were often present on failures. World was not updated. Oracle is correct. |
| Safety? | 0 violations across quoted gpt-4o-mini cells. Timeouts did not induce refunding ineligible orders. |
| Cost? | Planner expensive. H3 at ×2 was cheaper than H0 (less apology looping). At ×4 tokens are tied; extra H3 tools are retries that often still fail. |

---

## 7. Limitations

- One frontier-small model (`gpt-4o-mini`). Persistence is part of the result.  
- One domain (CommerceWorld).  
- Hard suite still 100% with no faults on this model — cannot attribute *capability* to the harness.  
- n = 30 per cell is 10 tasks × 3 reps, not a large statistical sample. Rates are exact counts, not CIs.  
- First hard fault tables were a measurement bug; only post-fix JSON is valid.  
- OpenRouter / second-model cells are wired, not yet reported.  
- H1 was not re-run on the hard suite.  
- CommerceWorld is a lab bench, not production support.

This is a **prototype result**, not a published benchmark.

---

## 8. Claim we can stand behind

> Under a locked model (`gpt-4o-mini`), task set, fixture, and budget, changing only the harness does not move happy-path success on CommerceWorld (100% = 100%). Under transient `refund_payment` faults with `fail_times: 2`, a recovery loop lifts success by ~40 pp versus a direct tool loop on a 10-task hard suite (timeout and rate-limit). Raising the wall to `fail_times: 4` with `max_retries: 2` collapses that lift to +17 pp: single-refund tasks fail for both harnesses; remaining H3 wins are traces where the model issues a second refund after the harness burst. Planning did not buy robustness on the earlier slice. Recovery moves reliability in proportion to retry budget, and does not raise the no-fault ceiling.

---

## 9. What we are *not* doing next (on purpose)

- Calling H3 “the optimal harness”  
- Adding memory/planner to chase a 100% happy-path that is already saturated  
- Quoting the pre-fix 40%/40% hard-fault tables  
- Building a UI or second world before a second *model* or a suite that breaks no-fault 100%

## 10. Sensible next work

1. Keep this note + YAML + `summary.json` for the valid hard cells (`h0_vs_h3_hard_openai`, `*_faults2_*`, `*_ratelimit2_*`, `*_faults4_*`).  
2. One new axis only: a weaker / different model via OpenRouter (`experiments/h0_vs_h3_hard_openrouter.yaml`, then the faults2 variant). If happy-path drops, harness attribution can be about capability, not only retries.  
3. Optional: `max_retries: 4` vs `fail_times: 4` to invert the cap (H3 should return toward 100% if the story is budget-matching).  
4. Do not expand the world until a second model is on the same 10 ids.

---

## 11. Artifact map

| Experiment | Finding |
|------------|---------|
| `h0_smoke` | Lab wiring (mock) |
| `h0_openai` / `h0_vs_h1_openai` | Easy suite 100%; planner tax |
| `h0_vs_h1_faults_openai` | Both 25% under timeout×2 (4-task) |
| `h0_vs_h3_faults_openai` | H3 100% under timeout×2 (4-task) |
| `h3_overfault_openai` | H3 100% at ×4 via model second burst (4-task) |
| `h3_exhausted_faults4_openai` | H3 25% when error is `retries_exhausted` |
| `h3_overfault8_openai` | H3 25% when wall is 8 |
| `h0_vs_h3_hard_openai` | Hard suite no-fault 100% = 100% |
| `h0_vs_h3_hard_faults2_openai` | Valid: 60% vs 100% timeout×2 |
| `h0_vs_h3_hard_ratelimit2_openai` | Valid: 56.7% vs 100% rate_limit×2 |
| `h0_vs_h3_hard_faults4_openai` | Cap: 40% vs 56.7% timeout×4 / retries=2 |
| `h0_vs_h3_hard_openrouter.yaml` | Wired, not run in this note |
| `h0_vs_h3_hard_faults2_openrouter.yaml` | Wired, not run in this note |

Runs live under `runs/<experiment_name>/`.
