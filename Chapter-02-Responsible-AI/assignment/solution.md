# Assignment Solution: Prepare the Travel System for Its Next Booking

This reference follows one booking from search to purchase. It keeps the chapter's boundary visible: the AI suggests, the application checks and acts, and the traveler decides consequential choices.

## One Booking Journey

The traveler wants a refundable London-to-Nairobi itinerary under $900, departing on 2026-09-14. The table shows how responsibility changes as the journey moves closer to a purchase.

| Stage | AI suggests | Application checks or acts | Traveler decides | Data needed | Record kept |
| --- | --- | --- | --- | --- | --- |
| Search | Possible itineraries and trade-offs | Searches approved services; checks dates, airports, chronology, and minimum transfer times | Confirms route, date, budget, and required preferences | Route, date, passenger count, chosen preferences | Search time, requirements, offer references, and check outcomes |
| Review | A comparison of checked offers | Rechecks price, refund rules, baggage, and accessibility details; displays booking status | Selects or rejects an exact offer | Legal passenger name only when needed to prepare booking | Offer shown, verified terms, and selection |
| Purchase | A plain-language summary of the proposed action | Confirms identity, authority, current total, and exact approval; submits only the approved purchase | Approves or rejects the exact itinerary, passengers, currency, total, and terms | Required booking details and protected payment reference | Approval, check results, provider response, and outcome without passport or payment secrets |

Notice that the AI does not verify facts or purchase the trip. If a price or term changes, the application stops and the traveler makes a new decision.

## Three Risks

Each risk has a different primary safeguard. Keeping them separate prevents a good factual check from being mistaken for purchase authority or privacy protection.

| Type | Risk and possible harm | Safeguard | How noticed | Owner and response |
| --- | --- | --- | --- | --- |
| Factual | An itinerary departs Istanbul before the arriving flight lands, causing a missed connection | Application checks chronology and minimum transfer time | Itinerary check fails | Booking team removes the offer and investigates its source |
| Authority | The application purchases without approval for the exact itinerary and total, causing an unexpected charge | Require exact approval immediately before purchase | Purchase request has no matching approval record | Payments team blocks the purchase or begins reversal and investigation |
| Privacy | Passport data is requested during search, creating unnecessary disclosure risk | Collect data only for a justified purpose and applicable legal basis at the stage where it is needed | Sensitive-data request occurs during search | Privacy team blocks collection and reviews the request path |

The owner maintains the safeguard and responds when it fails. Ownership does not replace the traveler's decision; it makes the organization accountable for the application around that decision.

## Three Evaluation Cases

These cases test the complete journey, not only whether the AI's wording sounds reasonable.

| Situation | Expected AI suggestion | Expected application behavior | Expected traveler decision | Evidence needed |
| --- | --- | --- | --- | --- |
| Factual: onward flight departs before arrival | Does not present the itinerary as viable | Rejects it before review and explains that the schedule failed | No purchase decision is requested | Offer reference, local dates and offsets, transfer rule, and failed check |
| Authority: purchase is requested without exact approval | May summarize the offer but does not claim it is authorized | Blocks purchase and displays the exact itinerary, terms, and total for review | Approves or rejects the offer | Offer shown, approval status, block decision, and message displayed |
| Privacy: passport is requested during search | Explains that passport data is unnecessary for comparison | Removes the request and continues search without the number | Provides no passport data during search | Time, stage, rule applied, and blocked-request outcome without the passport number |

A strong submission makes the expected stopping behavior explicit. When a fact fails, approval is missing, or data has no justified purpose, the application does not continue toward purchase.
