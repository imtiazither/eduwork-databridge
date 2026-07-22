# The story behind DataBridge

It usually starts with an ordinary question.

On Monday morning, a training manager needs to know who completed cybersecurity training, passed the assessment, and received a credential. HR has the employee roster. The learning platform has completion records. Scores arrive in a spreadsheet. Credential awards come from another system.

None of those systems is necessarily wrong. They simply do not tell the same story in the same language.

Someone exports four files and starts reconciling them by hand. A missing employee ID gets filled from memory. Two accounts that look similar get merged. A completion date that predates the assignment is left alone because the report is due at noon. The spreadsheet produces an answer, but six weeks later nobody can explain every choice that went into it.

EduWork DataBridge is an attempt to make that work visible.

## The idea

The project treats a data pipeline as a chain of evidence. It keeps the original source bytes, records the rules used to translate them, explains why a row failed, separates uncertain identity matches from safe ones, and attaches lineage to the published result.

That sounds procedural because it is. The hard part of cross-system reporting is rarely moving bytes from one place to another. The hard part is deciding what the bytes mean, what to do when they disagree, and who is allowed to make that call.

DataBridge gives those decisions a home.

## What it contributes

First, it puts evidence before cleanup. A raw snapshot is immutable and checksummed, so the starting point remains available after names, dates, and codes have been normalized.

Second, it gives bad records an explicit path. A validation failure is not silently deleted. It carries a reason code, a severity, and a review history. That makes a correction or waiver inspectable later.

Third, it is conservative about identity. Trusted, organization-scoped identifiers come first. Conflicts block a match. Probabilistic candidates stay separate from approved links, and the gray zone belongs to a human reviewer.

Finally, it connects governance to the output itself. A mart or export has a checksum, dictionary, lineage trail, permission boundary, and retention metadata. The report is not separated from the evidence needed to understand it.

## Why the public fixture matters

The public repository uses a fictional organization and deterministic synthetic records. The small case file contains 120 people, 366 learning events, 120 assessment results, 25 credential awards, and 43 deliberately planted problem occurrences.

Those problems are specific: nine missing employee IDs, seven invalid LMS statuses, five completions before assignment, six duplicate LMS accounts, and several other identity, timing, and export cases. An evaluator can inspect the same awkward records every time the demo runs.

This is useful evidence of behavior. It is not evidence of customer adoption, production readiness, savings, or improved learning outcomes.

## What a real pilot should discover

A bounded pilot should begin with one recurring report and one named data owner. The useful questions are practical:

- How long does the current reconciliation take?
- Which source disagreements occur most often?
- How many records need human review?
- Can a reviewer trace a published field without calling the pipeline author?
- Does the process become easier to repeat after the first cycle?

The pilot should compare those findings with the current manual process. If DataBridge cannot reduce ambiguity or make the work easier to explain, the organization should know that before expanding the scope.

## The line the project will not cross

DataBridge prepares evidence. It does not decide employment, eligibility, admission, discipline, disability, or access to services. It does not turn a probability into a fact, and it does not make a synthetic benchmark sound like a business result.

That boundary is part of the contribution. In workforce and education data, restraint is a feature.

