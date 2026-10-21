# Exercise 3 Solution: Protect Data and Explain the Request

The application needs route, dates, and passenger count to compare public fares. A passport number is not needed at this stage.

| Question | Example answer |
| --- | --- |
| Which requested data is unnecessary during search? | The passport number. |
| What should the traveler be told before any required data is collected? | The purpose, recipient, retention period, and whether the data is required or optional. The application should request passport details later only if a selected airline requires them for booking and there is an applicable legal basis. |
| What record can support an investigation without storing secrets? | Record that an unnecessary sensitive-data request was blocked, along with the time, search stage, rule applied, and outcome. Do not store the passport number or the full conversation. |

The application should block or remove the passport request, continue the search without that data, and explain that identity details may be requested later if they become necessary for booking.

## What This Shows

Privacy and transparency reinforce each other. Data minimization prevents unnecessary collection, while a clear explanation helps the traveler understand what is required and what has not been shared.
