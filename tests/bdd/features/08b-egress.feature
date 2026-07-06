Feature: Capability B — One guarded egress throat

  Scenario: Client content is redacted and residual PII masked on every field
    Given a pipeline built with a redacting egress policy and a capturing generator
    When a request that names the client and contains an email passes the shared guard
    Then the client terms are replaced by the alias and the email is masked across all fields
    And the grounding ids are left intact so they still resolve at the audit

  Scenario: Unconfigured redaction refuses to egress
    Given an egress policy with an empty redact-term list and no cleartext allowance
    When the policy is constructed
    Then it raises and blocks before any pipeline can be built

  Scenario: The operator previews each distinct payload once, and a rejection blocks
    Given a pipeline built with an operator-preview egress policy
    When the same client content is sent twice with different instructions then new content is sent
    Then the operator is asked once for the repeat and again for the new content
    And a rejected preview raises an egress block
    And a missing preview also blocks the egress

  Scenario: An egress reject is a human block, not a crash
    Given a pipeline built with an egress policy whose operator rejects the preview
    When the runner walks the pipeline and the first generating stage hits the guard
    Then the run status is blocked and nothing is sent to the model
