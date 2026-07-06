Feature: Capability C — Pin the brand fetch to a public host

  Scenario: Declared brand colors are authoritative and the network is never touched
    Given an input pack that declares brand_colors
    When brand capture runs
    Then the declared colors are used with source pack and no URL is fetched

  Scenario: A brand URL is fetched only over http(s), pinned to a validated public IP
    Given a pack with a brand_url and no declared colors
    When brand capture fetches it
    Then a non-http scheme such as file is refused
    And the fetch connects to the validated pinned IP

  Scenario: A URL resolving to a non-public address is refused before any bytes are read
    Given a brand_url that resolves to a private, loopback, CGNAT, or IPv4-embedded IPv6 address
    When the address is validated
    Then it is refused, and a host resolving to a mix of public and private addresses is refused whole

  Scenario: A redirect is re-validated at every hop
    Given a brand_url whose fetch follows a redirect
    When the fetch follows the Location header
    Then each hop is re-resolved and re-pinned, and too many hops is refused
