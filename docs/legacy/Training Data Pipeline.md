# **대체역사물 파인튜닝을 위한 데이터 역산(Reverse Engineering) 파이프라인**

## **💡 왜 메타데이터를 먼저 추출해야 하는가? (Train-Inference Alignment)**

파인튜닝의 제1원칙은 "학습할 때 보는 프롬프트 구조와, 실제 서비스(Inference)에서 던져줄 프롬프트 구조가 100% 동일해야 한다"는 것입니다.

대표님의 \[모듈 D\] 설계를 보면, AI는 글을 쓰기 전에 \<system\_context\>라는 방대한 SOT 정보(타겟 일자, 장소, 인물, 나비효과, 궤적, 이전 씬 요약 등)를 받습니다. 원본 소설(정답 텍스트)만으로는 이 SOT 정보를 알 수 없습니다.

따라서 **원본 소설을 뜯어서(Parsing) \-\> 메타데이터를 추출하고 \-\> 이를 바탕으로 가상의 SOT 상황을 역으로 조립한 뒤 \-\> 최종 XML 프롬프트를 만들어내는 과정**이 필수적입니다.

## **🛠️ 4단계 리버스 엔지니어링 프로세스**

### **Phase 1: 씬(Scene) 분할 및 원본 텍스트 확정 (Output)**

100여 개의 완결 소설 본문을 \[제1원칙\]에 따라 '씬(Scene)' 단위로 자릅니다.

* **결과물:** scene\_id\_001.txt, scene\_id\_002.txt ... (이 텍스트들이 파인튜닝 시 모델이 생성해야 할 최종 **Output**이 됩니다.)

### **Phase 2: Claude Haiku를 이용한 메타데이터 역추출**

잘려진 각 씬 본문을 가벼운 모델(Claude 3 Haiku 또는 GPT-4o-mini 추천)에 넣어 아래 정보를 강제로 추출하게 합니다. (2억 5천만 자를 처리해야 하므로 비용 효율이 중요합니다.)

* **추출 대상:** 작중 날짜(추정), 장소, 등장인물, 이 씬에서 일어난 핵심 사건 요약(대요).

### **Phase 3: 가상 SOT 및 문맥 재구성 (Context Simulation) \- ⚠️ 가장 중요**

이 단계가 파인튜닝의 퀄리티를 결정합니다. 현재 타겟이 되는 씬이 scene\_id\_150이라고 가정해 봅시다.

모델이 scene\_id\_150을 쓸 때, **미래의 정보(151화 이후)를 미리 알고 있으면 절대 안 됩니다.** (Data Leakage 발생)

* 추출된 메타데이터를 바탕으로, scene\_id\_001 부터 scene\_id\_149 까지의 정보만을 조합하여 **\[모듈 D\]의 \<system\_context\> 포맷을 완벽하게 재현**합니다.  
* *인물 궤적:* 149화까지 일어난 이순신의 주요 행적 요약.  
* *이전 씬 문맥:* 147\~149화의 대요 요약.

### **Phase 4: JSONL 학습 데이터셋 조립**

\[모듈 D\]의 프롬프트 구조와 100% 일치하는 프롬프트를 만들고, 원본 소설 텍스트와 매칭합니다.

{"instruction": "아래 XML 시스템 컨텍스트와 지시사항을 분석하여 다음 씬의 웹소설 본문을 작성하시오.", "input": "\<system\_context\>\\n  \<current\_scene\_info\>\\n    \<target\_date\>1593-02-15\</target\_date\>\\n    \<target\_location\>한산도 통제영\</target\_location\>\\n    \<target\_characters\>이순신, 원균\</target\_characters\>\\n  \</current\_scene\_info\>\\n  \<character\_trajectory\>\\n    \<character name=\\"이순신\\"\>\\n      \<event date=\\"1592-07\\"\>한산도에서 대승을 거둠\</event\>\\n    \</character\>\\n  \</character\_trajectory\>\\n  \<previous\_scenes\>\\n    \<scene date=\\"1592-12-15\\"\>원균이 공을 탐내어 이순신과 마찰을 빚음\</scene\>\\n  \</previous\_scenes\>\\n\</system\_context\>\\n\<instruction\>\\n  위의 \<system\_context\>를 바탕으로 1593년 2월, 한산도에서 이순신과 원균이 언쟁을 벌이는 다음 씬을 집필하시오.\\n\</instruction\>", "output": "원균의 목소리가 통제영 본영을 쩌렁쩌렁 울렸다. \\"통제사 영감\! 어찌하여 내 군사들을 사지로 몰아넣는단 말이오\!\\" 이순신은 묵묵히 붓을 내려놓았다. 그의 차가운 시선이 원균의 붉게 달아오른 얼굴에 꽂혔다..."}  
