# Acceptance specification. Automated evidence: tests/integration/broker-flow.mjs
@US04 @US12 @TS03
Feature: Read the dashboard of an authorized unit

  Scenario: Authorized or healthy request
    Given a signed-in user with a current plan can access a unit without recent readings
    When the client requests GET /api/v1/analytics/dashboard?unitId=<authorized-unit>
    Then the response status is 200
    And available is false in the response

  Scenario: Boundary or access control
    Given the review environment is available
    When a signed-in account with a current plan requests a unit outside its access
    Then the response status is 404
    And the other unit's dashboard is not returned
