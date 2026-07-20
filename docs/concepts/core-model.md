# Canonical Model

The core is intentionally industry-neutral.

- Organization and OrganizationUnit
- Person, ExternalIdentity, and RoleAssignment
- LearningProgram and LearningOffering
- Participation and ExperienceEvent
- AssessmentDefinition, AssessmentAttempt, and AssessmentResult
- CompetencyDefinition and CompetencyAlignment
- CredentialDefinition and CredentialAward

Every canonical entity uses an internal UUID. Source identifiers remain separate and scoped by organization and source. Email is not treated as a permanent global identity. Effective dates preserve change history.

Optional adapters translate xAPI, OneRoster, CASE, CEDS-informed, CTDL, HRIS, LMS, CRM, assessment, and credential concepts into the core without forcing academic terminology on enterprise users.
