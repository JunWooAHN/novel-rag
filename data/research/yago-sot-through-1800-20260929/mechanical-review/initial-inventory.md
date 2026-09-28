# YAGO 원본·기존 r3 기계 인벤토리

상태: **초기 근거 인벤토리만 완료**. 신규 1899 포함 세계사 적재의 구현·DB 결과는 아직 검증하지 않았고 완료 수락을 하지 않는다.

- 고정 원본 manifest 사본: `data/research/yago-storage-20260928/manifest-final.json`, SHA-256 `da0d761331e3ccb070bfebbc5ecf4ad5db4165eac0ef5bc619444d95f78a70bb`. 기록상 YAGO 4.6 아카이브 12개와 추출 엔트리 12개, 압축 9,907,409,082 B, 추출 78,426,497,491 B다.
- 최종 relay 기록은 `relay-final.exit` 값 `0`, 로그 SHA-256 `d385215846a7018461aa8dc4d42f1c1982ad0db3875d02dc2315d70164c2662b`다. 기존 최종 검증은 ZIP CRC/SHA 및 추출 SHA/크기/모드를 확인했다. 새 SSH 재접속 기록 SHA-256 `92f568636c32e0673cad40f3b109f4384d710544c0a2ed34fde8d4990c969da6`는 ZIP·추출 파일의 이름·크기·모드·marker 일치와 빈 문제 목록을 확인했으며 78 GB 전체 hash 재계산은 하지 않았다.
- 새 작업 후보에 가까운 기존 파일의 manifest상 추출판은 facts `5,087,821,943 B`, SHA `17da906cefea15aa076ccfd5ce0bd2956b2e95ae06b225cca18059bbaf5eb1e4`; Meta `720,870,838 B`, SHA `d6ddcf0803a13fcf69f3b32df2c6f817fc6a807c27bd9cae429287dbc460c020`; beyond-Wikipedia `17,209,268,126 B`, SHA `15cd804c1f5ab52f3766766886a44270f68cef8cfc5ebbc4240bb20c0d4b4b3b`다. 이 값은 원본 manifest의 검증 결과를 인용한다. 이 로컬 checkout에서는 H200 저장소 경로가 마운트되지 않아 직접 읽거나 원본을 재해시하지 않았다.
- 기존 다섯 대상 r3 readback은 SHA-256 `71161cba74d438dc7f0bef10875ba4f8022048fd9cb7316e0b43e649f7d60ed2`이며 해당 파일 자체가 고정한 범위는 entity 5, source statement 152, Meta 40, claim/decision/member 각 50이다. 이전 입력 점검 SHA `1c37627a1e4b98c684df379212e78d14a76ef648bea7c8c662e8e4b58f882416`의 분모는 5대상 캡처이며 mapped 130, excluded 22, unmapped 0(그 안에 alias 70, external ID 10, structural 50), Meta linked 24·outgoing orphan 5·incoming observation 11을 기록한다. **이는 YAGO 전체 stream 분모가 아니다.**
- 기존 foundation SQLite를 읽기 전용으로 확인한 SHA-256은 `640261c0eea9d3b064aba865f78c6d3c905098d63635fb8ea3deebfc0d551b14`, 크기는 139,264 B, `quick_check`는 `ok`였다. r3가 선언한 foundation SHA와 일치한다. 기존 r3 DB 불변성 영수증은 같은 입력 재실행 시 새 릴리스 미생성 및 변경 시도 거부를 기록한다. 이 파일럿은 새 SoT 결과를 입증하지 않는다.
- 기존 1890년 질의는 다섯 대상 파일럿의 23개 문맥 claim에 한정해 event/context 0건이었다. 이를 1899 cutoff 검증이나 전체 데이터 미래 누수 점검으로 확대하지 않는다.

다음 실제 산출물에서 full-stream 선택 manifest와 분모를 고정한 뒤, mapped/excluded/unknown/failed 회계, dedup 전후 수, facts·Meta anchor와 부모 연결, BCE/1899·1900 경계, date-unknown의 별도 context bounds, post-cutoff 누수, 새 불변 release readback을 확인한다. 표본 점검이면 표본 수와 전수 미점검 범위를 따로 기록한다.

기계 판독 세부와 각 파일의 실제 SHA-256은 같은 폴더의 `initial-inventory.json`에 있다.
