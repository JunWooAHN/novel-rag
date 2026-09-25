# **Phase 1: 로컬 PostgreSQL 기반 SOT 아키텍처 및 스키마 (Dual-DB 적용)**

## **1\. 로컬 PostgreSQL 도입의 3대 이점 (클라우드 탈피)**

1. **데이터 보안 및 비용 절감:** A40 서버 내 Docker 컨테이너로 직접 구동하므로 클라우드 스토리지 비용(Supabase 요금)이 발생하지 않으며, 학습용 원천 데이터의 외부 유출 리스크를 원천 차단합니다.  
2. **역할 분리 (Dual-DB):** 무거운 벡터 인덱스 연산은 Weaviate(Vector/Graph DB)로 이관하고, PostgreSQL은 순수 RDB로서 텍스트 원본 보존, 계층형 쿼리(타임라인), 무결성 검증에만 집중하여 성능을 극대화합니다.  
3. **강력한 서버사이드 함수 (RPC):** 복잡한 타임라인 분기 로직을 백엔드 코드가 아닌 PostgreSQL 자체의 재귀 쿼리(Recursive CTE)로 처리하여 네트워크 지연을 최소화합니다.

## **2\. Git-Branching 방식의 핵심 스키마 설계 (DDL)**

벡터 관련 확장을 제거하고 순수 관계형 데이터 모델로 재구성된 스키마입니다.

\-- 1\. 타임라인(브랜치) 관리 테이블  
CREATE TABLE timelines (  
    id SERIAL PRIMARY KEY,  
    name TEXT NOT NULL,   
    parent\_timeline\_id INT REFERENCES timelines(id),  
    divergence\_date DATE,  
    created\_at TIMESTAMPTZ DEFAULT NOW()  
);

\-- 2\. 토탈 연표 (SOT) 테이블  
CREATE TABLE sot\_chronology (  
    id BIGSERIAL PRIMARY KEY,  
    timeline\_id INT NOT NULL REFERENCES timelines(id),  
    event\_date DATE NOT NULL,  
    character\_name TEXT NOT NULL,  
    status TEXT DEFAULT 'alive',  
    major\_event TEXT NOT NULL,  
      
    \-- 나비효과 관리를 위한 델타(Delta) 컬럼  
    action\_type TEXT DEFAULT 'KEEP', \-- KEEP(유지), MODIFY(변형), CANCEL(소멸)  
    overrides\_event\_id BIGINT REFERENCES sot\_chronology(id),   
      
    metadata JSONB, \-- {"domain": "military", "impact": 3, "speed": 2}  
      
    \-- Weaviate 데이터 매핑용 외부 식별자 (필요 시)  
    weaviate\_uuid UUID UNIQUE,  
      
    created\_at TIMESTAMPTZ DEFAULT NOW()  
);

\-- 인덱스 최적화  
CREATE INDEX idx\_sot\_timeline\_date ON sot\_chronology(timeline\_id, event\_date);  
CREATE INDEX idx\_sot\_weaviate\_uuid ON sot\_chronology(weaviate\_uuid);

\-- 3\. 씬(Scene) 본문 테이블 (임베딩 컬럼 제거)  
CREATE TABLE novel\_scenes (  
    id BIGSERIAL PRIMARY KEY,  
    timeline\_id INT NOT NULL REFERENCES timelines(id),  
    chapter\_number INT,  
    scene\_order INT NOT NULL,  
    scene\_date DATE,  
    content TEXT NOT NULL,  
    metadata\_xml TEXT,  
      
    \-- 벡터 데이터는 Weaviate에 저장되며, 이 테이블의 id 값을 페이로드로 가짐  
    created\_at TIMESTAMPTZ DEFAULT NOW()  
);

## **3\. 세련된 SOT 조회 전략 (PostgreSQL 재귀 함수)**

클라우드 환경 여부와 무관하게 PostgreSQL의 코어 기능을 활용하여 타임라인 분기를 제어합니다.

CREATE OR REPLACE FUNCTION get\_sot\_for\_timeline(target\_id INT)  
RETURNS SETOF sot\_chronology AS $$  
WITH RECURSIVE lineage AS (  
    SELECT id, parent\_timeline\_id, divergence\_date, '9999-12-31'::DATE AS max\_allowed\_date  
    FROM timelines WHERE id \= target\_id  
    UNION ALL  
    SELECT parent.id, parent.parent\_timeline\_id, parent.divergence\_date, child\_lineage.divergence\_date AS max\_allowed\_date  
    FROM timelines parent  
    JOIN lineage child\_lineage ON parent.id \= child\_lineage.parent\_timeline\_id  
)  
SELECT s.\* FROM sot\_chronology s  
JOIN lineage l ON s.timeline\_id \= l.id  
WHERE s.event\_date \< l.max\_allowed\_date  
  \-- 취소(CANCEL)된 역사는 최종 컨텍스트에서 제외합니다.  
  AND s.action\_type \!= 'CANCEL'   
  \-- 변형(MODIFY)되어 덮어씌워진 과거의 원본 역사도 제외합니다.  
  AND s.id NOT IN (  
      SELECT overrides\_event\_id FROM sot\_chronology WHERE timeline\_id \= target\_id AND overrides\_event\_id IS NOT NULL  
  )  
ORDER BY s.event\_date ASC;  
$$ LANGUAGE sql;

## **4\. 데이터 운영 예시 (Data Flow)**

새로운 외전을 시작할 때 테이블을 생성하지 않고 timelines 레코드 추가만으로 분기합니다.

1. **초기 세팅 (정사 구축)**  
   * timelines 삽입: INSERT INTO timelines (id, name) VALUES (1, '실제 역사(정사)');  
   * SOT 추가: timeline\_id=1로 임진왜란 팩트 주입.  
2. **본편 런칭 (1592-04-14 분기 발생)**  
   * timelines 삽입: INSERT INTO timelines (id, name, parent\_timeline\_id, divergence\_date) VALUES (2, '대하소설 본편', 1, '1592-04-14');  
   * 이제 AI가 쓰는 모든 씬과 SOT는 timeline\_id=2로 저장.

## **5\. \[심화\] 나비효과 확산 제어 (Weaviate \+ PostgreSQL \+ LLM 조합)**

Dual-DB 아키텍처에 맞춘 인과율 스캔 프로세스입니다.

### **5.1. SOT 초기 분류 (Metadata Tagging)**

정사 SOT를 PostgreSQL에 넣을 때 metadata JSONB 컬럼에 인간의 힘으로 바꿀 수 없는 제약 조건을 하드코딩합니다.

### **5.2. Weaviate의 역할: "영향권(Blast Radius) 필터링"**

주인공의 행동을 기반으로 Weaviate에서 고속으로 벡터-그래프 검색을 수행합니다.

* *Weaviate 반환값:* 유사도와 인과 관계 조건을 충족하는 이벤트들의 PostgreSQL\_ID 목록.  
* *PostgreSQL 조회:* 반환된 ID 목록을 기반으로 RDB에서 상세 텍스트(major\_event)와 델타 이력(action\_type)을 일괄 조회(SELECT ... WHERE id IN (...)).

### **5.3. 판정관 (The Assessor Agent)**

PostgreSQL에서 최종 조합된 텍스트 컨텍스트를 Hermes Agent(또는 Claude)에 전달하여 인과율을 판정합니다.

**\[Agent Response\]**

{  
  "affected": true,  
  "action\_type": "MODIFY",  
  "overrides\_event\_id": 100,  
  "new\_event\_description": "한산도 대첩 \- 조선 수군이 조총 사격과 포를 결합하여 압도적인 승리를 거둠"  
}

판정 결과에 따라 PostgreSQL sot\_chronology에 신규 SOT를 INSERT하고, 해당 내역의 텍스트를 벡터화하여 Weaviate에 추가 업로드(Sync)합니다.