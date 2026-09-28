# 수정판 독립 코드 검토: H200 draft scan 가능, 불변 발행 보류

검토 대상: `tools/yago_history_sot/build.py` SHA-256 `e46070d3ef8336caefa7145c5b41e6b1be4c03cf6c5ccff58161f886bc2b1eaf`; `tests/yago_history_sot/test_build.py` SHA-256 `f4d32cebe999901907668f73d041fbeeca344d67673ff89feb1df02e82b2fdc3`. 로컬에서 `PYTHONPATH=. python3 -m pytest -q tests/yago_history_sot/test_build.py`를 독립 실행해 **8 passed**를 확인했다. H200 원본이나 새 PostgreSQL을 이 검토자가 직접 읽지 않았으며, 대량 스캔·결과 분모·릴리스는 아직 수락하지 않는다. 이전 [초안 검토](early-code-review.md)의 관측판과 혼동하지 않는다.

## 코드상 해결된 선행 결함

- `1899` 직접 사건 날짜 포함, `1900` 직접 사건 날짜 제외; `1890..1910` Meta 상태의 실제 끝 `1910`과 선택 컷오프 `1899`가 별개 필드다.
- Meta의 단일 시작/끝은 `dated_boundary_candidate`이며 `H_state`가 아니다. `rdf:type`과 기타 분류는 `K_taxonomy_timed`, 임의 `yago:onDate`는 `dated_observation_candidate`로 H 조회에서 제외된다. 허용 술어를 명시한 양끝 상태만 `H_state`가 된다.
- `-0044-02-31`은 `invalid_month_or_day`로 보류, `-0044` raw 연도와 달력 미상은 보존한다. `0000`은 held다. 날짜 파서의 양수 윤일 판단은 Gregorian을 사용하므로 이것은 YAGO 명목 어휘 검증일 뿐 역사 역법의 확정이 아니다.
- `prepare_context_index`는 동일 주체의 출생/사망 앵커가 각각 정확히 하나이고 순서가 유효할 때만 별도 context를 만들며 근거의 source_file/line_no를 저장한다. 날짜 없는 진술은 `auxiliary`의 `context_hint`로 놓고 H `valid_time`이나 상태 조회에 넣지 않는다.
- 큰 메모리 목록을 제거하고 SQLite disk index·Bloom/PG server cursor를 사용해 처리량에 비례해 Python 메모리가 커지는 주요 경로를 줄였다. 완료된 파일 단계의 ledger SHA·원본 SHA·stage/PG 행 수를 재검사하며 미완료 파일은 처음부터 재처리한다. 파일 내부 커서는 이번 최소 배치 수락 조건이 아니다.

**정정:** 의미 함수의 8개 테스트만으로 전체 draft scan 실행 가능 상태를 수락할 수 없었다. H200에서 e460 실행은 Meta 원본 hash 검증과 receipt 작성을 마친 뒤 facts 단계 진입에서 `time` 지역변수가 같은 이름의 시간 모듈을 가려 `UnboundLocalError`로 종료했다. facts 원본 읽기·PG 적재 전에 멈췄다고 엔지니어가 보고했다. 따라서 e460의 Meta 완료 증거는 stage/receipt 대조 후 재사용할 수 있으나, e460의 pipeline 실행 수락은 **취소**한다. 엔지니어는 수정 실행판과 e460을 분리 보존하고 실제 작은 PG fixture에서 meta→facts→context→aux→readback 전 경로 smoke를 수행해야 한다. 원격 입력 파일의 전체 해시 대조·메모리/디스크 실측·전수 분모도 아직 수락하지 않는다.

## 발행 전 필수 수정·검사

1. **독립 수락의 결과 결박**: e460 `publish()`는 acceptance의 `accepted=true`와 code/manifest SHA만 확인한다. 이 상태에서는 검토 후 PG staging이 변해도 다른 결과를 발행할 수 있다. 수락 파일은 검토한 staging `readback_sha256`, 행 수, receipt bundle SHA를 포함하고 발행 시 계산값과 정확히 같아야 한다. 따라서 이 검토는 `accepted` JSON을 만들지 않는다. 엔지니어가 후속 코드에서 보강하겠다고 답했다.
2. **재개 단계 검증**: `attach_meta()` receipt 재사용은 `meta_evidence` 실제 수·연결과 비교하지 않는다. meta/context Bloom은 크기만 검사한다. 체크포인트가 다른 stage의 같은 크기 산출로 바뀌어도 감지해야 한다. 종속 단계 내용과 연결을 검사하거나 무효화하는 시험이 필요하다. 엔지니어가 후속 코드에서 보강하겠다고 답했다.
3. **보조층 선택 범위**: e460의 labels 선택은 두 생몰 앵커가 있는 `subject_context`만 사용한다. 직접 날짜가 있는 기관·국가·사건·지식 claim의 주체는 라벨이 있어도 제외된다. taxonomy도 bounded 인물 context의 `rdf:type`을 통해서만 선택된다. 세계사 기초 claim의 실제 대상과 일치하도록 disk 기반 선택을 넓히거나, 릴리스와 조회의 누락 범위/분모를 명시해야 한다. 엔지니어에게 전달했다.
4. **Meta와 후보의 지위**: `seen`은 facts에서 Meta 부모를 본 수이며, PG `meta_evidence`에 연결한 수와 다르다. `attached`, excluded/unknown 부모, 원 자료에 없는 부모를 구분해야 한다. DB의 `dated_*_candidate`·K·H 정책 판정은 역사적 진실 검토나 작품 사용 적격으로 읽지 않도록 릴리스 보고와 실제 조회에서 구별해야 한다. 원 Meta raw/행/입력 SHA, claim↔Meta 부모, 미상/실패 분모를 Luna 결과와 대조한다.
5. **원본 및 실제 PG 발행 gate**: 소스는 선택한 YAGO manifest의 원본 해시와 전체 파일 scan 완료를 대조한다. 발행 때 PG claim/Meta/aux/context 수, 고아 연결, H 컷오프, readback을 수락판과 비교하고 새 연결로 재조회해야 한다. 동일 재실행 멱등과 변경 거부, 옛 r3 DB·Wikidata 다운로드 보존을 원격 증거로 확인한다. `source_scan`과 release payload는 원본/실행·발행 코드·정책판·분모를 식별해야 한다.

다음 수락 단계: 엔지니어의 수정된 발행 코드와 fixture, 실제 H200 선택 파일별 receipt 및 PG staging readback을 받아 독립 검사하고, Luna의 기계 점검 결과를 대조한다. 그 전에는 최종 릴리스 ID나 수락 JSON을 만들지 않는다.
