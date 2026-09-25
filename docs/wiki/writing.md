# 작가 분석·역구성·학습

선행 자료는 사용자가 지정한 **리첼렌·간다왼쪽·명원·마늘맛스낵**의 보유작 7편이다. 작품별 Luna 구조 지도와 초·중·후반 대표 장면 분석, 작가별 Sol 검토·프로필 4건이 완료됐다. 전편 정독이나 흥행 인과 검증은 아니다. 한 편만 보유한 작가의 작품 간 반복성은 확정하지 않는다. [작가 연구 현황](../research/author-study/README.md), [실행계획 §3.1](../plans/20260918-current-system-execution-plan-v0-1.md#31-r-단계의-분석과-산출물)

네 작가의 비교표와 집필 기준 **초안**은 교차 검토되었다. 설명 방식, 성취와 비용, 시점 거리, 회차 끝의 처리 등은 사용자 선택 전이다. 관찰한 원문 기법과 효과 해석, 실제 판매 원인을 구분한다. [작가 비교](../research/writing-spec-v0-1/author-comparison.md), [집필 기준 초안](../research/writing-spec-v0-1/writing-criteria-draft.md), [검토 현황](../research/writing-spec-v0-1/README.md)

학습 순서는 **사용자가 선택한 기존 원문 구간을 정답으로 고정 → 이전 문맥·가상 역사표·인물 인지·장면 명세를 역구성 → 원문 대조·누수 검수 → 작은 Gemma 학습**이다. 정답의 문장·대사와 이후 장면 결과를 Writer 입력에 넣지 않는다. 계획 사건은 결과 수준으로 입력할 수 있지만 가상 역사표는 원저자의 실제 기획 의도나 승인된 작품 캐논이 아니다. 검토 레코드와 Writer 입력을 분리한다. [입력 계약](../research/writing-spec-v0-1/reverse-input-contract.md#두-경계), [핵심 설계 §5](../systems/README.md#5-모델과-데이터의-역할)

1588 1화 장면의 개발 파일럿은 입력 계약 검사 대상으로 `accept_for_prototype` 판정을 받았다. 이는 학습 투입·사용자 취향 채택·실제 역사 설계·잠금 검증이 아니다. 분석한 7편과 파생물은 개발 자료이며 미관측 최종 test가 될 수 없다. 학습 예시·문체 reference를 만들기 전에 split·겹침 정책을 고정해야 한다. [파일럿 및 상태](../research/writing-spec-v0-1/README.md), [후보 정책](../research/writing-spec-v0-1/reverse-candidate-policy.md)

Gemma는 운영 생성·재작성과 문체 학습 목표, Munche는 소설 문체 비교·예문 검색, Granite는 역사·과학·인물 지식 검색, 역할별 SOTA는 역설계·검수·추출·입력 역구성을 맡는 **문서상 선택**이다. 실제 모델 revision·지원·성능은 실행 전 검증 대상이다. 현재 `toy-tune`의 `doctor`, `prepare`, `verify-dataset`은 학습 완료가 아니며 실제 H200 학습·재로드도 아직 수행되지 않았다. [핵심 설계 §5–6](../systems/README.md#5-모델과-데이터의-역할), [실행계획 §1·3](../plans/20260918-current-system-execution-plan-v0-1.md#1-출발점)

**역사 경로와 문체의 역할:** SOTA는 앵커 사이의 역사 경로·중간 사건과 서사적 갈등·선택·대가를 설계·검토한다. Gemma는 작가가 승인해 잠근 역사표를 학습된 문체로 본문에 실현한다. 이 역사 Backfilling은 위에서 설명한 기존 원문 정답의 **학습 입력 역구성**과 다르다. 재미 우선·전문가도 납득할 개연성이라는 목표는 경로 선택부터 적용한다. [핵심 설계 §1–5](../systems/README.md#1-만드는-것), [이음새 통합 문서](../systems/20260924-history-ontology-and-anchor-bridges.md)

학습·분석의 확인 상태와 다음 결정은 [현재 상태](status.md)에, 실제 작품 집필의 승인·잠금 흐름은 [역사 설계와 집필](system.md)에 있다.
