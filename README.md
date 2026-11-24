# Support Ticket Queue

An MIT-licensed public demo for creating sample support tickets and viewing the 50 newest open tickets. Python serves the browser interface and JSON API. SQLite persists tickets and daily browser counts.

## Day 1 on Windows
Install Python 3.11+ and open PowerShell in this folder. Run each line:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn web:app --port 8000
```

Open http://127.0.0.1:8000 and create a sample ticket. Refresh, then open a private browser window. The daily count should increase once for the new window. Stop the server with Ctrl+C and restart from the same folder. Your ticket and counts should persist.

## Publish and deploy
Create a public GitHub repository and upload the contents of this folder (keep render.yaml at the repository root). Include LICENSE. Exclude local databases, .venv and credentials. In Render choose New > Blueprint, connect the repository, review the Starter instance and 1 GB disk and deploy. Open the assigned HTTPS service URL and repeat the acceptance check. The disk preserves data across redeploys. Use only sample ticket text because the queue is public.

## Monitor
The homepage displays today's unique browsers. /usage returns seven Pacific calendar days. A random, first-party cookie deduplicates repeated homepage loads until local midnight. API-only clients and /health probes do not count. Private windows, cookie clearing, and bots affect estimates. Record the URL, date, baseline, and final count; record your two test browsers separately. For a complete day, measure midnight to midnight Pacific.

## Original API-only exercise

From this directory, run `python service.py`. In a second terminal, create a ticket and read the queue.

```sh
curl -X POST http://127.0.0.1:8000/tickets -H 'Content-Type: application/json' -d '{"title":"Receipt missing"}'
curl 'http://127.0.0.1:8000/tickets?status=open'
```

On Windows PowerShell, use `Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/tickets -ContentType application/json -Body '{"title":"Receipt missing"}'` followed by `Invoke-RestMethod http://127.0.0.1:8000/tickets`. Restart the server and confirm the record survives.

## Reproduce the SQL experiment
Run `python benchmark.py`. It creates a fresh in-memory database with 100,000 synthetic tickets (1% open), warms the query, times 201 reads, adds an index on (status, id DESC), then repeats. Both conditions must return the same 50 records in the same order. One local run produced medians of 0.151 ms and 0.028 ms. These timings cover SQL execution and fetching rows, excluding HTTP and disk I/O. The query plan changes from scanning tickets to searching the index. An index also consumes space and adds write work.

## Seven daily sessions
1. Run both endpoints, restart the service, and trace a request through the handler, transaction, and response. Change the title limit and test both sides of the boundary.
2. Implement PATCH /tickets/{id} to close a ticket. Decide what a repeated close returns and test that behavior.
3. Add integration tests for creation, empty titles, missing IDs, and closing. Run them against a disposable database.
4. Run the index experiment with 1%, 10%, and 50% open tickets. Record machine details and medians. Explain why the gain varies.
5. Add cursor pagination using the last ticket ID. Insert another ticket between two requests and check for duplicates.
6. Add continuous integration for tests and document one failing case you discovered and repaired.
7. Record a two-minute walkthrough. Demonstrate one request, the query plan, your measured result, and a limitation. Publish your reviewed changes under the included MIT license when ready.

## Interview practice
Explain who reads the queue, why the query sorts by ID, how you checked equivalence, and when the index might cost more than it saves. Describe changes you personally implemented. For an employment question, use an actual workplace incident and its own measurements.
