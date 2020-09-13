#!/usr/bin/env python3
"""
checkpoint.py
Simulates the drift and throughput of idempotent and non-idempotent workers
at various rates of checkpointing and failures.
"""

from collections import defaultdict, namedtuple
from random import random
import sqlite3
import matplotlib.pyplot as plt

TICKS = 100_000

Result = namedtuple(
    "Result",
    ("label", "name", "checkpoint_steps", "err_rate", "throughput", "drift"),
)


def main():
    types = (idempotent_task, non_idempotent_task)
    checkpoint_steps = (1, 3, 5, 8, 11)
    err_rates = (0.0005, 0.001, 0.005, 0.01, 0.02)
    data = [
        model(*args)
        for args in [
            (typ, steps, rate)
            for typ in types
            for rate in err_rates
            for steps in checkpoint_steps
        ]
    ]
    plot(data)


def idempotent_task(conn, checkpoint_steps, err_rate, tick, event_id):
    """
    Idempotent events can be safely retried. By using the event_id we
    ensure that we never increment a counter if we've seen the event
    before. Additionally, we update both counters in a single atomic
    transaction so that we can't have partial updates.

    Note that atomicity and idempotency aren't the same thing! But
    you can't have idempotency without atomicity if you make multiple
    updates.
    """
    try:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO counterA VALUES (?)", (event_id,))
        maybe_error(err_rate)
        cur.execute("INSERT OR REPLACE INTO counterB VALUES (?)", (event_id,))
        maybe_checkpoint(conn, tick, checkpoint_steps)
        event_id += 1
    except Exception:
        conn.rollback()
    return event_id


def non_idempotent_task(conn, checkpoint_steps, err_rate, tick, event_id):
    """
    Non-idempotent events cannot be safely retried. We're stil using
    the event_id so that we never increment a counter if we've seen the
    event before. But because this isn't an atomic transaction, each
    table can see a different set of events!
    """
    try:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO counterA VALUES (?)", (event_id,))
        maybe_checkpoint(conn, tick, checkpoint_steps)
        maybe_error(err_rate)
        cur.execute("INSERT OR REPLACE INTO counterB VALUES (?)", (event_id,))
        maybe_checkpoint(conn, tick, checkpoint_steps)
        event_id += 1
    except Exception:
        conn.rollback()
    return event_id


def model(process_event_fn, checkpoint_steps, err_rate):
    """ simulates one set of variables for TICKS events """
    with setup() as conn:
        event_id = 0
        for tick in range(TICKS):
            event_id = process_event_fn(
                conn, checkpoint_steps, err_rate, tick, event_id
            )
        counter_a, counter_b = get_results(conn)
        drift = abs(counter_a - counter_b)
        throughput = counter_a
        return Result(
            "{}, {}-step checkpoints".format(
                process_event_fn.__name__, checkpoint_steps
            ),
            process_event_fn.__name__,
            checkpoint_steps,
            err_rate,
            throughput,
            drift,
        )


def setup():
    """ our database is a just a pair of counters we'll increment """
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE counterA (id INTEGER)")
    cur.execute("CREATE TABLE counterB (id INTEGER)")
    conn.commit()
    return conn


def get_results(conn):
    """ get the value of our counters """
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM counterA;")
    counter_a = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM counterB;")
    counter_b = cur.fetchone()[0]
    return counter_a, counter_b


def maybe_checkpoint(conn, tick, checkpoint_steps):
    """ commit every checkpoint_steps events we process """
    if tick % checkpoint_steps == 0:
        conn.commit()


def maybe_error(err_rate):
    """ randomly fail """
    if random() <= err_rate:
        raise Exception()


def plot(raw_data):
    """ make a pretty diagram"""

    event_data = defaultdict(list)
    for row in raw_data:
        event_data[row.label].append(row)

    def figure(title, attr, label):
        for _, events in event_data.items():
            events = sorted(events, key=lambda e: e.err_rate)
            xs = ["{:0.2f}%".format(100 * event.err_rate) for event in events]
            ys = [getattr(event, attr) for event in events]
            plt.plot(
                xs,
                ys,
                label=events[0].label,
                linestyle="dashed"
                if events[0].name == "idempotent_task"
                else "solid",
                linewidth=4,
                marker="o",
                markersize=12,
            )
        plt.xlabel("failure rate %", fontsize="x-large")
        plt.ylabel(label, fontsize="x-large")
        plt.legend(fontsize="x-large")
        plt.title(title, fontsize="x-large")

    plt.figure(1)
    plt.subplot(211)
    figure("failure rate vs throughput", "throughput", "throughput")
    plt.subplot(212)
    figure("failure rate vs error drift", "drift", "error drift")
    plt.show()


if __name__ == "__main__":
    main()
