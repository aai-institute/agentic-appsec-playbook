---
title: "3 · Fix a validated finding"
description: Have an agent draft the fix for the finding you validated, check that the regression test and the suite pass, and have someone who did not drive the agent review it.
---

**Goal:** Turn the confirming test from
[exercise 2](/exercises/validate-a-finding/) into a fix. An agent drafts the
change on a branch in the review VM, you check that the regression test fails
before and passes after, and a person who did not drive the agent reviews it.
Then fill the fix half of the
[validation loop record](/validation/validation-loop-template/).

Plan for one to two hours. The security-specific work is small: the test is
the adversary, and the review decides whether the change removed the flaw or
only the symptom.

**You need:** the claim and the confirming test you kept from exercise 2, and
the review VM from that exercise or a fresh one set up the same way. Without a
confirmed finding of your own, use the
[fallback target](#fallback-target-the-example-applications-attachment-download)
at the end of this page.

## Part 1: Brief a patch agent

Give the agent the claim and the failing test. The discovery transcript and
the findings export stay out: an agent that reads the tool's report patches what the report says, which is not always the flaw.

Ask for:

- the smallest change on a branch that makes the regression test pass without
  changing the test's assertion;
- dependencies installed from the lockfile only, with neither the lockfile
  nor any other test changed, except fixtures the new test needs;
- the regression test and then the whole suite run, with the first failing
  assertion reported as printed.

:::tip[Prompting the agent]

- Paste the claim and the test as you wrote them, each labelled.
- Name the files and functions on the path you traced in exercise 2.
- Say that the test is correct and must not be edited. An agent that cannot
  make it pass should say so and leave the assertion as it is.
- Ask it to leave unrelated code alone, including formatting.
- Describe the task as what it is: make a regression test pass by fixing the
  rule the code should enforce.
  :::

The expected outcome is <span class="value-chip value-chip--fixed">fixed</span>. Two other outcomes are valid too. If tracing
the path shows the code is already safe, the outcome is <span class="value-chip value-chip--no-change">no change needed</span>, with the reason. If the
finding may be real but a piece of evidence or a product decision is missing,
the outcome is <span class="value-chip value-chip--blocked">blocked</span>, with what is missing. Either is better than a
speculative patch. If the agent declines or cannot produce a passing change,
write the fix yourself and record it as drafted <span class="value-chip value-chip--plain">manual</span>.

## Part 2: Verify the fix yourself

The agent's report of its own run is not evidence
([rule 1](/triage/triage-rubric/#evidence-rules)). In the review VM, on the
agent's branch:

1. Check out the base commit, run the regression test, and confirm it fails
   on the assertion that names the rule.
2. Check out the branch, run the regression test, and confirm it passes.
3. Run the whole suite, for example `uv run --frozen pytest`, and whatever
   static analysis your project already uses.

Then check the five ways a passing patch can still be wrong. One check each:

| Failure mode | Check |
|---|---|
| Scope creep | The diff touches only the files and functions on the traced path. Anything else needs its own justification. |
| Test gaming | The test file is unchanged, and the test still asserts the rule the code must enforce. |
| Hallucinated API or dependency | The lockfile is unchanged and every new import resolves in the VM. |
| Weakened validation elsewhere | Read the diff for removed checks, loosened defaults or widened permissions anywhere, even where the test does not look. |
| Bypass | Write one more test with harmless input that reaches the same flaw another way: a sibling route, another encoding, another entry point to the same code. It must fail on the base commit and pass on the branch. If it still fails on the branch, the fix is incomplete. |

A patch that fails any of these goes back to the agent with the check named,
or becomes a manual fix. The bypass check matters most: an agent patches until
the reported input stops working, and a patch can block that input while the
flaw stays reachable through a slightly different one.

## Part 3: Review and record

Hand the branch to someone who did not drive the agent. Give them the claim,
the diff and the test results, but not the agent's transcript or its
explanation of the fix: a reviewer who reads the agent's reasoning first tends
to check the reasoning instead of the code. The reviewer rates four risks in
a word each (impact if the fix is wrong, likelihood of a regression, whether
the tests would catch one, how easily it reverts) and answers three questions
in writing:

- Does the change fix the root cause, or a symptom the test happened to
  catch?
- Did anything change beyond the finding?
- Would you have merged this without the regression test?

The result is <span class="value-chip value-chip--merged">merged</span>, <span class="value-chip value-chip--merge-ready">merge-ready</span> or
<span class="value-chip value-chip--rejected">rejected</span>, each with a reason. If nobody in your
organisation can review in time, have a model review it as in the
[optional challenge](#a-second-model-reviews-the-fix), or record that no review
took place. Either way the loop is not closed, and the record says so.

Fill sections 5 to 7 of the loop record: the outcome, who drafted the fix,
what the regression test and the suite did, what verification actually ran,
who reviewed and what they saw, their risk call, changes and result, and the minutes
for drafting and review.
Time-to-valid-fix adds those to the validation minutes from exercise 2,
against the triage minutes from the rubric as the baseline. For section 8,
two lines: where the agent helped or misled, and whether you would run this
loop in CI, under what conditions.

## Optional challenges

### A tool's own fix step

Several shortlist tools have a patch stage of their own:
[Codex Security](/tools/shortlist/#openai-codex-security) patches a saved
finding, verifies the change in a sandbox and opens a draft pull request; the
[Defending Code](/tools/shortlist/#anthropic-defending-code-reference-harness)
harness runs a patch agent against an isolated grader for C and C++;
[Mantis](/tools/shortlist/#google-mantis) has a patch stage that needs Docker.
Run one on the same finding and grade what it calls verified with the
evidence rules: did it execute anything, and what did its test assert?
Compare its diff with the agent's from Part 1. Where a tool opens a pull
request on its own, the review in Part 3 applies unchanged. The tool's
"verified" label names a process, and the merge decision stays with the reviewer.

### A second model reviews the fix

If nobody can review in time, or as a second opinion next to a person, have a
model review the fix. Use a different model from the one that wrote the patch:
it is less likely to share the first one's blind spot, for the same reason the
reviewer should not be the person who drove the agent. Give it what the
reviewer in Part 3 gets: the claim, the diff and the test results, but not the
patching agent's transcript or explanation. Ask for the four risk words, a
written answer to each of the three questions, and one test with harmless
input that still reaches the flaw on the patched branch.

A review that includes a bypass test rarely meets provider safeguards. If your
provider's model declines anyway, or you want a model from another family, use
an open-weight model in a separate VM, set up as in
[exercise 2's Part 2](/exercises/validate-a-finding/#part-2-brief-an-agent-and-check-its-test);
[Choosing a model](/tools/choosing-a-model/) lists the options. Open-weight
models find fewer bypasses, so a clean result lowers the risk without ruling a
bypass out. For parsers and memory-handling code, fuzzing the patched build is
a complementary check that needs no model.

Run the bypass test yourself as in Part 2 and grade it with the
[evidence rules](/triage/triage-rubric/#evidence-rules). A model can review but
not decide: section 6 names the model as the reviewer, and without a person's
review the result is <span class="value-chip value-chip--merge-ready">merge-ready</span> at most. Record the bypass
attempt in section 5.

## Fallback target: the example application's attachment download

If you have no confirmed finding, patch the flaw the working group validated
together. Import the example application at its `seeded` revision, as in
[Getting started](/getting-started/#import-the-repository).

**The claim:** the flaw is a missing access check: `GET
/attachments/{id}/download` in `forum/routes.py` returns the file without
checking that the requester may view the parent post. It is reachable by
anyone, guests included, because attachment numbers count up from 1. The
impact is that anyone can read attachments on private boards and hidden
posts.

**The regression test.** Save it as `tests/test_attachment_visibility.py`
and run it with `uv run --frozen pytest tests/test_attachment_visibility.py`.
On the seeded revision the first test fails on its first assertion (the guest
receives 200) and the second passes; after a correct fix both pass.

```python
from conftest import sign_in


def test_download_is_refused_without_access_to_the_post(client):
    # Attachment 1 belongs to a post on the private "Garden Circle" board.
    # A guest and a member who is not on that board must not receive the file.
    assert client.get("/attachments/1/download").status_code == 404
    sign_in(client, "bob")
    assert client.get("/attachments/1/download").status_code == 404


def test_download_is_allowed_for_a_board_member(client):
    sign_in(client, "alice")
    assert client.get("/attachments/1/download").status_code == 200
```

Brief the agent with the claim and this test, and run Parts 2 and 3 as above.
Afterwards compare your diff with the corrected code on the application's
`main` branch: a one-line restoration is the expected size, and anything
larger is worth a line in section 8.

## What you should have at the end

- A branch with the fix and the unchanged regression test, failing before
  and passing after, with the suite green.
- The five failure-mode checks, each with its result.
- A written review by someone who did not drive the agent, or by a second
  model and recorded as such, with the risk call, the result and the answer to "would you have merged without the
  test?".
- Sections 5 to 8 of the loop record, with time-to-valid-fix.
