# 역사 SOT·온톨로지·벡터 검색 조사 출처 지도

기준일·확인일: 2026-09-24. 목적은 현재 계획을 위한 좁은 사전 조사다. 아래는 공식 문서에서 확인한 기술 동작과 로컬 파일 메타데이터이며, 다운로드 완료·검증, 배포 설계 확정, 구현, 벤치마크 완료를 뜻하지 않는다. 페이지 본문을 전재하지 않고 각 출처의 계획상 함의만 요약했다.

## 관찰된 사실

### 로컬 덤프 메타데이터

사용자는 `wiki-dump/`에 이미지·영상 없이 텍스트 기반 XML을 bzip2 압축한 덤프 전체를 다운로드했다고 확인했다. 로컬 파일명·크기 재집계에서도 2026-09-01자 enwiki current 이름의 `.xml.bz2` 19개, 총 46,445,603,916 bytes(46.45 GB, 43.26 GiB)가 일치했다. `SHA256SUMS`(2,097 bytes)와 `_SUCCESS`(0 bytes)도 존재한다. 이번 확인은 파일 목록·크기만 대상으로 했으며, checksum 검증 및 파서 호환성 확인은 미실행이다.

공식 Wikimedia 안내는 배포 완결을 확인하는 `SHA256SUMS` 존재와, 내려받은 각 파일의 checksum 검증을 구분한다. 이 프로젝트는 다운로드 완료(사용자 확인 및 파일 목록·총량 일치)가 된 상태이며, checksum 검증은 별도 미실행 항목이다. [MediaWiki Content File Exports](https://wikitech.wikimedia.org/wiki/MediaWiki_Content_File_Exports)

### 원자료·파싱

MediaWiki Content File Exports는 공개 위키의 **비파싱 콘텐츠**를 압축 XML로 제공하며, `current`는 월간 배포 시점의 각 페이지 최신 revision, `history`는 전체 revision 이력이다. 과거 XML 생성 경로는 deprecated로 안내된다. 원시 snapshot을 불변으로 보관하고, 파싱 산출물·검색 구간은 원자료 revision과 위치를 가리키는 파생 표현으로 두는 것이 자료 경계를 유지한다.

MediaWiki의 Parsoid API는 wikitext를 MediaWiki DOM 규격의 HTML/XHTML+RDFa로 변환하며 pagebundle 표현도 문서화한다. 파싱은 단순 텍스트 정제와 같지 않으므로 제목·절·표·링크·주석·참고문헌·원문 오프셋을 보존할 수 있는 표현과 파서 버전을 계획에서 다뤄야 한다. 이 문서만으로 오프라인 덤프 전체를 처리하는 특정 라이브러리나 완전성은 선택되지 않는다. [Parsoid API](https://www.mediawiki.org/wiki/Parsoid/API)

### 식별자·시간·출처 주장

Wikidata의 모델은 item과 property를 사용하며, statement에 qualifier를 붙여 범위·조건·시기 등을 기술하고 reference를 통해 근거 출처를 연결한다. 시작·종료 시점 같은 시간 qualifier가 실제 적용 기간을 제한할 수 있고, qualifier 중 일부는 의미 범위를 바꾸므로 소비자가 무시해도 된다고 일반화할 수 없다. Wikidata QID는 연결 후보 식별자로 유용하지만, 프로젝트의 사건 ID·주장 ID를 대체하거나 개별 주장의 진실·수락 상태를 보증하지 않는다. [Wikidata Data Model](https://www.wikidata.org/wiki/Help:Data_model)

### 역사 사건·출처이력·검증

CIDOC CRM은 역사 서술을 위한 사건 중심 개념 모델의 예다. 시간에 걸쳐 일어난 과정(E2 Temporal Entity), 사건 하위 유형, 지속물, 시간 범위와 관련을 표현한다. 사건, 인물·장소의 상태, 기술의 발견·전파·보급을 시간·행위·영향 대상으로 나눠 표현하는 설계 후보를 검토할 근거는 되지만, 전체 CRM 채택이나 특정 관계 집합의 확정 근거는 아니다. 인과 주장은 단순 시간 순서나 참여 관계와 구별되어야 한다. [CIDOC CRM 7.1.3](https://cidoc-crm.org/sites/default/files/Documents/cidoc_crm_version_7.1.3.html)

W3C PROV-O는 Entity·Activity·Agent 및 생성·사용·파생·책임 관계로 데이터 산출과 변환의 계보를 표현한다. 원문 snapshot → 추출 후보 → 검토된 assertion → 릴리스와 검색용 임베딩의 출처 사슬을 기록하는 데 적용 가능하다. PROV provenance는 그 자체로 역사 주장에 대한 진실 판정이 아니다. [PROV-O](https://www.w3.org/TR/prov-o/)

W3C SHACL Recommendation은 RDF 데이터 그래프가 정해진 shape·제약을 만족하는지 표현·검증하는 표준이다. RDF 그래프로 모델링할 경우 필수 식별자·시간값·출처 연결 같은 구조 검증 후보가 된다. 이는 사료 평가나 인간의 의미 검토를 대신하지 않는다. [SHACL](https://www.w3.org/TR/shacl/)

### PostgreSQL·pgvector 검색

pgvector는 PostgreSQL의 정확 최근접 검색과 HNSW/IVFFlat 근사 검색을 제공하며, 근사 인덱스는 속도와 재현율의 절충이다. 일반 `WHERE` 조건 필터는 근사 인덱스 탐색 후 적용될 수 있어 필터 선택도·반환 부족을 고려해야 한다. 별도의 필터 컬럼 인덱스, iterative scan, partial index 또는 partitioning은 조건과 규모에 따라 검토할 옵션이지 이번 조사만으로 채택할 설정은 아니다.

공식 README는 PostgreSQL full-text search와 pgvector를 함께 쓰는 hybrid search와 Reciprocal Rank Fusion 또는 cross-encoder 조합 예를 제시한다. 따라서 관계·기간 필터 및 키워드 후보 검색과 벡터 후보 검색은 같은 PostgreSQL 목표 안에서 결합해 검토 가능하다. 검색 결과 순위·인과 해석·역사적 타당성은 별도 검증 대상이다. [pgvector README](https://github.com/pgvector/pgvector)

## 계획에서 확인할 질문

1. **역사 SOT의 단위:** 원자료는 불변 보존하고, 어떤 최소 단위의 `reviewed assertion`을 구조화 원역사 릴리스에 수락할지 정한다. assertion마다 출처·revision·정확한 문서 구간, 원문 주장과 추출자 해석 구별, 검토 상태, 수정·철회 이력을 어떻게 연결할지 결정한다. raw Wikipedia 문서 그 자체를 사실 SOT라고 부르지 않는다.
2. **두 번째 원역사와 창작 분리:** 출처가 말하는 주장, 모델이 추론한 관계, 미확정/상충 판단, 작품의 역설계·Backfilling 창작을 별도 지위로 두고 원역사 릴리스로 역류하지 않도록 한다. 계획의 승인·잠금 규칙은 [핵심 시스템 설계](../systems/README.md)를 따른다.
3. **온톨로지의 범위와 시점:** 초기 핵심 개념(사건, 인물·기관, 장소, 상태, 기술·조건, 주장, 출처, provenance)과 필수 시간 표현을 좁게 정할지, CIDOC CRM 전체 정합을 목표로 할지 비교한다. 동일 사건의 발생 시점, 유효 기간, 문서·출처가 말한 시점, 인물의 인지 시점, 추출·검토 시점을 혼합하지 않는다. 시간 미상·범위·불확실 날짜를 어떻게 저장할지도 정한다.
4. **관계 유형과 인과:** `참여`, `발생 장소`, `전후`, `유효`, `원인으로 주장됨`, `필요조건/가능조건/방해조건으로 해석됨`의 출처·주장 수준을 분리한다. 출처의 명시적 인과 문장과 SOTA 가설을 별도 assertion으로 둔다. 그래프 경로나 벡터 유사도만으로 인과를 확정하지 않는다.
5. **Wikidata 상호운용:** QID 별칭·다국어 label·sitelink를 entity resolution 보조자료로 쓸 범위와, Wikidata의 statement·qualifier·reference를 원자료 주장과 나란히 보존할 방법을 정한다. QID 부재, 중복·모순·미상 시간과 변경 이력의 정책도 필요하다.
6. **벡터 생성 시점:** ontology 완성이 임베딩 선행조건이라는 주장은 아직 검증되지 않았다. 원문 절/chunk를 provenance와 연결한 semantic 후보 검색은 구조화 ontology assertion의 완성 전에 파일럿할 수 있는지 확인한다. 온톨로지·검토 assertion·키워드·임베딩이 서로 다른 역할과 상태를 가진 파생/권위 층이 되도록 한다.
7. **쿼리별 검색 계약:** 기간, 참여 인물, 지역, 관계, 인과 주장, 과학·기술 구현 조건에 대해 필수 구조 필터, 키워드 필드, 벡터 대상 텍스트, 반환할 근거·상태를 정의한다. 관계 탐색은 관계 데이터, 명시값은 필터/키워드, 의미 유사성은 임베딩 후보 검색으로 역할을 나누는 설계를 검토한다.
8. **기간 및 인지 필터:** 검색 대상 기간과 장면 내 인물의 지식 허용 범위를 분리한다. 사실/절 수준의 시간 필터를 적용하고, 현대 문헌이 설명하는 과학 원리를 과거 인물의 인지로 자동 승격하지 않는다. 시작 이전 상태를 만든 선행 사건과 기간을 가로지르는 유효 상태를 포함할 규칙도 점검한다.
9. **출처 유형과 역설계 누수:** 1차 사료, 학술 연구, 백과사전 서술, Wikidata statement/reference, 모델 해석, 작품 창작을 출처·주장 유형으로 구별한다. 역설계 질문·정답 경로·추출 결과가 서로 누출되는지, 특정 앵커의 결과가 공용 원역사 검색 인덱스에 섞이는지 통제한다. 확인해야 할 범위와 증거를 검색 후보에 함께 반환한다.
10. **필터 포함 검색 평가:** 질문 유형별로 정답 근거·관련 무응답 예시를 준비하고, 시간·인물·지역·관계 필터의 반환 부족/누락률, 정확 검색과 근사 검색의 차이, 구조+키워드+벡터 hybrid 순위, 출처 추적 가능성을 측정한다. 평가용 집합·합격 기준·튜닝/확인 분할은 계획에서 정하며 이번 사전 조사에서 실행하지 않는다.

## 미검증·이번 조사 범위 밖

- 로컬 19개 XML의 checksum 일치 및 파서 호환성.
- 파일 본문과 미디어 포함 여부(이미지·영상 없음은 사용자 제공 사실이며 본문을 열어 확인하지 않음).
- 오프라인 dump parse의 정확도, 원문 byte offset 재현, 표/인용/템플릿/각주 보존, 특정 파서의 처리 성능.
- Wikidata와 Wikipedia의 시간적 일치·사실 정확도·reference 신뢰도, QID 매칭 품질.
- CIDOC CRM 전체 도입 여부, 로컬 온톨로지의 클래스·속성 집합, RDF 저장소 도입 여부.
- PG/pgvector에서 실제 기간·작품 필터 조합의 속도, 필터링 근사 검색의 recall, hybrid 검색 품질, 데이터량별 적정 인덱스. 현재 설계 목표 PostgreSQL + pgvector는 유지하며 여기서 변경 결론을 내리지 않는다.
- 모든 다운로드, 압축 해제, 전체 해시, DB 변경, LLM 추출, 임베딩, 벤치마크, 대규모 원역사 조사.

## 공식 출처 목록

아래 문서는 모두 2026-09-24에 웹에서 실제 페이지를 열어 확인했다. 요약은 계획용 메모이며 각 표준/도구의 구현 적합성은 후속 작업에서 검토한다.

| 출처 | 확인한 내용 |
|---|---|
| [Wikimedia MediaWiki Content File Exports](https://wikitech.wikimedia.org/wiki/MediaWiki_Content_File_Exports) | raw XML, `current`/`history`, 완료 확인용 SHA256SUMS와 파일 checksum 검증 |
| [MediaWiki Parsoid API](https://www.mediawiki.org/wiki/Parsoid/API) | wikitext→MediaWiki DOM HTML/RDFa 및 pagebundle 표현 |
| [Wikidata Data Model](https://www.wikidata.org/wiki/Help:Data_model) | QID/item/property, qualifiers, 시점 제한, references의 statement 구조 |
| [CIDOC CRM 7.1.3](https://cidoc-crm.org/sites/default/files/Documents/cidoc_crm_version_7.1.3.html) | 역사 사건 중심 모델, Temporal Entity와 time-span 표현 |
| [W3C PROV-O](https://www.w3.org/TR/prov-o/) | Entity/Activity/Agent, 생성·사용·파생·책임 계보 |
| [W3C SHACL](https://www.w3.org/TR/shacl/) | RDF graph에 대한 구조·제약 검증 |
| [pgvector README](https://github.com/pgvector/pgvector) | PostgreSQL 정확/근사 벡터 검색, 필터 동작, full-text hybrid 검색 |
