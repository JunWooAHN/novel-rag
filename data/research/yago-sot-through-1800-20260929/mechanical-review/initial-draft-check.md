# YAGO 1899 SoT 초기 draft 기계 점검

**판정: 제한된 중간 snapshot 점검만 완료. 최종 수락은 하지 않았다.** 사실 파일은 계속 적재 중이며 Meta 연결, context, auxiliary, release 단계가 남아 있다.

첫 Meta receipt 파일 SHA-256은 `c8036e0a751584da8a4ecebe746397b135acbaf351ed867f700267a680a6fa2a`이며, receipt가 보고한 ledger SHA-256은 `d7217bcd3e645a693be624ead125575fa7d631747cf8f4b883b333b3c8d957b1`이다. 원본 manifest 추출 Meta의 `720,870,838` byte / SHA-256 `d6ddcf0803a13fcf69f3b32df2c6f817fc6a807c27bd9cae429287dbc460c020`와 receipt의 byte·source SHA가 일치한다. 행 회계는 `6,221,779 = 6,221,745 + 34`로 맞는다. 이 receipt는 Meta 단계만 뜻하며 첫 attempt 전체는 이후 `scan.exit=1` (`UnboundLocalError`)로 끝났다. 고정된 다음 코드의 실제 SHA-256은 `ad4f94668b380e4344c391deaaecc8b2ec104291100b0b4544879063a8534932`다.

H200 DB `reality_yago46_through_1899_20260929`의 짧은 `REPEATABLE READ READ ONLY` snapshot에서 facts line `<=7,000,000`에 해당하는 mapped claim 93,967건을 보았다. lane 분포는 H_event 67,681, H_state 1,918, H_boundary 14,704, K_taxonomy_timed 5,784, 나머지 날짜 검토 후보 3,880건이다. 직접 point year가 1900 이상인 claim은 0, H_event 날짜 누락도 0이었다. H_state 694건은 source end year가 1900년 이후지만 모두 `scope_end_year=1899`를 보존한다. 5개를 원문 byte offset에서 재확인했다. 따라서 이는 현재 event 누수로 세지 않되 최종 query/readback에서 cutoff cap 적용을 확인해야 한다.

11개 raw line byte sample은 원문 offset·개행 경계·terminator와 일치했다. 첫 3개는 작은 prefix 개행 수로 line number도 맞췄고 이후 샘플은 원문/offset만 직접 맞췄다. Meta evidence·context anchor·auxiliary·release 행은 아직 0이다. attach-meta 이전이므로 orphan 수를 판정하지 않았다. context가 아직 생성되지 않아 context 검사도 미실행이며, 1880 출생·1905 사망 장소 claim은 이번 7M mapped-event slice에서 짝을 찾지 못했다. 전체 stream 부재를 뜻하지 않으므로 후기 regression으로 유지한다.

전체 facts 분모와 unknown/excluded/failed 수, Meta orphan 회계, context 규칙, H_state cutoff readback, 나머지 단계와 immutable release는 완료 receipt 이후 재검증한다. 상세 snapshot ID·실제 hash·byte 좌표는 `initial-draft-check.json`에 기록했다.
