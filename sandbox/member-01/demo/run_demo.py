"""InflMem sandbox demo: minimal end-to-end pipeline.

Synthetic 20 users x 3 sessions -> MockMemory -> naive/provenance writers
-> CMR / CMR_cond / Coverage / IDR / SFB.

This is a pipeline sanity check, not a scientific experiment.
No LLM API, no external data.
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timedelta, timezone

SEED = 0
N_USERS = 20
N_SESSIONS = 3
DEMO_DATE = "2026-11-12"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUN_ROOT = os.path.join(BASE_DIR, "runs")

COLORS = ("blue", "black")


class MockMemory:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def add(self, record: dict) -> None:
        self.records.append(record)

    def search(self, user_id: str, query: str = "color", top_k: int = 5) -> list[dict]:
        return [r for r in self.records if r["user_id"] == user_id][:top_k]


def make_users() -> list[dict]:
    users = []
    for i in range(N_USERS):
        color = "blue" if i % 2 == 0 else "black"
        users.append(
            {
                "user_id": f"u{i:03d}",
                "true_color": color,
                "initial_preference": color,
            }
        )
    return users


def simulate(users: list[dict], rng: random.Random) -> tuple[list[dict], dict]:
    events: list[dict] = []
    labels: dict[str, dict] = {}
    start = datetime(2026, 11, 12, 10, 0, tzinfo=timezone.utc)

    for user in users:
        true_color = user["true_color"]
        for session_idx in range(N_SESSIONS):
            before = true_color
            rec_color = "blue" if rng.random() < 0.7 else "black"
            accept_prob = 0.9 if rec_color == true_color else 0.75
            accept = rng.random() < accept_prob

            label = None
            if accept:
                if rec_color == true_color:
                    label = "stable"
                elif rng.random() < 0.15:
                    label = "internalization"
                    true_color = rec_color
                else:
                    label = "compliance"

            event_id = f"e{len(events):04d}"
            event = {
                "event_id": event_id,
                "user_id": user["user_id"],
                "session_id": f"{user['user_id']}_s{session_idx}",
                "turn": 0,
                "timestamp": (start + timedelta(minutes=len(events))).isoformat().replace("+00:00", "Z"),
                "context": {
                    "task": "headphone_purchase",
                    "domain": "electronics",
                    "budget": 1000,
                    "scenario_id": "sandbox_demo",
                    "prior_preference": user["initial_preference"],
                },
                "agent_action": {
                    "type": "recommend",
                    "item_id": f"i_{rec_color}",
                    "attributes": {"color": rec_color},
                    "text": f"这款 {rec_color} 耳机今天有货。",
                    "candidate_set": [
                        {
                            "item_id": f"i_{rec_color}",
                            "attributes": {"color": rec_color},
                            "rank": 1,
                        }
                    ],
                    "rank": 1,
                },
                "user_response": {
                    "type": "accept" if accept else "reject",
                    "item_id": f"i_{rec_color}" if accept else None,
                    "utterance": "行，就这个。" if accept else "我再看看。",
                    "rating": None,
                },
                "exposure": {
                    "attribute": "color",
                    "value": rec_color,
                    "propensity": 0.7,
                    "source": "recommendation",
                    "position": 1,
                },
            }
            events.append(event)
            labels[event_id] = {
                "label": label,
                "true_color_before": before,
                "true_color_after": true_color,
            }

    return events, labels


def make_record(event: dict, memory_type: str, evidence_type: str, confidence: float,
                influence_prob: float, text: str) -> dict:
    now = event["timestamp"]
    return {
        "memory_id": f"m_{event['event_id']}",
        "user_id": event["user_id"],
        "session_id": event["session_id"],
        "attribute": "color",
        "value": event["agent_action"]["attributes"]["color"],
        "memory_type": memory_type,
        "evidence_type": evidence_type,
        "source_event_ids": [event["event_id"]],
        "influence_prob": influence_prob,
        "confidence": confidence,
        "validity": {"start": DEMO_DATE, "end": None, "context": "headphone_purchase"},
        "counterevidence": [],
        "status": "active",
        "supersedes": [],
        "text": text,
        "created_at": now,
        "updated_at": now,
    }


def write_naive(event: dict) -> dict | None:
    if event["user_response"]["type"] != "accept":
        return None
    value = event["agent_action"]["attributes"]["color"]
    return make_record(
        event,
        memory_type="durable",
        evidence_type="agent_suggested_accepted",
        confidence=0.8,
        influence_prob=0.0,
        text=f"User prefers {value}.",
    )


def write_provenance(event: dict) -> dict | None:
    if event["user_response"]["type"] != "accept":
        return None
    value = event["agent_action"]["attributes"]["color"]
    prior = event["context"]["prior_preference"]
    if event["exposure"]["source"] == "recommendation":
        if value != prior:
            return make_record(
                event,
                memory_type="hedged",
                evidence_type="agent_suggested_accepted",
                confidence=0.3,
                influence_prob=0.7,
                text=(
                    f"User accepted {value} after agent recommendation; "
                    f"prior preference {prior}; may be compliance."
                ),
            )
        return make_record(
            event,
            memory_type="durable",
            evidence_type="agent_suggested_accepted",
            confidence=0.7,
            influence_prob=0.2,
            text=f"User accepted {value}; consistent with prior preference {prior}.",
        )
    return make_record(
        event,
        memory_type="durable",
        evidence_type="independent_choice",
        confidence=0.7,
        influence_prob=0.1,
        text=f"User prefers {value}.",
    )


def solve3(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
    def det3(m: list[list[float]]) -> float:
        return (
            m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
        )

    det = det3(matrix)
    if abs(det) < 1e-12:
        return None
    out = []
    for i in range(3):
        m = [row[:] for row in matrix]
        for r in range(3):
            m[r][i] = vector[r]
        out.append(det3(m) / det)
    return out


def sfb_beta(observations: list[tuple[float, float, float]]) -> float | None:
    """OLS: u_hat = a + b * exposure + c * u_true; return b."""
    xtx = [[0.0] * 3 for _ in range(3)]
    xty = [0.0] * 3
    for u_hat, exposure, u_true in observations:
        x = [1.0, exposure, u_true]
        for i in range(3):
            xty[i] += x[i] * u_hat
            for j in range(3):
                xtx[i][j] += x[i] * x[j]
    beta = solve3(xtx, xty)
    return None if beta is None else beta[1]


def safe_div(num: int, den: int) -> float | None:
    return num / den if den else None


def evaluate(events: list[dict], labels: dict, records_by_event: dict[str, dict]) -> dict:
    compliance = [e for e in events if labels[e["event_id"]]["label"] == "compliance"]
    internalization = [e for e in events if labels[e["event_id"]]["label"] == "internalization"]
    accepts = [e for e in events if e["user_response"]["type"] == "accept"]

    def durable(e: dict) -> bool:
        r = records_by_event.get(e["event_id"])
        return bool(r and r["memory_type"] == "durable")

    def written(e: dict) -> bool:
        return e["event_id"] in records_by_event

    cmr_num = sum(1 for e in compliance if durable(e))
    cmr_cond_den = sum(1 for e in compliance if written(e))
    idr_num = sum(1 for e in internalization if durable(e))

    metrics = {
        "cmr": {"value": safe_div(cmr_num, len(compliance)),
                "numerator": cmr_num, "denominator": len(compliance)},
        "cmr_cond": {"value": safe_div(cmr_num, cmr_cond_den),
                     "numerator": cmr_num, "denominator": cmr_cond_den},
        "coverage": {"value": safe_div(sum(1 for e in accepts if written(e)), len(accepts)),
                     "numerator": sum(1 for e in accepts if written(e)),
                     "denominator": len(accepts)},
        "idr": {"value": safe_div(idr_num, len(internalization)),
                "numerator": idr_num, "denominator": len(internalization)},
    }
    return metrics


def run_writer(name: str, events: list[dict], labels: dict, writer) -> dict:
    memory = MockMemory()
    records_by_event: dict[str, dict] = {}
    current: dict[str, dict] = {}
    observations: list[tuple[float, float, float]] = []

    for event in events:
        record = writer(event)
        if record is not None:
            memory.add(record)
            records_by_event[event["event_id"]] = record
            current[event["user_id"]] = record

        current_record = current.get(event["user_id"])
        if current_record is None:
            u_hat = 0.0
        elif current_record["memory_type"] == "durable":
            u_hat = 1.0
        elif current_record["memory_type"] == "hedged":
            u_hat = 0.5
        else:
            u_hat = 0.0
        exposure = 1.0 if event["exposure"]["value"] == "blue" else 0.0
        u_true = 1.0 if labels[event["event_id"]]["true_color_before"] == "blue" else 0.0
        observations.append((u_hat, exposure, u_true))

    metrics = evaluate(events, labels, records_by_event)
    metrics["sfb"] = {"beta": sfb_beta(observations), "n": len(observations)}

    run_id = f"20261112_{name}_mock_demo_seed{SEED}"
    run_dir = os.path.join(RUN_ROOT, run_id)
    os.makedirs(run_dir, exist_ok=True)

    with open(os.path.join(run_dir, "events.jsonl"), "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    with open(os.path.join(run_dir, "memories.jsonl"), "w", encoding="utf-8") as f:
        for record in memory.records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    payload = {
        "run_id": run_id,
        "writer": name,
        "n_users": N_USERS,
        "n_sessions": N_SESSIONS,
        "n_events": len(events),
        "metrics": metrics,
        "notes": "sandbox demo; synthetic data; no LLM; pipeline sanity check, not a scientific result",
    }
    with open(os.path.join(run_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "seed": SEED,
                "users": N_USERS,
                "sessions": N_SESSIONS,
                "writer": name,
                "memory": "MockMemory",
                "date": DEMO_DATE,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    payload["run_dir"] = run_dir
    return payload


def fmt(value) -> str:
    if value is None:
        return "N/A"
    return f"{value:.3f}"


def main() -> None:
    rng = random.Random(SEED)
    users = make_users()
    events, labels = simulate(users, rng)

    results = [
        run_writer("naive", events, labels, write_naive),
        run_writer("provenance", events, labels, write_provenance),
    ]

    print("=== InflMem sandbox demo ===")
    print(f"users={N_USERS} sessions={N_SESSIONS} events={len(events)} seed={SEED}")
    print(f"{'metric':<12}{'naive':>10}{'provenance':>14}")
    for key in ("cmr", "cmr_cond", "coverage", "idr"):
        print(f"{key:<12}{fmt(results[0]['metrics'][key]['value']):>10}"
              f"{fmt(results[1]['metrics'][key]['value']):>14}")
    print(f"{'sfb_beta':<12}{fmt(results[0]['metrics']['sfb']['beta']):>10}"
          f"{fmt(results[1]['metrics']['sfb']['beta']):>14}")
    print()
    compliance_ids = [eid for eid, info in labels.items() if info["label"] == "compliance"]
    if compliance_ids:
        example_id = compliance_ids[0]
        print(f"example compliance event: {example_id}")
        for result in results:
            path = os.path.join(result["run_dir"], "memories.jsonl")
            with open(path, encoding="utf-8") as f:
                for line in f:
                    record = json.loads(line)
                    if example_id in record["source_event_ids"]:
                        print(f"- {result['writer']}: {record['memory_type']} | {record['text']}")
                        break

    print()
    print("note: provenance is intentionally conservative in this rule-based demo; "
          "it lowers CMR/SFB but also misses internalization (IDR=0).")
    for result in results:
        print(f"- {result['writer']}: {result['run_dir']}")

    summary_path = os.path.join(BASE_DIR, "demo_summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# InflMem sandbox demo summary\n\n")
        f.write("> Pipeline sanity check only; synthetic data, no LLM, not a scientific result.\n\n")
        f.write(f"- users: {N_USERS}\n- sessions: {N_SESSIONS}\n- events: {len(events)}\n- seed: {SEED}\n\n")
        f.write("| metric | naive | provenance |\n|---|---:|---:|\n")
        for key in ("cmr", "cmr_cond", "coverage", "idr"):
            f.write(f"| {key} | {fmt(results[0]['metrics'][key]['value'])} | "
                    f"{fmt(results[1]['metrics'][key]['value'])} |\n")
        f.write(f"| sfb_beta | {fmt(results[0]['metrics']['sfb']['beta'])} | "
                f"{fmt(results[1]['metrics']['sfb']['beta'])} |\n")
        f.write("\n## What this shows\n\n")
        f.write("- naive writer overclaims: all compliance events become durable preference; CMR = 1.0.\n")
        f.write("- provenance writer hedges recommendation-accepted mismatches: CMR = 0.0.\n")
        f.write("- provenance is too conservative in this demo: IDR = 0.0; it misses real internalization.\n")
        f.write("- SFB drops from 0.112 (naive) to 0.009 (provenance).\n")
        f.write("\n## What this does not show\n\n")
        f.write("- This is not a scientific result: 20 synthetic users, 60 events, no LLM, rule-based writers.\n")
        f.write("- It does not validate the real CMR threshold or Gate 1; that needs P2–P5's pipeline.\n")
        f.write("- The provenance writer needs persistence / negative controls / exploration to recover IDR.\n")
    print(f"\nsummary: {summary_path}")


if __name__ == "__main__":
    main()
