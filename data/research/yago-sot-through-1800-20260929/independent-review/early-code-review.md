# 신규 YAGO 세계사 어댑터 조기 독립 코드 검토

상태: **초안 검토, 발행 불수락, 수정·시험·H200 실측 대기**. 엔지니어가 동시에 수정 중인 `tools/yago_history_sot/build.py`에서 검토한 SHA-256은 처음 `f5574b514e547ac1737ec2fba6e5703c2479d2fa8c7209d388f44a3961982942`, 이어 `f36a235ce71f3deec5565761ad19e5228a7ca491982039082b26787bdf58a54d`, 마지막 읽기 `0c57d3f32b51990098b50d75b2e513e95c4725b73c7dc74c0e762cd2636548ea`다. 아래 문제는 이 초안 관측과 함수 호출 결과다. 후속 수정판의 결함 지속 여부나 전체 실행 결과를 판정하지 않는다. 검토자는 구현·DB·원본을 수정하지 않았다.

## 발행 전 해결할 사항

1. **시간 범위가 없는 상태의 수락**: 마지막 읽기판 `choose_time`은 Meta 시작 하나 또는 끝 하나만 있는 사실을 `H_state`로 반환한다. 실제 호출에서 `schema:spouse`의 `startDate=1800`은 `end_year=None`, `endDate=1800`은 `start_year=None`인 H_state였다. 현재 `query`는 `None`을 무한 범위처럼 비교하여 각각 1899년까지 또는 모든 이전 연도로 유효한 상태를 만든다. 단일 경계·누락 경계는 보수적 후보/미상으로 격리하거나 명시 근거 있는 검색 제한을 따로 두어야 한다. 1890..1910처럼 양 끝이 있는 crossing 상태는 원 종료 1910을 보존하고 1899 이전 겹침만 범위 조회한다.
2. **타입과 관찰값의 H 승격**: `rdf:type yago:Person`에 Meta 1800..1850을 넣은 호출이 `H_state`를 반환했다. `yago:onDate`가 달린 임의 관계도 `H_observation`이 된다. 직접 날짜를 가진 술어도 `dated_other_candidate`로 남기는 의미 정책을 Meta 경로에 똑같이 적용해야 한다. K·분류·출처 관찰을 시대 사건·상태로 섞지 말고 지원 술어와 미지원 후보 분모를 명시한다.
3. **BCE 날짜 오류**: `nominal_year('"-0044-02-31"^^xsd:date')`가 `(-44, 'nominal_bce_calendar_unknown')`을 반환했다. 음수 연도는 월 일 유효성 검사에서 빠진다. BCE 원 어휘·연도 체계·달력 미상을 보존하면서 명백히 불가능한 일자를 보류해야 한다. 양수 연도에 Python Gregorian 윤일 검사를 역사 달력의 진실로 해석하지 않는 처리도 필요하다.
4. **발행 검증이 receipt에만 의존**: `publish`는 receipt의 선언 hash와 분모만 비교한다. 실제 PG의 claim/Meta/auxiliary 행 수와 원 파일 좌표, parent 연결, cutoff 위반, release payload readback hash를 대조하지 않는다. 중단 후 DB 부분행이 남았거나 receipt가 오래되어도 발행 가능하다. 검토 전 발행을 막는 조건은 현재 docstring뿐이다. 고정 코드·원본 manifest·단계 receipt와 실제 PG snapshot을 검사하고 독립 Sol 수락판 및 Luna 기계 점검의 정확한 ID/hash를 발행 gate에 연결해야 한다. 발행 뒤 새 연결의 readback과 동일 재실행/변조 거절이 별도 확인 대상이다.
5. **단계 재개 판 확인 부족**: `scan_meta`, `scan_fact_file`, `attach_meta` 등은 receipt가 있으면 입력 hash·정책판·단계 DB/bloom/ledger/PG 결과를 재검사하지 않고 통과한다. 반대로 미완료 파일은 처음부터 재처리한다. 파일 단계 단위 재시작 자체는 이번 최소 범위에서 허용된다. 다만 각 완료 단계의 hash·산출·DB 상태 재대조, 미완료 단계의 행 삭제/재처리·정확히 한 번 분모, 종속 단계 receipt 무효화가 필요하다. 파일 내부 커서 구현은 요구하지 않는다.

## 추가로 최종판에서 확인할 계약

- `scan_meta`의 `seen`은 모든 facts에서 Meta 부모를 발견하면 표시하지만 `attach_meta`는 채택 claim의 키만 PG에 넣는다. 따라서 `unmatched_meta_rows`는 실제 `attached + excluded-parent + unsupported/absent-parent` 전체 분모를 나타내지 않는다. 원 Meta의 parsed/time predicate/부모 찾음/채택 claim 연결 여부를 분리해 회계하고, claim→Meta와 raw 파일 행·SHA를 재조회해야 한다.
- 마지막 읽기판에서 context index는 출생 **또는** 사망 앵커 하나만으로 주체를 채택하고, 충돌하는 여러 앵커는 SQLite upsert의 마지막 값이 이긴다. `scan_context`는 연도 bound와 basis source ID를 auxiliary 행에 남기지 않는다. 별도 `context_range`를 표시하려면 방어 가능한 두 앵커·순서·ID·규칙판이 필요하며, 한 앵커만 있으면 시간 미상으로 남겨야 한다. undated 관계가 역사 상태가 되면 안 된다.
- 현재 `claim`·`meta_evidence`는 원 raw/행은 담지만 릴리스에는 claim별 decision과 사람 검토 여부·작품 범위 검토 여부가 보이지 않는다. 최소한 정책 수락/미검토 지위, 원본 YAGO에서 읽은 것과 새 해석의 구별, 불변 판의 근거 연결을 확인한다.
- 선택 manifest를 CLI 인자로 받을 뿐 고정된 원본 manifest SHA와의 동일성은 `publish`에서 확인하지 않는다. 사용자 승인 원본판과 선택 파일 집합을 릴리스 입력에 고정해야 한다. 실패/제외 ledger는 원본 파일 hash와 파일 행 좌표로 재조회 가능해야 하며, 선택 파일 범위와 비선택 YAGO 파일을 명시한다.

엔지니어는 위 1~5번을 수용하고 수정판·테스트를 전달하겠다고 응답했다. 따라서 이 기록은 **수정 요청과 미결 체크리스트**이며 수락 판정이 아니다. Luna의 원본 인벤토리는 [`initial-inventory.md`](../mechanical-review/initial-inventory.md)에 있고, 그 수치는 기존 원본 검증과 다섯 대상 r3를 구별한다. 다음 독립 검토는 수정판의 정확한 SHA, fixture/회귀 테스트, H200 선택 파일 전수 scan receipt, staging PG readback 및 실제 Meta/cutoff 반례를 대상으로 한다.
