---
category_id: history-sot-mapping
lineage_id: lin-c300c56c-2475-41d8-b4d9-19a792468b74
document_id: doc-88a083c3-ffe9-46c8-acb8-cca0faaa971f
parent_lineage_id: null
abstract: 영어 위키백과 전체 입력을 위한 역사 SOT·CIDOC CRM 의미 영역, 원자 관계, 근거·작품 분기 및 커버리지 설계 매핑을
  검토할 때 읽는다.
version: 0.0.2
created_at: '2026-09-25T10:33:23.000000Z'
updated_at: '2026-09-25T10:35:05Z'
tags:
- 역사
- 위키백과
- 온톨로지
- CIDOC CRM
- SOT
canon: false
---
# 영어 위키백과 전체 입력을 위한 역사 SOT·CIDOC CRM 종합 매핑 설계

- 상태: **설계 작성·교차 검토 완료; 실행 미수행.** 아래 행과 사례는 실제 덤프 추출 결과, 전수 커버리지, 운영 DB 구현, 역사 사실의 채택을 증명하지 않는다. 새 매핑은 문서 DB에 등록하되 `canon=false`로 유지하며 역사표 승인·운영 적재와 구별한다.
- 우선 기준: [핵심 시스템 설계](../systems/README.md). [역사 SOT·온톨로지 조사 계획](20260924-history-sot-ontology-research-plan.md) 및 [기존 영어 위키 지식 적재 계획](20260914-enwiki-granite-knowledge-ingestion-plan-v0-1.md)의 목표를 넓은 입력 계약으로 구체화한다. 이전 계획의 SQLite 탐색·실험 제안은 운영 저장소 확정이 아니다. 운영 목표는 **PostgreSQL + pgvector**이고, 검색 인덱스는 재생성 가능한 파생물이다.
- 기준 외부 모형: [CIDOC CRM 7.1.3 공식 정의](https://cidoc-crm.org/sites/default/files/Documents/cidoc_crm_version_7.1.3.html), [동판 클래스·속성 선언](https://cidoc-crm.org/html/cidoc_crm_v7.1.3.html). 이 판의 의미에만 `E`/`P` 번호를 붙인다. 확장 모형은 의존판 검증 뒤 선택한다.

## 산출물과 읽는 법

| 파일 | 역할 | 이 문서에서의 경계 |
|---|---|---|
| [의미 영역 매핑](wikipedia-history-sot-mapping/semantic-domains.csv) | 59개 `SD-` 행: 영역·원문 패턴·지시 대상 경계·프로젝트 타입·CRM 정렬·시간·식별·근거 조건 | 백과 항목 전체를 한 클래스에 대응시키지 않고 한 항목 안의 서로 다른 대상을 분해한다. |
| [관계 매핑](wikipedia-history-sot-mapping/relation-mapping.csv) | 81개 `RM-` 행: 원자 술어, 양방향 CRM 경로/domain/range, 시간·한정자·출처·분기 | CRM과 동등하지 않은 프로젝트 관계는 `none`과 `project_extension`으로 드러낸다. |
| [원문 구조 매핑](wikipedia-history-sot-mapping/input-mapping.csv), [필드 라우팅](wikipedia-history-sot-mapping/field-routing.csv) | XML·wikitext 구조와 실제 후보 필드의 파서·의미 경로 | 실제 스냅샷별 template/module/alias 인벤토리 이전에는 후보 규칙이다. |
| [확장 정렬](wikipedia-history-sot-mapping/extension-mapping.csv), [입력·증거 계약](wikipedia-history-sot-mapping/ingestion-contract.md) | 확장·보완 온톨로지의 조건부 crosswalk와 손실 없는 입력·검토 계약 | 확장 모듈 전체를 자동 활성화하지 않는다. |
| [CRM 기본 어휘 등록부](wikipedia-history-sot-mapping/crm-base-registry.csv), [공식 소스 manifest](wikipedia-history-sot-mapping/crm-source-manifest.json) | 기준판 어휘와 원문 해시/취득 범위 | 등록부 수·사용 수·공식 표 수를 섞어 완전성의 대리 지표로 삼지 않는다. |
| [CRM 사용 어휘 대조표](wikipedia-history-sot-mapping/crm-usage.csv), [기계 검증 보고](wikipedia-history-sot-mapping/validation-report.json) | 최종 문서 등록 뒤 실제 사용 E/P 번호·방향·링크·파일 hash의 대조 결과 | 정적 검증의 실행 범위·결과는 해당 보고에서 확인하며 덤프 처리·성능·의미 검증과 구별한다. |
| [수락 사례](wikipedia-history-sot-mapping/acceptance-cases.json) | 9개 `AC-` 수작업 설계 fixture의 기대 동작·금지 추론 | 실제 위키 덤프에서 추출하거나 실행해 통과한 테스트가 아니다. |

`semantic-domains.csv`의 `crm_alignment`에 슬래시로 나열된 `E` 클래스는 문서 안에서 **분해할 후보 대상/대안**이다. 한 ID에 모든 타입을 일괄 부여하라는 뜻이 아니다. `crm_path`의 `A --P→ B`만 공식 정방향의 domain/range이며 세미콜론은 독립된 주장들을 나눈다. `relation-mapping.csv`의 `subject_project_type → predicate → object_project_type`은 입력·조회 방향이고, `crm_forward`가 `P…i`라면 공식 속성의 역방향을 쓰는 변환이다. 예를 들어 actor `member_of` group은 `P107i`이고 CRM 공식 정방향은 group `P107` actor다. `E74/P14/E7` 같은 방향 없는 축약을 유효 경로로 읽지 않는다. `P183`을 엄격한 선후에 쓰며 옛 `P120`을 새 적재 경로에 쓰지 않는다.
`crm_inverse=none`은 그 판에 공식 역방향 술어 URI가 없다는 뜻이다. DB에서 조건을 거꾸로 조회할 수 있음과 `P…i`라는 공식 속성이 존재함은 구별한다. 예컨대 P90의 역질의는 가능하지만 CRM 7.1.3의 공식 P90i는 없다.

지원 수준은 `direct`(판·입력 전제가 확정된 공식 관계 직접 적용), `conditional`(대상의 의미·문맥·domain/range를 확인한 뒤 정렬), `project_extension`(프로젝트 계약이며 CRM과 동등 선언 없음), `preserve_unmapped`(원문·위치·실패 이유를 지키고 의미 확정 보류)다. `direct`도 역사적 진실 확인을 뜻하지 않는다. 현재 영역과 대부분의 관계를 신중하게 `conditional`로 표기했다. 어느 수준이든 출처 주장과 SOT 채택은 별개다.

교차 검토는 Sol 설계 담당의 `SD-/RM-/AC-`/본문과 다른 Sol의 `IN-/EX-/FR-`/입력 계약을 서로 읽어, 형식상 ID 존재뿐 아니라 필드→술어의 **실제 의미·방향**을 대조했다. 치료법 설명을 실제 사용 P33으로, 종교 분포를 개인 실천으로, 직위 전후를 단순 재임으로 바꾸던 후보 링크를 분리·보류했다. 공식 CRM 7.1.3의 사용 관계 domain/range와 공식 inverse URI도 등록부와 대조했다. 이 수락 범위는 설계의 구조·의미 경계이며, 실제 dump template/alias 전수 조사·파서 실행·확장판 import·gold 평가·운영 적재는 포함하지 않는다.

## 추출 단위와 대상의 분해

영어 위키백과의 한 페이지는 실체 하나가 아니다. 문단·표셀·인포박스 필드·주석·목록 항목의 각 **원문 span**에서 지시 대상을 먼저 찾고, 그 뒤 독립 객체·역사 발생·그것을 설명하는 주장 중 어디에 해당하는지 라우팅한다. 종교 페이지에서도 전통의 이름, 교리 내용, 경전 표현판, 교단 조직, 의례 사건, 후대 연구자의 평가를 별도 레코드로 만든다. 과학 페이지에서도 자연 현상, 수학적 서술, 시대별 이론판, 발견/발표 활동, 실제 기술 사용이 구별된다. 목록·개념 페이지·모호성·넘겨주기는 그대로 대상의 진실 집합이 아니며 항목별 후보와 탐색 힌트다. 역사 문장에 등장한 ‘없었다’는 명시적 부정 주장이고 검색 실패는 미상이다.

| 지시 대상 묶음 | 주요 `SD-` 행 | 경계와 CRM 정렬의 핵심 |
|---|---|---|
| 사람·집단·정치 | `SD-PEOPLE-01..03`, `SD-GROUP-01..02`, `SD-POLITY-01..04` | E21 사람, E74 집단/조건부 국가 행위체, E53 영토를 분리한다. 국호·왕조·정권·주권·직위의 동일성을 이름에서 추론하지 않는다. 권한/관할/계승은 프로젝트 관계로 판과 유효기간을 보존한다. |
| 법·경제·인구·분쟁·외교 | `SD-LAW-01..02`, `SD-ECON-01..03`, `SD-WAR-01..02`, `SD-DIP-01..02` | 규범 내용과 제정/시행, 거래/권리 이전과 가격·인구 집계, 전쟁 상위 사건과 전투, 조약문과 체결/인정 행위를 가른다. 통계는 E54 수치만이 아니라 분모·대상·기간·측정법을 요구한다. |
| 지리·시설·물질·유물 | `SD-GEO-01..03`, `SD-OBJECT-01`, `SD-MATERIAL-01..02` | 장소 E53, 실제 시설/제작물, E57 재료 유형, 자원·표본 개체는 별개다. 경계는 시점과 지도판이 붙은 프로젝트 관계다. 부품 P46과 상징 내용 P106을 혼동하지 않는다. |
| 기술·과학·수학 | `SD-TECH-01..03`, `SD-SCI-01..03`, `SD-MATH-01` | E55 일반 기술, E29 문서화된 설계, E89 이론 명제, E73 표현판과 E7/E12 실제 활동을 나눈다. 자연 법칙 자체를 인간이 창안한 E28로 단정하지 않는다. 수학의 추상 대상은 프로젝트 객체이며 CRM `E28` 동등 매핑을 보류한다. |
| 생물·질병·의학·자연 | `SD-BIO-01..02`, `SD-DISEASE-01..02`, `SD-MED-01`, `SD-NATURE-01`, `SD-ASTRO-01`, `SD-CLIMATE-01` | 분류군 E55와 개체/표본 E20 계열, 질병 유형과 환자/발병, 치료법과 임상행위, 자연 사건/기후 집계/천체를 분리한다. 관찰·진단·원인 이론의 판을 남긴다. |
| 종교·사상·언어·문화 | `SD-REL-01..04`, `SD-IDEA-01..02`, `SD-LANG-01..02`, `SD-LIT-01`, `SD-ART-01`, `SD-MEDIA-01`, `SD-SPORT-01` | 교리/이데올로기 내용과 그 시대의 정식화·수용·전파·실천을 분리한다. 경전/번역/사진/작품의 표현판·매체와 조직·공연·경기를 구별한다. 종교 전체를 단일 E89로 만들지 않는다. |
| 가상·문서·시간·정량·미해석 | `SD-FICTION-01`, `SD-LIST-01..03`, `SD-SOURCE-01`, `SD-TIME-01`, `SD-QUANT-01`, `SD-UNKNOWN-01` | 가상 인물은 원역사의 실존 E21이 아니다. 문서 내용과 그 문서의 사실 주장, 사건 시점과 편집/출판 시점을 분리한다. 미지원 template은 원형과 좌표를 보존한다. |

독립 지식 객체는 원역사 연표에 최초 등장 사건이 없거나 그 시점이 미상이어도 식별·조회할 수 있다. 객체에 임의 발생연도를 붙이지 않는다. 다만 **인간이 만든 이론판·교리 해석판·발명된 절차**의 정식화·발표·번역·전파에는 E65/P94 등 해당 역사 활동과 시각·장소·행위자·방식·출처가 붙을 수 있다. E28의 ‘지적 산물’은 초시대적 진리의 증명이 아니며, 물리 법칙 자체와 그 법칙을 말한 명제는 다르다. 국가를 행위체·영토·권한판으로, 생물 종을 분류 개념·실물 개체로, 신앙을 교리·문헌·기관·실천으로 분해하는 이유가 여기에 있다.

## 관계와 시간의 적용 계약

`relation-mapping.csv`의 각 행은 의미가 하나인 술어다. 출생/사망 `E67 --P98→ E21`, `E69 --P100→ E21`, 집단 성립/해산 `E66 --P95→ E74`, `E68 --P99→ E74`, 가입·이탈 `E85/E86`의 사건 경로를 단순 현재 소속 `P107`과 구별한다. 물리 소유권 이전은 `E8`의 양도자 `P23`, 양수자 `P22`, 대상 `P24`를 결합하고, 단순 현재 소유 `P52`와 실제 점유·이동을 합치지 않는다. `P4 → E52`의 시기와 `P81` 확실한 지속 내부/`P82` 가능한 외부 범위를 원문 정밀도에 맞게 사용한다. `P183`은 기간이 겹칠 수 있으면 생성하지 않는다.
장소 포함 `E53 --P89→ E53`, 실물의 기준시점 현재 위치 `E19 --P55→ E53`, 사건 발생 장소 `E4 --P7→ E53`도 서로 다른 술어다. 수도·최대 도시·좌표·조직 상위기관·제휴는 고유한 프로젝트 관계로 보존하며 재임·사건 장소·회원 관계에 억지 연결하지 않는다. 필드의 형식 ID가 존재하는지만 확인하지 말고 **술어의 의미와 방향**이 맞는지 교차 검토한다.

지식의 **인지**(`knows_content`), 수행 **숙련**(`has_procedural_skill`), 지역·자원이 갖춰진 **실행 가능성**(`can_execute_here`), 실제 행위 `P16`/`P33`, 완성 실물 `P108`, 전파(`transmitted_content`)와 수용(`adopted_interpretation`)은 각각 다른 증거를 요구한다. `P33`은 E7 Activity가 E29 특정 절차를 실제 사용한 관계다. E11 Modification은 가능한 E7 하위 사례이며, 단순 인지나 필요조건은 `P33`이 아니다. `P16`도 단순 ‘알고 있었다’를 뜻하지 않는다. `P15`는 넓은 영향 관계이지 `causes_event`의 인과 입증이 아니다. 원인 가설·필요조건·사건의 상태 변경은 프로젝트 관계이고, 시간순·문서 링크·벡터 유사성만으로 자동 확정하지 않는다. 사회 일반화를 보편 인과 법칙으로 올리지 않는다.

모든 assertion은 원문 주장/외부 문헌 사실/모델 해석/작품 설정/후보 발명 및 검토·릴리스 상태를 별개 축에 보존한다. E13의 P140/P141/P177은 귀속 대상을 표현하지만 주장이 참인지, 상충에서 어느 판을 채택했는지, 작품에서 공개됐는지 결정하지 않는다. 각 관계의 역할·유효기간·수량·단위·부정·불명·다중값·상충 주장·귀속 화자·원문 span을 별도 한정자로 기록한다. 출처가 하나라도 빠진 관계는 SOT 릴리스 대상이 아니다.

원문 좌표는 최소 `wiki/site + snapshot/export family + shard hash + page_id + revision_id + slot + raw span + citation/reference occurrence`를 갖고, 변환된 표현마다 parser/crosswalk 판과 원문 역매핑을 보유한다. 명칭·QID·redirect는 동일성 **후보**이고 자동 병합 키가 아니다. 안정 ID는 원문 위치/정규화 주장/대상 식별의 서로 다른 네임스페이스에 부여한다. 같은 snapshot·revision·span·parser판·규칙판 재처리는 멱등이어야 하고, 규칙판 변경 시 원래 assertion을 수정하지 않고 새 파생판과 차이를 남긴다. 표·템플릿의 알 수 없는 값은 `preserve_unmapped` 큐의 원형·실패 이유·재처리 상태로 남는다.

## 원역사와 작품 분기 조회

공용 원역사 출처와 검토된 assertion 릴리스는 불변 기준선이다. 작품은 `work_id/branch_id`를 가진 변경 전표로 원역사 ID를 참조하고 유지·변형·취소·지연·대체를 별도 기록한다. 작품의 주인공이 미래 지식을 안다는 설정은 공용 개념 객체를 참조하는 작품 **인지 전표**다. 청동기시대 철기 도입 사례에서는 지식 내용, 문서화된 공정, 그 지역 재료·설비·노동·권한, 실제 시제품/생산, 지역 전파를 따로 조회한다. `안다 → 생산 가능 → 세계적 보급`을 자동 연쇄시키지 않는다. SOTA는 필요조건의 충족·부족·충돌·미확인을 역산해 중간 사건 후보를 만들고 정방향으로 검토한다. 작가가 역사표를 승인·잠근 뒤 Gemma가 그 제약을 받아 장면을 집필한다. 재미를 위한 개변 선택은 작가 권한이며 계산기가 승인하지 않는다.

기획 조회에는 개념·원리·가능한 미래 지식이 기간 밖이어도 검색될 수 있다. **인물 시점 조회**에는 해당 인물이 언제 무엇을 어떤 경로로 알았는지, 당시 지역에서 무엇을 쓸 수 있었는지, 작품 설정과 공개 상태를 필터로 적용한다. 출처 작성일이 현대라고 과학 원리를 검색에서 버리지 않지만, 그것을 과거 인물의 자동 지식으로 바꾸지도 않는다. 같은 객체를 공용 원역사와 여러 작품이 참조할 수 있어도 작품의 인지·사건 전표는 작품 간 전이하지 않는다.

## 전체 덤프 적용 순서와 완료 판정

1. **스냅샷 확정:** export family/current 대 history, site, 파일 manifest·SHA-256, 압축/XML 건전성, namespace/page/revision/slot 분모를 실제 파일로 검증한다. 파일명이나 파일 개수만으로 완료를 선언하지 않는다. 원문은 불변으로 보존한다.
2. **구조 전수 등록:** 모든 범위의 page/revision/section/table/template/reference/span을 등록하고 파서 실패를 원형 그대로 큐에 둔다. 이 단계에서 의미 추출은 선택 영역 밖이어도 원문 좌표가 남아야 한다.
3. **의미 후보 생성:** 원문 구조→`IN-`/필드 규칙→`SD-` 객체 경계→`RM-` 원자 관계 순으로 후보와 증거를 만든다. 한 페이지에서 독립 지식과 시대 사건을 동시에 뽑는다. 불명·부정·상충은 묵살하지 않는다. `EX-` 정렬은 고정된 의존판에서만 활성화한다.
4. **검토·릴리스·질의:** 타입/domain/range·시간/출처·동일성·충돌을 검사하고 범위가 명시된 원역사 assertion 릴리스를 만든다. 키워드·pgvector는 원문/릴리스에서 재생성한다. 첫 의미 추출과 의미 검토의 좁은 사례는 문종 죽음→단종 즉위의 앵커 쌍과 관련 시대·지역으로 시작한다. 이는 검증 cohort일 뿐 전체 분야의 필드·의미 매핑 목표를 줄이지 않으며 독립 지식 전체를 그 기간으로 잘라내지 않는다.
5. **확장 판단:** 파일럿의 누락·오매핑·검토비용을 본 뒤 영역·템플릿·언어 범위를 넓힌다. 분야별 원문 표본에서 precision/recall과 금지 추론, 재추출 멱등, 질의 누수를 별도로 평가한다. `acceptance-cases.json`은 우선 설계 fixture이며 실제 gold 근거 span으로 대체되어야 실측 검증이다. 앵커의 중간 사건·정답 서술을 입력과 검색 후보에서 가리는 blind split을 만들어 복원 품질과 정답 누수를 따로 확인한다.

커버리지 분모는 검증된 `snapshot_id`의 XML **page/revision**, 발견된 구조 occurrence(표셀·필드·본문 span·ref 등), 파싱된 의미 후보, 독립 평가 표본을 각각 따로 센다. 분자는 구조 정상 처리, `preserve_unmapped` 보존, parser 실패, 후보 생성, 출처 완비, 검토 채택/기각/보류/충돌을 구분한다. `mapped + lossless-unmapped + explicit-parser-failure = inventoried eligible units`를 해당 구조 단위에서 검사하되, 이 등식이 의미 정확도·전체 위키의 사실 수용을 증명하지는 않는다. 실제 템플릿별 alias·Lua 모듈·revision 분포를 조사하지 않았으므로 현재의 59/81행은 **설계 범위**이며 실제 모든 필드의 의미 커버리지가 아니다. 숫자로 행을 부풀려 빈 영역을 덮지 않고, 검토되지 않은 의미는 근거와 함께 미매핑으로 보존한다.

인포박스를 공통 타입으로 정규화하고 `TemplateMapping`·조건부 매핑·값 파서를 분리한 [DBpedia ontology/mapping](https://www.dbpedia.org/resources/ontology/)과 [DBpedia mapping 지침](https://mappings.dbpedia.org/index.php/How_to_edit_DBpedia_Mappings)은 어댑터 설계의 선례다. 그 매핑이 CRM과 동등하거나 사실 검증이 끝났다는 뜻은 아니다. 실제 재사용에는 dump/template snapshot, 라이선스, 이 프로젝트의 원문 span·CRM 교차표를 별도 고정한다.

독립 검토에서 확인할 미결정은 ① 전체 snapshot의 공식 manifest·범위 및 리비전 정책, ② 분야별 동일성 병합 임계와 복합 객체의 ID 정책, ③ 템플릿판·필드 alias 실측 뒤의 라우팅 우선순위, ④ 확장 모형 import/판 호환성, ⑤ 릴리스별 검토 표본과 합격 기준, ⑥ 작품별 인지·권한 자료의 결핍을 어떻게 명시할지다. [CRMinf 1.2.1](https://cidoc-crm.org/extensions/crminf/html/CRMinf_v1.2.1.html)와 [CRMsci 3.2](https://cidoc-crm.org/extensions/crmsci/html/CRMsci_v3.2.html)는 CRMbase 7.1.3과 서로를 참조하지만 [CRMdig 5.0](https://cidoc-crm.org/sites/default/files/CRMdig_V5.0.pdf)은 CRMsci **3.1** 의존이므로 3.2와의 동시 활성화는 호환성 검토 전 보류한다. 설계 검토가 끝나기 전에는 `canon=true` 채택, 덤프 적재, 역사표 승인, 실제 성능·커버리지 완료 주장을 하지 않는다.
