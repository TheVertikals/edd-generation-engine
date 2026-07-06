Feature: Capability A — Writes are atomic; reads tolerate corruption

  Scenario: An interrupted write never leaves a half-written file
    Given a resumable checkpoint store with committed state
    When a checkpoint write is interrupted after the temp file exists but before the rename
    Then the store still holds either the old state or none — never a partial
