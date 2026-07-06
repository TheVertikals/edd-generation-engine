Feature: Capability D — A mockup carries only grounded, on-brand content, and synthesize seals the bundle

  Scenario: Every citation in the mockup resolves to a grounded claim
    Given a set of grounded claim ids
    When the purity check runs against a model-authored prototype
    Then every cited id must resolve to a grounded claim
    And visible content with no citations blocks unless tagged all-sample
    And a stated total must reconcile with the sum of its parts

  Scenario: The mockup must actually use the brand, judged on the model's own output
    Given a captured brand primary color and a generator that ignores the brand
    When the mockup stage runs
    Then a mockup that ignored the brand is regenerated
    And if it still fails purity or brand after the regeneration budget the stage raises a purity block

  Scenario: One adversarial sweep runs on the accepted candidate
    Given a prototype that passed the deterministic purity checks
    When a verifier runs one semantic sweep and flags an uncited claim
    Then the finding blocks the prototype as a policy block, not a crash

  Scenario: Synthesize fills the remaining docs and seals a resolvable manifest
    Given a graded, audited bundle
    When synthesize runs
    Then it fills the remaining docs with grounded copy and fails loudly if any is empty
    And it writes a manifest listing only artifacts and prototype surfaces that exist on disk
