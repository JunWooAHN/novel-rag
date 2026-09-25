# 기존 원문을 정답으로 삼는 역설계 입력 계약 v0.1

이 문서는 [핵심 시스템 설계](../../systems/README.md), [현행 실행계획 R/A/B 경계](../../plans/20260918-current-system-execution-plan-v0-1.md), [상세 아키텍처 §11.1](../../20260914-novel-factory-architecture-v5.md)를 작은 개발 예제로 옮기는 계약이다. 순서는 **작가 간 비교 → 사용자의 취향·집필 기준 선택 → 선택한 기존 원문 장면을 정답으로 고정 → 이전 문맥·작품 내 가상 역사표·인물 인지·장면 명세 역구성 → 원문 대조 검수 → 작은 학습**이다. 앞선 선택은 아직 끝나지 않았다. 아래 JSON은 계약을 설명하는 설계 예시이며 학습 투입 승인이나 데이터셋 예시가 아니다. 새 원고를 먼저 생성하는 절차도 아니다.

**개발 자료 지위는 이 예시를 만들기 전에 고정한다.** 이미 분석된 7편의 원문 전체와 그 발췌·이전 문맥·분석 보고서·역구성 파생물은 개발 자료다. 이 문서의 1588 구간과 진행 중인 파일럿도 영구적으로 개발 풀에 속하며 미관측 최종 test로 이동시키지 않는다. 이것은 자료의 지위 결정이지 train/validation/test 건수나 학습 실행 승인 결정이 아니다. 이후 학습용 예시나 문체 reference를 생성하기 **전에** 개발 풀 내부의 split과 중복/문맥 겹침 정책을 고정한다. 그때 같은 장면·겹치는 target/window·파생 질문·이전 문맥이 서로 다른 split에 새지 않도록 묶고, reference는 train에서만 만든다. 별도 미관측 평가는 이 7편 밖의 적법한 자료 또는 독립적 새 집필 과제로 설계한다.

## 두 경계

**검토 레코드**는 정답을 읽은 분석자가 만든 비공개 자료다. 원문 위치와 hash, 관찰과 가정의 근거, 누수 검수, 정답 참조를 보관한다. **Writer 입력**은 실제 집필 시점에 기획자가 줄 수 있는 정보만 담는다. 정답 원문 경로·좌표·표현·이후 장면 원문은 Writer에게 전달하지 않는다. 두 자료는 같은 장면을 가리키되 목적과 열람 권한이 다르다. 학습 builder가 정답을 붙이는 순간에도 정답은 입력 메시지가 아닌 target에만 둔다.

가상 역사표는 **분석 대상 소설의 사건을 학습용으로 재구성한 fixture**다. 공용 원역사도, 실제 작품에서 작가가 승인·잠근 캐논도 아니다. 역구성된 명세를 원저자의 실제 기획 의도라고 주장하지 않는다. 실제 작품 집필에 이 의미 계약을 재사용할 때에만 운영 역사표의 승인·잠금 revision을 별도로 확인한다.

## 최소 필드와 검수

| 영역 | 필수 내용 | 검수 질문 |
|---|---|---|
| `source_ref` | 로컬 원문 경로, 원본 바이트 SHA-256, 좌표 단위, `[start,end)` | 동일 사본·동일 범위를 재조회할 수 있는가? BOM·줄바꿈·정규화 기준이 명확한가? |
| `prior_context` | 목표 장면 **앞**에서만 온 연속 구간 또는 검증된 요약과 그 근거 범위 | 문맥 끝이 목표 시작 이하인가? 대상 장면 뒤 원문을 읽고 만든 줄거리·암시는 없는가? |
| `virtual_history` | 그 시점까지의 상태·사건과 이번 장면이 실현할 계획 사건. 각 항목의 `basis`를 `observed` 또는 `reconstructed_assumption`으로 구분 | 관찰 근거 좌표가 있는가? 추정은 추정으로 남겼는가? 사건 발생·독자 공개·인물 인지를 섞지 않았는가? |
| `character_knowledge` | 인물별 현재 지식·믿음/오해·획득 경로·모르는 정보 | 기획자가 아는 미래를 인물에게 무단으로 주지 않았는가? 예외적인 미래 지식은 설정·경로가 있는가? |
| `scene_spec` | 목적, 실현해야 할 결과/필수 사건, 허용 자유, 금지 전개 | 결과는 사건 수준인가? 정답 문장·대사·어휘·비유를 재현하라는 힌트는 없는가? |
| `answer_ref` | 별도 원문 정답의 `source_ref`와 추출 검증 상태 | 입력에서 분리되고 실제 원문 범위와 정확히 일치하는가? |

기획자는 미래의 목표나 잠긴 역사표를 알고 Writer에게 **이번 장면이 실현해야 할 결과**를 줄 수 있다. 이는 정답 누수가 아니다. 예를 들어 “인물이 이주 선택을 한다”는 필수 사건일 수 있다. 금지하는 것은 그 선택을 원문의 특정 문장·대사·장면 순서로 재현하라는 힌트, 장면 시점의 인물이 알지 못하는 미래 결과를 그의 지식으로 주입하는 것, 목표 장면 뒤의 원문으로 이전 문맥을 오염시키는 것이다. 서술자·독자·인물의 정보 범위를 별도로 확인한다. 계획 사건이 장면 뒤에야 실현되는 것으로 밝혀지면 이번 장면의 필수 사건에서 빼거나 후보 경계를 다시 잡는다.

아래 JSON은 **형태 예시**다. 기존 [간다왼쪽 표본 좌표](../author-study/ganda-left/works/1588-samples.json)의 1화 말미 주변을 사용했지만, 900 코드포인트 관찰 구간은 완결 장면으로 아직 수락되지 않았으므로 `hold`다. 요약과 사건 명세는 실제 후보 확정 시 원문과 재대조한다. 검토 레코드에만 원문 좌표를 두고 Writer 입력에는 선행 문맥의 요약을 넣었다. 실제 학습용 패킷에서는 검수된 이전 문맥 텍스트 또는 검수된 요약을 사용하되 목표 이후를 포함하지 않는다.

```json
{
  "review_record": {
    "example_id": "dev-1588-ch01-choice",
    "status": "hold",
    "source_ref": {
      "local_path": "/Users/ahnjunwoo/dev/novel/docs/references/ganda-left/1588 샤인머스캣으로 귀농 왔더니 신대륙 1-661 완.txt",
      "sha256_raw_file": "7ee52308ed896730c457b9da9158f8dfed4e0ca1aaaf91cba363535cf059fa77",
      "unit": "Python Unicode code point after UTF-8 decode; leading BOM included",
      "start_inclusive": 3035,
      "end_exclusive": 3935
    },
    "basis_note": "1화 관찰 구간의 장면 경계·충분한 선행 문맥·선택지의 최초 공개 시점을 재검수해야 함",
    "prior_context_ref": {"same_source_as": "source_ref", "range": [14, 3035], "verified_prior_only": true},
    "history_evidence": {"current_pressure": [14, 3035], "planned_choice": [3035, 3935]},
    "answer_ref": {"same_source_as": "source_ref", "range": [3035, 3935], "verified_exact_slice": false},
    "leakage_review": "pending"
  },
  "writer_input": {
    "prior_context": {
      "summary": "포도 농장 노동과 귀농 결정이 현재 생활의 압박을 드러낸다."
    },
    "virtual_history": [
      {"event": "현재 생활에 압박이 있다", "basis": "observed"},
      {"event": "이번 장면에서 이주 여부를 선택한다", "basis": "reconstructed_assumption", "role": "planned_for_this_scene"}
    ],
    "character_knowledge": [
      {"character": "선택하는 인물", "knows": ["자신의 현재 형편"], "believes_or_misunderstands": [], "does_not_know": ["선택 이후 실제 이주의 결과"], "acquisition": "장면 이전 경험"}
    ],
    "scene_spec": {
      "purpose": "생활상의 압박을 행동 선택으로 연결한다",
      "required_events": ["인물이 이주 여부를 결정한다"],
      "allowed_freedom": ["대사", "묘사", "장면 내 세부 구성"],
      "forbidden": ["다음 회차의 결과를 현재 인물의 확정 지식으로 서술", "원문 표현 재현 지시"]
    }
  }
}
```

이 JSON은 구현 스키마가 아니라 사람이 점검할 최소 기록 형식이다. 실제 `toy-tune` v1 source bundle로 내보낼 때에는 [현행 데이터 계약](../../../toy-tune/docs/data-contract.md)의 `answer`, `source_id`, `source_sha256`, 문자 인덱스 범위를 **별도로** 채우고 검사한다. 그 계약의 SHA-256은 `sources[].text`의 UTF-8 바이트 hash이고 위 `sha256_raw_file`은 BOM·CRLF를 포함한 원본 파일 바이트 hash다. 좌표를 옮기거나 원문을 정규화하면 hash와 범위를 다시 계산한다. `packet_id`는 현재 builder가 거부하므로, 본 문서가 구현된 패킷 반입을 뜻하지 않는다.

검수자는 (1) source hash·범위·정답 정확 일치, (2) 이전 문맥의 시간/좌표 상한, (3) 역사 사건별 관찰/가정 근거, (4) 인물 지식 경계, (5) 명세가 결과만 지정하고 표현을 누설하지 않는지, (6) 학습 예시·reference를 만들기 전에 정한 split과 겹침 정책을 확인한다. 이 문서만으로 새 원문에 대한 학습 허락을 추정하지 않는다.
