---
category_id: history-sot-mapping
lineage_id: lin-1dee6c30-41dd-4fa1-b907-a77a7b19b589
document_id: doc-8c171388-904d-4ea1-8a7c-9e1d7eef83e4
parent_lineage_id: null
abstract: 위키백과 XML·wikitext·보조 입력의 구조 추출, 원문 좌표, 주장 지위, 시간·분기 및 손실 없는 보존 계약을 검토할 때
  읽는다.
version: 0.0.1
created_at: '2026-09-25T10:33:29.000000Z'
updated_at: '2026-09-25T10:33:29Z'
tags:
- 역사
- 위키백과
- 입력
- 근거
canon: false
---
# 위키피디아 덤프 입력·증거 보존 계약

이 문서는 전체 덤프의 **입력 구조를 빠뜨리지 않고 분류하는 설계 계약**이다. 실행 완료 기록이나 전수 의미 매핑 선언이 아니다. `input-mapping.csv`(원문 구문), `field-routing.csv`(분야별 필드), `extension-mapping.csv`(기본·확장 모형)를 함께 적용한다. 각 행의 `mapping_id`/`field_id`는 설계 식별자이며 `semantic_domain_id`, `relation_id`, `case_id`는 형제 표와의 교차 키다. `*`는 아직 특정 관계·사례에 묶이지 않은 공통 규칙이지 모든 분야에서 의미가 확정됐다는 뜻이 아니다. 지원 수준 `direct`, `conditional`, `project_extension`, `preserve_unmapped`는 각각 원형 직접 적용, 문맥·검토 뒤 적용, 프로젝트 전용 명세, 원문 보존·매핑 보류를 뜻한다. 프로젝트 술어와 클래스는 CIDOC CRM 클래스·속성과 동등하다고 선언하지 않는다.

## 입력 경계와 판 고정

영어 위키피디아 **XML content export의 지정 날짜·export family·site**를 먼저 고정한다. [Wikitech export 문서](https://wikitech.wikimedia.org/wiki/MediaWiki_Content_File_Exports)에 따라 current export와 모든 revision history export는 다른 자료이며 `SHA256SUMS`는 압축 shard 검증의 선언 목록이다. 파일명의 페이지/리비전 범위는 관찰된 XML 범위와 대조해야 한다. 보유 폴더의 파일 개수나 `_SUCCESS`만으로 전체성·현재성을 확정하지 않는다. 실제 큰 파일의 SHA-256·압축 건전성·XML 파싱·페이지 분모 검증은 아직 수행되지 않았다. 사이트의 최신 상태도 이 스냅샷과 구별한다.

압축 shard의 **SHA-256**, 압축 해제 XML 바이트의 해시, 각 revision의 원문 wikitext/slot 텍스트 해시, XML 내부에 선언된 text `sha1`을 서로 다른 필드로 저장한다. 선언 해시의 인코딩 정의와 검증 방법도 기록한다. 원본은 불변으로 두고 파생 HTML·정규화 텍스트·후보 주장에는 `snapshot_id/wiki_id/page_id/revision_id/slot_role/shard_id/raw_xml_byte_range/raw_text_byte_range/source_url/revision_url`을 첨부한다. XML 엔터티 해제, Unicode 정규화, 공백·markup 제거, 템플릿 전개, 문장 분할은 각각 이름·버전·입출력 해시와 **정규화 범위→원문 복수 범위** 변환표를 남긴다. 정확한 원문 위치로 역추적되지 않는 후보는 SOT 릴리스에 넣지 않는다. 텍스트·각주가 가리키는 저작물·참조 미디어·보조 데이터마다 판별 가능한 출처와 권리/라이선스 메타데이터를 별도로 기록한다. URL만 참조한 자료와 실제 원문 바이트를 확보한 자료도 구별하며 하나의 덤프 라이선스를 모든 외부 자료에 전파하지 않는다.

[MediaWiki Export](https://www.mediawiki.org/wiki/Help:Export)의 XML 스키마 URI와 실제 `siteinfo`, namespace, page, revision, slot, model/format를 선행 스캔해 파서를 선택한다. 단일 페이지=단일 revision, 모든 본문=wikitext, 제목=불변 ID를 가정하지 않는다. contributor는 공개된 최소 편집 메타데이터만 보존하고 역사 행위자로 승격하지 않는다. 숨김·삭제 내용은 복원하려 하지 않고 접근 불가 상태로 남긴다. 압축·XML 오류, 미지원 content model, 미해결 transclusion, 인용 표기 오류는 원문/좌표/원인/단계가 있는 lossless queue로 보낸다.

## 렌더링과 의미 분리

[Parsoid API](https://www.mediawiki.org/wiki/Parsoid/API)와 [HTML 출력 규약](https://www.mediawiki.org/wiki/Specs/HTML)의 DOM/source-range·`data-mw`는 템플릿 전개와 구조 복원에 쓸 수 있는 후보 경로다. 그것이 모든 wikitext 또는 extension tag의 완전한 원문 좌표를 보장한다는 가정은 금지한다. 섹션→문단→문장, 표→행/열/헤더/셀, 목록→항목, `<ref>`→정의/재사용/`<references>`를 순서와 중첩까지 보존한다. infobox, 일반 template, parser function, Lua module, category, hatnote, disambiguation, internal/interwiki/external link, 파일·SVG·수학·화학 표기는 각기 다른 구조로 기록한다. 템플릿이나 category의 이름과 필드명을 CRM 클래스·관계로 곧바로 해석하지 않는다. 문장·표셀·주석의 **문맥, 부정·추측, 인용자, 단위, 시간 역할, 출처 범위**를 갖춘 뒤에만 주장 후보를 만든다. [Cite 확장](https://www.mediawiki.org/wiki/Help:Cite)의 재사용된 named reference와 reflist도 개별 주장에 다시 연결한다.

`field-routing.csv`는 분야별 검토 가능한 변환 설계다. `Infobox person|birth_date` 같은 selector는 **후보 바인딩**이며 실제 덤프의 template 판·별칭·모듈 의존성·대상 namespace를 인벤토리한 후 snapshot별 registry로 확정해야 한다. 한 필드의 값이 날짜·역할·국가·장소 중 무엇인지 template 이름, 문서 유형, 필드 조합, 주변 텍스트/표 헤더, 값 파서를 함께 판별한다. DBpedia의 [template mapping 편집 방식](https://mappings.dbpedia.org/index.php/How_to_edit_DBpedia_Mappings)은 이 조건부 어댑터의 선례일 뿐, 그 매핑을 영어 위키 덤프에 그대로 채택한다는 뜻은 아니다. 후보 field row가 있다는 사실을 운영 지원 완료로 계산하지 않는다.

선택 보완 입력인 `page_props`의 `wikibase_item`, Wikidata QID/진술/qualifier/rank/reference/sitelink, SQL `redirect`, `categorylinks`, `linktarget`는 **현재 XML 덤프에 내재한 데이터가 아니며 보유·적재가 확인되지 않았다**. 도입하면 각 덤프·SQL 판과 join 키를 다시 검증한다. Wikidata의 [진술 데이터 모델](https://www.wikidata.org/wiki/Help:Data_model)에서 qualifier와 rank는 주장 범위를 바꾸고 `somevalue`/`novalue`는 서로 다른 상태다. 보조 자료가 없어도 원문 XML 기반 후보는 보존되지만 QID나 구조화 진술은 추측하지 않는다.

## 시간, 주장, 분기

원문 편집 시각·자료 수집 시각·주장 기록/검토 시각·사건 발생 시각·상태 유효 기간·행위자가 알게 된 시각·작품 분기 기준 시각을 각기 다른 축으로 유지한다. 부정확한 연대, 다른 달력, 기원전, `circa`, 열린 구간은 원문과 해석 경계를 모두 저장한다. [Wikidata 날짜 규약](https://www.wikidata.org/wiki/Help:Dates)도 선택 보완 자료의 달력/정밀도 해석에만 쓰고 XML의 날짜를 Wikidata 값으로 대체하지 않는다. CRM의 `E52 Time-Span`과 `P81`(확실한 내부), `P82`(가능한 외부)는 지원 가능한 역사 시간 주장에만 사용한다. 사건 part-of와 전후 관계는 인과와 구별한다.

각 후보 주장은 `assertion_id`, 술어/대상, 긍정·부정·불명, 귀속 화자, **basis**(`historical_evidence`, `attributed_source_claim`, `interpretation`, `model_hypothesis`, `author_setting`, `fiction`), 출처 revision/span/citation, 추출기 버전, 유효 시간, 검토 상태, scope를 가진다. 상충하는 날짜·정체성·원인·수치를 하나로 덮지 않고 경쟁 주장으로 남긴다. 사람의 지식·지역의 지식 가용성·실제 자원/공정 역량은 서로 다른 조건이다. 시간여행 인물의 조기 지식은 명시적 `author_setting`과 `work_id/branch_id`에서 허용하되, 그것만으로 자원·기술적 가능성이 증명되지는 않는다. 작품 분기의 가상 사건은 공용 역사 SOT에 역류시키지 않는다. 릴리스는 범위·원문 스냅샷·매핑/모형 판·수락 주장 버전·검토 결정을 고정한다.

## 모형 판과 활성화

기본 교차표는 [CRMbase 7.1.3](https://cidoc-crm.org/html/cidoc_crm_v7.1.3.html)이다. [CRMinf 1.2.1](https://cidoc-crm.org/extensions/crminf/html/CRMinf_v1.2.1.html)은 근거·신념·논증에, [CRMsci 3.2](https://cidoc-crm.org/extensions/crmsci/html/CRMsci_v3.2.html)은 실제 과학 관측/추론 기록에, [CRMdig 5.0](https://cidoc-crm.org/sites/default/files/CRMdig_V5.0.pdf)은 디지털 파생·실행 추적이 필요한 경우에만 선택한다. CRMinf 1.2.1과 CRMsci 3.2는 각각 CRMbase 7.1.3 및 서로의 판을 참조한다. CRMdig 5.0은 CRMbase 7.1.3과 **CRMsci 3.1**에 의존하므로 CRMsci 3.2와의 동시 활성화는 클래스/속성·import 충돌을 확인하기 전까지 보류한다. CRMsci 3.2의 `S5 Inference Making` 설명과 상속/FOL 표기의 불일치도 자동 `owl:equivalentClass` 생성 없이 의미 대조 항목으로 남긴다. model file/hash/import matrix와 지역 crosswalk 테스트를 통과한 조합만 `enabled`가 된다. 문서에 후보로 나온 모든 확장을 강제 로드하지 않는다.

[LRMoo 1.0](https://cidoc-crm.org/extensions/lrmoo/html/LRMoo_v1.0.html)은 작품·표현·발행형 구별, [SKOS](https://www.w3.org/TR/skos-reference/)는 통제 개념/이름, [QUDT catalog](https://www.qudt.org/catalog/qudt-catalog.html)는 측정량·단위, [GeoSPARQL 1.1](https://docs.ogc.org/is/22-047r1/22-047r1.html)은 명시적 공간기하 질의가 필요할 때의 선택 후보일 뿐이다. 수학·화학·분류군 동등성도 별도 권위 자료와 판 고정 전에는 원문식/별칭 후보로 보존한다.

## 손실·범위 계측과 수락

전체 코퍼스의 분야별 의미 매핑이 목표다. 전역 처리의 첫 단계는 원문 보존과 page/revision/structure 카탈로그이며, 앵커·시대·지역은 변환·추론 품질을 검증할 **첫 수락 표본**이다. 첫 표본 밖 항목도 범위 제외로 종료하지 않고 `deferred_by_wave` 큐에 남겨 분야별 처리 wave로 확대한다. 비용이 큰 사건·상태·관계 의미 추출, 검토, 벡터 색인은 이 표본의 품질·처리량·디스크·비용 결과를 기준으로 단계별 확대한다. 섹션·문단·문장·표·행·셀·template 호출/필드·reference occurrence·link·media/math/chemical 태그별로 **발견 분모**와 파싱 성공·lossless queue·실패·평가제외 분자를 모두 남긴다. 주장/관계는 `후보로 생성된 수`를 분모로 `근거 연결`, `시간/객체 판별`, `검토 수락`, `충돌/보류`를 따로 센다. 원문 전수 보존률과 의미 추출 정확도/재현율을 혼동하지 않는다. 샘플로 처리량·디스크·검토비용을 재고 확장 예산과 합격 기준을 정한다. 합격 수치나 전체 인포박스 필드 커버리지는 아직 설정되지 않았다.

현재 설계 fixture는 형제 `acceptance-cases.json`의 `case_id`로 교차한다. 실제 실행용 수락 표본에는 **추가로** 같은 제목의 리비전 차이, HTML 정규화→원문 역추적, 표셀의 헤더/주석/단위, 같은 named ref 재사용, 미지원 template의 무손실 보류를 포함해야 한다. 이미 제시된 설계 사례에서도 편집 시각과 사건 시각, 논쟁적 연대, part-of와 cause, 앵커 인물의 당대 지식, 명시적 시간여행 설정과 자원 부족, 작품 분기와 공용 역사를 원문 근거로 검증해야 한다. 실제 앵커 복원 평가에서는 중간 사건과 정답 서술을 검색·입력에서 가린 blind split을 사전 정의해야 한다. 이 문서 작성 시점에 실제 덤프를 실행하거나 이러한 사례를 통과시켰다는 뜻은 아니다.
