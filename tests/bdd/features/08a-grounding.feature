Feature: Capability A — Ground every claim or block

  Scenario: A stated pain must cite a fact that resolves to the corpus
    Given a customer intake adapted into the shared corpus as intake facts
    When research proposes a stated pain that cites a corpus id
    Then the pain is a fact tier and its cited id resolves to the corpus
    And a pain that cites an id not in the corpus is regenerated and then blocked by the audit

  Scenario: A latent opinion must trace to a grounded fact, with no cycles
    Given a latent pain marked confidence inferred
    When the grounding audit evaluates it
    Then an opinion whose basis resolves transitively to a grounded fact passes
    And an opinion whose basis is missing, cyclic, or itself ungrounded fails the audit

  Scenario: The audit gate blocks ungrounded content before any deliverable is built
    Given a solution whose basis cites a GHOST id that is not in the corpus
    When the pipeline runs the blocking audit between solution and mockup
    Then the run status is blocked at the audit stage
    And no prototype mockup is ever written

  Scenario: Empty or speculative output cannot be finalized
    Given an audited claim set that is empty or carries a speculative claim
    When the audit runs with require-nonempty and block-speculative on
    Then the empty set blocks and the speculative claim blocks by default
    And only a content-bound waiver with a named approver downgrades that one claim
    And any malformed or unbound waiver file applies zero waivers
