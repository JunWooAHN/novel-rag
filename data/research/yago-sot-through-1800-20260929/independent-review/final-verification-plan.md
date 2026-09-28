# 실제 세계사 SoT 최종 독립 검증 준비

상태: **절차 준비, 전량 결과·발행 미검토**. 스캔 실행 코드는 `ad4f94668b380e4344c391deaaecc8b2ec104291100b0b4544879063a8534932`으로 고정되어 있으며, [범위 한정 코드 수락](scan-code-acceptance-ad4f9466.md)은 실제 전량 수락이 아니다. 검토자는 프로덕션 코드·DB writer가 아니다.

## 이번 독립 Sol 담당

1. 스캔 종료 후 고정 manifest·실행/발행 코드 SHA와 모든 단계 receipt의 완결성을 읽는다. `readonly_verify.py`를 **전용 PG DB의 read-only 트랜잭션**으로 실행하여 릴리스 내용 4개 테이블의 전체 readback SHA·행 수, receipt bundle SHA, source receipt SHA와 manifest 일치 여부를 구한다. 이 스크립트는 원본 TTL 78 GB를 다시 읽지 않고 acceptance 파일도 만들지 않는다. 엔지니어 `prepublish` 출력과 해시가 같아야 한다.
2. `1899` 직접 H 시점 표본, `1900` 직접 사건 누출 0, 기원전 연도 표본(없으면 없음으로 기록), 1899를 가로지르는 상태의 **원래 1900 이후 종료 연도 보존**, 미상/별도 context 근거의 H query 미승격, K·taxonomy의 H 분리, Hangul `schema:startDate` 등 유형 미확정 경계를 조회한다. 후보 0건과 전체 자료 부재를 혼동하지 않는다. `H_boundary`는 원 source의 경계 어휘일 뿐 K 기원·당시 사용 증명이 아니다. `1900` 사용자 query는 발행 후 CLI에서 결과 0과 컷오프 표시를 별도 확인한다.
   - 명시적인 허구 유형은 별도 검토 대상이다. [고정 4.6 schema 영수증](../run-evidence/fictional-schema-check.json) SHA-256 `f697eee9ed9edf15c41386a62e7efa359fc100e2c1b9e7c4634161b9188e38e9`은 manifest와 일치하는 `yago-schema.ttl` SHA-256 `b3f185f27c21e0e2b561dc92f7f9e3d54ccd6f4acac01e9ae97c2d42ef3b636f`의 254–257행에서 `yago:FictionalEntity`를, 1330·1511행에서 인물과 허구 개체를 허용하는 관계 range를 확인한다. 따라서 YAGO 4.6이 허구 개체를 원천 배제한다는 전제는 성립하지 않는다. 이 schema 확인만으로 실제 선택된 pre1900 H 주체에 허구 개체가 있는지는 결론낼 수 없다. `rdf:type`는 Meta가 있는 경우 claim의 `K_taxonomy_timed`, 없는 경우 context 보조층에 들어갈 수 있으므로 **두 경로**에서 명시적 `yago:FictionalEntity` 유형과 pre1900 H 주체를 결합해 조사한다. 유형의 부재 조회만으로 모든 허구 개체가 배제됐다고 주장하지 않는다. 명시적 허구 유형의 H가 현실 역사로 노출된다면 fiction/held 지위나 정책 필터를 발행 전 결정해야 한다. 신화성 일반 판정은 이번 범위 밖이다.
3. 전량 staging 수치와 원 출처 표본을 Luna 결과·엔지니어 보고와 대조한다. 의미적으로 설명할 수 없는 컷오프·K/H 혼합이나 결과 hash 차이가 있으면 실제 발행 수락을 보류한다. 정확한 코드/manifest/readback/receipt bundle SHA와 4개 행 수, 검토 근거 경로를 넣은 **별도 최종 `accepted=true` JSON은 이 모든 대조가 끝난 뒤** 소유 폴더에만 작성한다. 현재는 작성하지 않는다.
4. 엔지니어 단일 writer가 불변 발행한 후 새 DB 연결에서 release ID·payload·readback을 다시 확인한다. 잘못된 acceptance/output hash의 발행 거부와 발행 뒤 UPDATE/DELETE 거부, 같은 입력 재실행 멱등, 별도 백업/복원 영수증 및 기존 다섯 대상 r3 DB/release 불변 근거를 대조한다. 복원 영수증이 없으면 그 한계를 정확히 남긴다. 작업 카드는 실제 release 또는 실행 중/차단 상태 중 하나만 보고한다.

Luna는 **선택 파일별 물리행과 mapped/excluded/unknown/failed 전수 분모, Meta 부모 연결·원 source byte/line 표본, 각 lane의 기계 수치와 raw 출처 hash**를 맡는다. Sol은 그 수치를 인용·대조하지만 같은 78 GB 스캔을 반복하지 않는다. 엔지니어는 단일 DB writer로 source hash·stage receipt·prepublish·발행/복원 실행 영수증을 만든다. 루트는 코드판·역사 사실/작품 권한·문서 체크포인트와 완료 보고를 취합한다.

## 후대 사망지 누출 반례

[합성 회귀 bundle](../run-evidence/deathplace-regression-bundle.tgz) SHA-256 `5727c9c71475226e7874dcdceb7256fe8d1f919d78dc9557ced6a404d5357cb4`, [재현 스크립트](../run-evidence/deathplace-regression.py) SHA-256 `7d365dafd237045428490a619843aca56a2c94dc76ca1e7db5951213d598c3fa`. bundle 내부 `deathplace-regression-result.json`은 ad4f 실행·1880 출생/1905 사망/사망지 진술에서 대상의 `context_anchor` 0 및 1899 이전 사망지 context 0을 기록한다. 합성 자료의 범위 한정 반례이며 실제 DB 전량 누출 0의 증거로 확대하지 않는다.

## 기존 r3와 새 기초판을 비교할 때의 말뜻

r3 다섯 대상의 한글 `1443` `schema:startDate`는 원 raw를 가진 **K 기원 후보**로 기록했다. ad4f 전역 정책은 직접 `schema:startDate`를 주체 종류 판정 전에 `H_boundary`로 놓는다. 따라서 새 판의 H_boundary를 한글이라는 지식판의 독립 검증된 발생, 1450년 사용/보급 B, 역사적 진실로 보고하지 않는다. `rdf:type`+Meta는 새 판에서 `K_taxonomy_timed`로 분리되지만, K 내용판·최초 기원·당시 인지를 완성한 것은 아니다. 유효 구간 없는 일반 taxonomy/K 관계는 기초 역사 H 상태나 당시 사용으로 승격하지 않고 미상/보조층·제외 분모에 남는다. r3의 `context_range`/사건 유도 규칙과 새 전역판의 동일 구현을 가정하지 않는다. 실제 source와 report가 이 구별을 유지하는지 최종 확인한다.
