Feature: Capability E — Walk the stages under human gates, resumably

  Scenario: Intake stamps the beacon that joins the deliverable back to its engagement
    Given an input pack whose manifest carries an engagement beacon id
    When intake adapts the pack into the bundle
    Then the beacon id is persisted for downstream provenance
    And an empty beacon id fails loudly

  Scenario: A revise verdict regenerates the stage; a reject fails closed
    Given a pipeline whose first stage fires the gate
    When the operator returns a revise verdict then an approve
    Then the run completes after the revised stage re-runs
    And a reject or any unrecognized verdict stops the run as rejected

  Scenario: An interrupted run resumes at the last incomplete stage
    Given a run that completed intake and research then stopped
    When it is re-run
    Then the checkpointed stages are skipped and it resumes at the next incomplete stage

  Scenario: A best-effort stage that crashes stops the run without corrupting the trunk
    Given a pipeline where a stage raises an unexpected error and another raises a policy block
    When the runner handles each
    Then an unexpected error stops the run with status error and a policy block surfaces as blocked
    And no later stage runs after the block
