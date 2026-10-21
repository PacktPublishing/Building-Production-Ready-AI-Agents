# Exercise 1 Solution: Identify the Failure Chain

The request contains three exact constraints: the flight must be direct, refundable, and under $700. The AI violates two constraints in its suggestion, and the application then acts without approval.

## Separate the Failures

| Failure | Unsupported assumption or violated requirement | Possible harm | Preventive control | Evidence for investigation |
| --- | --- | --- | --- | --- |
| The AI suggests a connecting, nonrefundable itinerary | The traveler required a direct, refundable flight | The traveler receives an unacceptable route or loses the fare | Have the application check every required constraint | Original request, provider fare rules, and validation result |
| The application charges the saved card | Searching did not grant permission to purchase | An unexpected financial charge occurs | Require the traveler to approve the exact offer, passengers, and maximum total | Approval record and purchase request |
| The confirmation says the request was satisfied | The purchased itinerary contradicts the request | The traveler may trust an incorrect summary and miss the problem | Build the status from checked provider results | Provider response and message shown to the traveler |

## Follow the Chain

The suggestion failure is the proposed itinerary: it does not satisfy the traveler's requirements. The application-control failure is more serious because it allows that proposal to charge a card.

The strongest control belongs immediately before purchase. At that point, the application should compare the current offer with the saved constraints and exact approval. Earlier checks still matter, but a final check protects against a changed price or offer.

## What This Shows

A correct price does not make the whole itinerary correct. Responsible evaluation checks each requirement separately, and responsible execution prevents an unchecked proposal from becoming an external action.
