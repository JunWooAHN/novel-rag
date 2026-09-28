---
category_id: research
lineage_id: lin-eb924976-5287-44bf-8e80-f5b6d6723a43
document_id: doc-1a5564b3-f021-4234-ad1c-da41b8e91bfe
parent_lineage_id: lin-1a78dc59-6af9-4445-88e4-858f5327a856
abstract: YAGO 4.6을 위키백과 기반 현실 역사 전표의 구조적 바탕으로 사용할 때 공식 배포·논문·코드의 근거와 한계를 검토한다.
version: 0.0.1
created_at: '2026-09-28T03:44:12Z'
updated_at: '2026-09-28T03:56:11Z'
tags:
- YAGO
- 위키데이터
- 위키백과
- 역사온톨로지
canon: false
---
# YAGO 4.6의 현실 역사 전표 기반 적합성 조사

상태: **2026-09-28 공식 자료 조사·코드 부분 독립 검토 수락·비캐논. 제품 채택 또는 역사 릴리스 승인 아님.** 이 문서는 [현실 역사 온톨로지 변환기 PRD](../prd/wikipedia-history-ontology.md)의 H/K/B/F와 [핵심 시스템 설계](../systems/README.md)의 현실·작품 승인 경계에 비추어 YAGO 4.6의 사용 가능 부분을 검토한다. 공개 YAGO 전체 덤프 다운로드·로컬 적재·H200 작업 변경·역사 사실 품질 표본 평가는 하지 않았다. 논문과 페이지의 수치는 저자 보고값, 아래 한 개체 SPARQL 결과만 이번 조사 실측이다.

## 판과 수치의 기준

[YAGO 홈페이지](https://yago-knowledge.org/)는 4.6을 최신판이라 표기하고 2026년 7월 출시, 9월 ISWC 2026 demo paper 수락을 알린다. [4.6 배포 페이지](https://yago-knowledge.org/downloads/yago-4-6)는 Wikidata에서 고른 3,900만 개체·1억 6,700만 사실을 설명한다. [4.6 논문](https://suchanek.name/work/publications/iswc-2026-demo-yago.pdf) p.3 표 2의 비교는 **4.5: 4,900만 개체·1억 3,200만 사실 → 4.6: 3,900만 개체·1억 6,700만 사실**이다. 반면 [4.5 배포 페이지](https://yago-knowledge.org/downloads/yago-4-5)는 4.5 사실을 1억 900만으로 표시한다. 서로 다른 4.5 수치를 섞어 증감률을 계산하지 않는다. 4.6 논문은 개체 감소를 제외 대상 하위 클래스 확대(19→77)와 연결하지만 사실 증가의 기여 요인을 정량 분해하지 않는다(p.2–3). 속성 수 확대는 관련 관찰이지 사실 증가량의 확정 원인은 아니다.

4.6 논문 p.3 표 2의 `64G`는 저자가 제시한 덤프 크기다. [공식 배포 인덱스](https://yago-knowledge.org/data/yago4.6/)의 ZIP 표시 크기를 별도 합산하면 schema·taxonomy·영문 위키 페이지 보유 개체의 facts/labels·meta 5개가 **3,165,146,257 bytes**, beyond-Wikipedia facts/labels까지 7개가 **9,207,904,854 bytes**다. tiny·JSONL·제외 로그를 포함한 목록 12개 총합은 **9,907,409,082 bytes**다. 이는 디렉터리 표시값의 산술합이지 다운로드, 압축 해제, DB 색인, 메모리의 실측치가 아니다. 인덱스 파일 시각은 2026-08-03 03:04–03:06(인덱스 시간대 미표기)이고 공개 schema ZIP의 HEAD는 `Last-Modified: Mon, 03 Aug 2026 03:04:52 GMT`를 반환했다. 출시 월과 파일 수정 시각을 같은 날짜로 취급하지 않는다. 파일별 값과 HTTP 기록은 [기계적 조사](../../data/research/yago-20260928/inventory.md), [HEAD 원기록](../../data/research/yago-20260928/head-check.txt)에 있다.

## 4.6에서 달라진 구조와 논리 보장의 범위

[4.6 논문](https://suchanek.name/work/publications/iswc-2026-demo-yago.pdf) p.2는 최상위 클래스·속성을 YAGO 팀이 직접 정의하고 schema.org의 **식별자**를 사용한다고 설명한다. 최상위 수동 클래스 39→55, 제외 클래스 19→77, 수동 속성 123→155 및 Wikidata 속성 212개 매핑을 보고한다. 상위 11개 분류의 합계에는 `Event` 110만, `BioChemEntity` 17.1만, `MedicalEntity` 2.2만이 포함된다(p.2 표 1). 논문은 의료·생화학 상위 분류를 **4.6의 신설 분류**로 표시한다. 이 개체 수가 과학 원리, 공정, 시대별 기술 보급 관계까지 갖추었음을 뜻하지는 않는다. 4.6은 동일 날짜의 시작·끝 병합, 단위 타입 검사, 누락/잘못 생성된 진술의 수작업 점검도 기술한다(p.2). [공식 4.6 배포 페이지](https://yago-knowledge.org/downloads/yago-4-6)는 schema·taxonomy·facts/labels·beyond-Wikipedia facts/labels·RDF* meta·제외 로그를 파일군으로 공개한다.

주요 새 기능은 **제외된 Wikidata 진술의 사유를 RDF* 로그로 노출**하는 것이다(4.6 논문 pp.1,3–5). 표 3은 `maxCount` 초과 약 84.7만, domain 검사 실패 약 110만, range 검사 실패 약 150만, 객체가 YAGO에 없어 제외 약 600만 등 여러 이유를 집계한다. 다만 고의 제외(예: 학술논문·메타클래스), 형식 문제, 의미 제약 위반을 같은 ‘Wikidata 오류’로 묶으면 안 된다. 논문은 기능성 속성의 오래된 값을 제거한 뒤 남은 경합을 임의로 결정한다고 설명한다(p.4). 현재 공개 코드에서는 뒤의 표처럼 더 구체적인 정렬/선택 로직이 보이며, 둘을 동일 동작이라고 단정할 수 없다. 어느 설명도 역사상 상충 견해를 심사했다는 의미는 아니다. 클래스와 개체 분리를 위해 **클래스에 붙은 속성 약 280만 건**을 버리는 것 역시 논문이 인정한 정보 손실이다(p.3–4).

여기서 *논리 일관성*은 **정의한 제약**을 대상으로 한 것이다. [4.6 논문](https://suchanek.name/work/publications/iswc-2026-demo-yago.pdf) p.5는 SHACL/OWL의 값 타입·기능성·라벨 등 제약을 Apache Jena와 pySHACL로 검사했고, 검사 오류가 음수 연도 날짜의 pySHACL 처리에 한정됐다고 보고한다. 그 기술을 기원전 날짜 지원의 일반 보증이나 전체 사실의 진위 검증으로 넓히지 않는다. [4.5 논문](https://suchanek.name/work/publications/sigir-2024.pdf) pp.7–8도 OWL API/Pellet 및 Jena SHACL 검사를 보고하며, 외재 평가는 2019년 영어 위키백과 기반 **19,000개 개체 연결 표본**에서 YAGO 4 대비 YAGO 4.5의 macro 정확도 52%→58%다. 4.6 논문에는 역사 사실의 precision/recall, 시대·지역별 재현율, 역사 인과관계 정답률 평가가 없다. 과거 [YAGO 2s의 95%](https://yago-knowledge.org/downloads/yago-2s)는 당시 위키백과와 대조한 구판 설명이며 4.6이나 역사 전표의 정확도 수치가 아니다.

## 시간·출처·다국어·역사 범위

[4.5 논문](https://suchanek.name/work/publications/sigir-2024.pdf) pp.5–7은 Wikidata full Turtle에서 사실의 timestamp를 읽어 RDF* meta에 붙인다고 설명한다. [4.6 배포 페이지](https://yago-knowledge.org/downloads/yago-4-6)도 meta를 사실에 대한 주석이라 설명한다. 다만 아래 공개 4.6 코드에서는 `wdt:` 사실에 대응한 첫 statement의 일부 날짜만 추출한다. 어느 자료도 프로젝트가 필요한 사건 발생/유효 시각, 공개 시각, 인물의 인지·보급·적용 시각을 모두 구분해 준다는 근거는 아니다. 4.6 논문의 자료원은 Wikidata이며, 배포 페이지는 영문 위키백과 페이지 **유무**로 파일을 나눈다. 위키백과 본문 구절·revision·인용 occurrence까지 따라가는 PRD의 `Assertion`·`SourceUnit`·`EvidencePacket`을 YAGO가 제공한다고 확인할 근거는 없다. RDF* 제외 로그도 원문 주장과 독립 사료의 검토 원장을 대신하지 않는다.

4.6은 taxonomy/labels와 Wikidata 유래의 폭넓은 개체 연결을 제공하지만, 논문의 `Event` 110만 개체나 `BioChemEntity` 17.1만 개체 수는 **특정 작품의 1453–1600년·특정 지역·과학 공정·소사건 coverage**가 아니다. 역사 대상의 참여자·원인·이전/이후 상태와 위키 문단의 세밀한 사건을 어느 정도 담는지는 비교 표본 평가가 필요하다. 공식 labels sample에는 독일어·네덜란드어·프랑스어·중국어 등 다국어 라벨이 관찰됐고 해당 sample의 `@ko`/`한국` 검색은 0건이었다. 이 소표본으로 전체 한국어 또는 다국어 coverage를 판정하지 않는다([기계적 조사](../../data/research/yago-20260928/inventory.md)). [schema 웹페이지](https://yago-knowledge.org/schema)는 제목에 아직 `YAGO 4.5`라고 표시하므로 4.6의 버전 확정 스키마로 인용하지 않고 배포 ZIP·논문과 판을 대조해야 한다.

## 공개 생성 코드에서 확인한 추가 경계

아래는 [공식 생성 저장소](https://github.com/yago-naga/yago-4.6)의 **2026-09-04 main commit `5f84fa960fca294ad3784c974a78a127b21cd358` 코드 판독**이다. 2026-08-03 공개 ZIP이 이 커밋으로 빌드됐다는 증거와 정확한 tag는 확인되지 않았다. 따라서 공개 배포판의 실제 데이터 관측이나 live endpoint의 설정으로 등치하지 않는다.

| 확인한 코드 동작 | 프로젝트에 중요한 뜻과 근거 |
|---|---|
| `wdt:` 사실을 YAGO로 바꾸고, 일부 유형 생성에서는 normal 순위 진술도 사용한다. | `wdt:`는 속성별 최고 비폐기 순위 값이므로 preferred 진술이 있으면 normal의 역사적 값이 일반 사실 변환에서 빠질 수 있다. 일부 유형 생성만 normal 예외가 있다. ‘모든 Wikidata 진술·순위 보존’으로 해석할 수 없다. [Wikibase RDF 형식](https://www.mediawiki.org/wiki/Wikibase/Indexing/RDF_Dump_Format#Truthy_statements), [변환](https://github.com/yago-naga/yago-4.6/blob/5f84fa960fca294ad3784c974a78a127b21cd358/03-make-facts.py#L90-L129), [유형 예외](https://github.com/yago-naga/yago-4.6/blob/5f84fa960fca294ad3784c974a78a127b21cd358/03-make-facts.py#L158-L171) |
| 같은 주체·술어·객체의 첫 `p:/ps:` statement에서 `P585` 또는 `P580/P582`를 추출하며, 날짜 메타는 `onDate` 또는 시작/끝 한 쌍으로 출력한다. | 반복 재임 기간, 원 statement GUID·모든 qualifier·reference를 출력 원형으로 유지하는 계약이 아니다. [추출](https://github.com/yago-naga/yago-4.6/blob/5f84fa960fca294ad3784c974a78a127b21cd358/03-make-facts.py#L189-L215), [출력](https://github.com/yago-naga/yago-4.6/blob/5f84fa960fca294ad3784c974a78a127b21cd358/05-make-ids.py#L270-L276) |
| 날짜는 원 time precision 필드를 읽지 않고 `1월 1일`을 `gYear`로 바꾸는 휴리스틱을 쓴다. | PRD의 시간 정밀도·불확실성은 별도 원본 보존과 검토가 필요하다. [날짜 정규화](https://github.com/yago-naga/yago-4.6/blob/5f84fa960fca294ad3784c974a78a127b21cd358/03-make-facts.py#L342-L352) |
| `maxCount` 초과 값은 현재 코드에서 시작일 내림차순과 객체 문자열로 골라내며, 날짜가 달린 탈락 값은 로그 기록에서도 빠진다. 알려지지 않은 속성 및 일부 중복 라벨도 로그 밖이다. | 논문의 ‘제외 로그’를 **전체 원본 누락 원장**으로 사용할 수 없다. 역사적 경합 원자료는 Wikidata statement 판에서 보존해야 한다. [선택/로그](https://github.com/yago-naga/yago-4.6/blob/5f84fa960fca294ad3784c974a78a127b21cd358/03-make-facts.py#L482-L511), [미매핑 속성](https://github.com/yago-naga/yago-4.6/blob/5f84fa960fca294ad3784c974a78a127b21cd358/03-make-facts.py#L313-L325), [중복 언어 라벨](https://github.com/yago-naga/yago-4.6/blob/5f84fa960fca294ad3784c974a78a127b21cd358/03-make-facts.py#L513-L529) |
| 영문 위키 제목을 우선한 YAGO ID와 살아남은 주체의 Wikidata `owl:sameAs`를 출력한다. | 이름은 변경될 수 있으므로 프로젝트 ID는 판별도로 둔다. [ID 생성](https://github.com/yago-naga/yago-4.6/blob/5f84fa960fca294ad3784c974a78a127b21cd358/04-make-typecheck.py#L152-L178), [QID 연결](https://github.com/yago-naga/yago-4.6/blob/5f84fa960fca294ad3784c974a78a127b21cd358/05-make-ids.py#L252-L269) |
| 현재 `07-export.sh`는 QLever가 RDF* meta를 파싱하지 못한다는 주석과 함께 QLever 입력에서 meta를 제외한다. | 이 export recipe만 따를 때 SPARQL 본체에서 시간 주석 조회를 기대하면 안 된다. meta 별도 적재/변환이 필요하다. 실제 공개 서버의 설정은 미확인이다. [export script](https://github.com/yago-naga/yago-4.6/blob/5f84fa960fca294ad3784c974a78a127b21cd358/07-export.sh#L42-L61) |

2026-09-28 공개 [SPARQL 안내](https://yago-knowledge.org/sparql)의 endpoint에 George Washington 한 개체·선택 술어 8개·최대 10행으로 제한한 질의가 HTTP 200으로 답했다. 출생/사망 날짜·장소, 영국/미국 국적의 **6행**이 반환됐다([질의와 원 JSON](../../data/research/yago-20260928/endpoint-query-02.txt)). 질의한 직업 술어의 0행은 모든 직업 정보 부재의 증거가 아니다. 첫 sandbox 요청은 DNS 오류였고 두 번째 제한 요청만 성공했다([첫 시도](../../data/research/yago-20260928/endpoint-query-01.txt)). 서버 데이터 판본은 응답에서 확인되지 않았다. 한 요청의 네트워크 포함 0.924초와 서버 `query-time-ms: 21`은 처리량·대규모 질의 성능 지표가 아니다.

## 프로젝트 적용 가설과 남은 판정

**제안:** YAGO 4.6을 사람·장소·기관·사건의 시작 식별자, 상위 분류, 일부 구조화 관계의 **후보 골격**으로 시험한다. 공용 현실 릴리스의 사실 정본으로 자동 수입하지 않는다. 프로젝트가 요구하는 작은 사건/상태의 H, 시대 독립 지식 내용판 K, 인지·전달·보급·실행 B, 문장·인용·revision에 연결된 F는 고정 Wikidata 전체 statement/qualifier/reference와 위키백과 원문 span을 별도로 보존하고 Gemma/SOTA의 추출 후보에 정책 형식검사·독립 원문 표본 의미검토·고위험 병합/인과 별도 검토를 적용하는 경로가 필요하다. 이는 모든 후보의 전문가 개별 승인을 새로 요구한다는 뜻이 아니다. 이 구성은 [프로젝트 PRD](../prd/wikipedia-history-ontology.md)의 출처·시점·승인 계약에 맞추려는 **설계 가설**이며 YAGO 성능이나 비용의 실측 결론이 아니다. YAGO 식별자는 외부 참조로 보존하고 프로젝트 안정 ID 및 원문·Wikidata QID와의 대응판을 따로 관리해야 한다.

다음 판정은 자료를 고정한 작은 표본으로 한다. 작품 기간/지역에 맞는 인물·전쟁·조약·직위·과학 공정과 세부 사건을 뽑아 YAGO의 개체/속성/시간/메타 수록과 원 Wikidata statement·위키백과 근거를 나란히 대조한다. **존재 판정과 누락 판정의 분모**, 상충·반복 구간, 원문 출처 위치, 다국어 별칭, 잘못 붙은 인과를 각각 기록한다. 작은 표본 수락이 전체 1950년 이전 역사 릴리스나 집필용 `ReviewScope` 완료는 아니다. 공개 ZIP의 체크섬·내부 파일·압축 해제 및 DB 색인 규모, H200 처리 시간·메모리, endpoint와 배포판의 동일성은 아직 미확인이다.

## 배포 이용 조건과 출처

[4.6 배포 페이지](https://yago-knowledge.org/downloads/yago-4-6)와 [4.6 논문](https://suchanek.name/work/publications/iswc-2026-demo-yago.pdf) p.2는 데이터 라이선스를 CC BY로, [4.5 배포 페이지](https://yago-knowledge.org/downloads/yago-4-5)는 CC BY-SA로 기술한다. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)은 출처·라이선스 링크·변경 표시를 요구하고, [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)도 상업 이용을 허용하되 변형물 배포 때 ShareAlike 조건이 있다. 따라서 4.6의 변화는 **ShareAlike 조건 제거**로 설명하고 ‘4.6부터 처음 상업 이용 허용’이라고 쓰지 않는다. 외부 재배포 전에는 실제 선택 파일의 라이선스 표시를 다시 확인한다.

주요 1차 자료: [YAGO 공식 홈페이지](https://yago-knowledge.org/), [4.6 배포](https://yago-knowledge.org/downloads/yago-4-6), [4.6 ISWC 2026 demo paper](https://suchanek.name/work/publications/iswc-2026-demo-yago.pdf), [4.5 SIGIR 2024 paper](https://suchanek.name/work/publications/sigir-2024.pdf), [4.5 배포](https://yago-knowledge.org/downloads/yago-4-5), [공식 4.6 생성 코드의 고정 커밋](https://github.com/yago-naga/yago-4.6/tree/5f84fa960fca294ad3784c974a78a127b21cd358). 공개 배포 ZIP과 이 코드 커밋의 정확한 빌드 대응은 미확인이다.
