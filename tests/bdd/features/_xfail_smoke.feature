Feature: xfail tag wiring smoke test

  # Deliberately named outside the 08* namespace so the cross-repo drift gate (which globs
  # 08*.feature) ignores it. Proves the conftest hook turns @xfail into a STRICT expected-failure:
  # the step below always fails, so the scenario must be collected as an XFAIL. Without the hook it
  # would be a hard FAIL and turn the suite red; under strict, an xpass would also fail the suite.
  @xfail
  Scenario: a deliberately failing scenario is collected as an expected failure
    Given a step that always fails
