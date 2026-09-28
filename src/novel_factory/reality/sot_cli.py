"""Publish and inspect the bounded YAGO historical-ledger SoT PostgreSQL release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from novel_factory.reality.sot import (
    RELEASE_ID_V3, era_packet, evidence_packet, load_foundation, make_release, temporal_ledger,
)


def _ledger_markdown(rows: list[dict]) -> str:
    lines = ["# 시간 미상 역사 주장: 시대 탐색 전표", "",
             "원 주장 유효 시간은 미상이다. 숫자 범위는 같은 인물의 별도 생몰 자료에서 파생한 검색 힌트이며 역사적 참·당시 상태·작품 사용 승인이 아니다.", "",
             "| 원천 ID | 인물 | 관계 | 대상 | 검색용 생애 범위 | 사건 후보 | 사건 근거 원천 ID | 생애 근거 원천 ID |",
             "|---|---|---|---|---|---|---|---|"]
    for row in rows:
        context = row["context_range"]
        event = row["inferred_event_bound"]
        context_label = (str(context["start_year"]) + " ~ " +
                         str(context["end_year_exclusive"] - 1) + "년 (검색용)"
                         if context else "근거 미상")
        event_label = (str(event["start_year"]) + "년 (사건 후보)"
                       if event else "없음")
        event_basis = event["basis_source_statement_id"] if event else "없음"
        basis = (", ".join(context["basis_source_statement_ids"])
                 if context else "없음")
        fields = [row["source_statement_id"], row["subject"], row["predicate"],
                  row["object"], context_label, event_label, event_basis, basis]
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in fields) + " |")
    lines += ["", "원본 날짜의 정밀도는 `xsd:date` 어휘상 day이고 달력은 미상이다. 사건 후보는 같은 YAGO 원천 계열의 별도 진술을 의미상 연결한 것이며 독립 증언이 아니다.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True, help="Local PostgreSQL DSN; do not put credentials in logs")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="install dedicated SoT tables in the dedicated PostgreSQL database")
    publish = sub.add_parser("publish", help="validate frozen foundation before one atomic release")
    publish.add_argument("--foundation", type=Path, required=True)
    publish.add_argument("--revision", choices=("v1", "v2", "v3"), default="v3")
    query = sub.add_parser("query", help="fresh PostgreSQL evidence packet for an explicit year/day")
    query.add_argument("--release-id", default=RELEASE_ID_V3)
    query.add_argument("--entity", required=True)
    query.add_argument("--as-of", required=True)
    show = sub.add_parser("release", help="inspect release manifest and persisted denominators")
    show.add_argument("--release-id", default=RELEASE_ID_V3)
    show.add_argument("--full", action="store_true", help="return complete release-scoped ledger readback")
    source = sub.add_parser("source", help="inspect one retained YAGO source statement and linked Meta")
    source.add_argument("--release-id", default=RELEASE_ID_V3)
    source.add_argument("--statement-id", required=True)
    era = sub.add_parser("era", help="era discovery; derived ranges never become current state")
    era.add_argument("--release-id", default=RELEASE_ID_V3)
    era.add_argument("--period", required=True, help="YYYY or inclusive YYYY..YYYY")
    ledgers = sub.add_parser("ledgers", help="export all undated source-linked claims")
    ledgers.add_argument("--release-id", default=RELEASE_ID_V3)
    ledgers.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    from novel_factory.reality.adapters.sot_postgres import PgSotStore

    store = PgSotStore(args.dsn)
    if args.command == "init":
        store.init()
        result = {"database": "ready", "release": "not_changed"}
    elif args.command == "publish":
        prepared = make_release(load_foundation(args.foundation), revision=args.revision)
        result = store.publish(prepared)
    elif args.command == "release":
        snapshot = store.read(args.release_id)
        result = snapshot if args.full else {"release": snapshot["release"], "persisted_counts":
                                         {key: len(snapshot[key]) for key in ("entities", "source_statements",
                                                                           "source_meta", "claims", "decisions", "member_ids")}}
    elif args.command == "query":
        result = evidence_packet(store.read(args.release_id), args.entity, args.as_of)
    elif args.command == "era":
        result = era_packet(store.read(args.release_id), args.period)
    elif args.command == "ledgers":
        result = temporal_ledger(store.read(args.release_id))
        if args.format == "markdown":
            print(_ledger_markdown(result))
            return 0
    else:
        snapshot = store.read(args.release_id)
        rows = [x for x in snapshot["source_statements"] if x["statement_id"] == args.statement_id]
        if not rows:
            raise ValueError("Unknown source statement in release")
        result = {"release_id": args.release_id, "source": rows[0],
                  "meta": [x for x in snapshot["source_meta"] if x["parent_statement_id"] == args.statement_id],
                  "claim": next((x for x in snapshot["claims"] if x["source_statement_id"] == args.statement_id), None)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
