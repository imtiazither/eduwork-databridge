# Can we trust the training report?

## A field guide to EduWork DataBridge

A training report may begin with four exports: an employee roster, learning events, assessment results, and credential awards. The final spreadsheet can look tidy even when IDs are missing, dates disagree, or two accounts may belong to the same person.

EduWork DataBridge is a pre-production reference implementation for keeping those decisions visible. It preserves source evidence, applies versioned mappings and validation rules, sends uncertain identity matches to review, and carries lineage into governed outputs.

Public examples use deterministic synthetic data. They do not describe a customer deployment or measured business outcome.

## The Monday-morning question

> Who completed cybersecurity training, passed the assessment, and received the credential?

HR knows the employee. The LMS knows the assignment and completion. The assessment system knows the score. The credential system knows the award. Someone still has to decide how those records fit together.

The project gives that reasoning a place to live. A missing ID becomes a named exception. A date conflict becomes a review item. A likely match carries evidence instead of becoming a silent merge.

## The five-stop evidence path

1. **Collect:** read approved source data and preserve an immutable, checksummed snapshot.
2. **Check:** profile structure and run explicit validation rules.
3. **Connect:** link identities with trusted IDs first and route gray-zone cases to review.
4. **Publish:** create documented, permission-aware marts and masked exports.
5. **Trace:** follow a report field back through the output, rule, and raw source.

## The public case file

The small fixture contains 120 fictional HRIS people, 366 learning events, 120 assessment results, and 25 credential awards. It includes 43 deliberately planted problem occurrences across nine issue types.

Examples include nine missing employee IDs, seven invalid completion statuses, five completions before assignment, six duplicate LMS accounts, and one credential that predates its qualifying assessment.

## The contribution

DataBridge makes cross-system data work inspectable. It treats the pipeline as a chain of evidence, gives bad records an explicit review path, and keeps uncertain identity decisions reversible. Governance travels with the output through checksums, dictionaries, lineage, permissions, audit events, and retention metadata.

The project also models restraint. It does not turn a probability into a fact or use synthetic results as a stand-in for customer outcomes.

## What still needs a pilot

A real pilot must supply partner-specific ownership, mappings, identity rules, infrastructure validation, and measured process findings. A useful first pilot would compare one recurring report with its current manual workflow: preparation time, exception rate, reviewer burden, and the ability to trace a published field without calling the pipeline author.

The software prepares evidence. People remain responsible for consequential decisions.

