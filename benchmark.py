"""Compare one query before and after adding its index on synthetic data."""
import sqlite3
from statistics import median
from time import perf_counter_ns

from service import INDEX, QUEUE, initialize


def measure(db):
    def query():
        return db.execute(QUEUE, ("open",)).fetchall()
    expected = query()
    print(db.execute("EXPLAIN QUERY PLAN " + QUEUE, ("open",)).fetchall())
    samples = []
    for _ in range(201):
        start = perf_counter_ns()
        result = query()
        samples.append((perf_counter_ns() - start) / 1_000_000)
        assert result == expected
    return expected, median(samples)


if __name__ == "__main__":
    db = sqlite3.connect(":memory:")
    initialize(db)
    db.execute("DROP INDEX tickets_status_id")
    db.executemany("INSERT INTO tickets VALUES (?, ?, ?)",
                   ((i, f"Ticket {i}", "open" if i % 100 == 0 else "closed")
                    for i in range(1, 100_001)))
    before, baseline = measure(db)
    db.execute(INDEX)
    after, indexed = measure(db)
    assert before == after and len(after) == 50
    print(f"Median SQL read, 201 warm runs per condition: {baseline:.3f} ms before; {indexed:.3f} ms after.")
