# 마늘맛스낵 작가 분석 사전 점검

확인일: 2026-09-24

## 대상과 보유 범위

[보유 인벤토리](../../20260924-owned-novels-inventory.json), [선정표](../../20260924-selected-novels.json), [기존 대조표](../../20260924-bestseller-selection.md)를 대조한 현재 대상은 **2편**이다. 공식 문피아 작품 귀속은 두 작품 모두 마늘맛스낵으로 기록되어 있다. 파일명과 공식 표시 총회차는 각각 653화, 524화로 맞지만, 이 숫자만으로 원문 본문의 회차 누락·중복이 없다고 판단할 수 없다.

| 작품 | 공식 작품 | 보유 폴더·파일명 | 표시 범위 | Drive ID |
|---|---|---|---:|---|
| 《고려, 신대륙에 떨어지다》 | [문피아](https://www.munpia.com/novel/detail/216931) | `2605/고려 신대륙에 떨어지다 [외포완] 1-653.txt` | 1~653 | `12Gc9wGbK6qs7Y7Ai1TlvHWnAUy3qVJi3` |
| 《폴란드 여왕 키우기》 | [문피아](https://www.munpia.com/novel/detail/415466) | `2607/폴란드 여왕 키우기 1-524 완결.txt` | 1~524 | `1-DJl9LGFtkgnP_gZ2aM9bw2UltnbNXAk` |

## 원문 보관 및 검증

두 Drive 파일은 `text/plain`이다. 원본 Drive 파일을 변경하지 않고 커넥터의 기본 텍스트 응답을 UTF-8로 재구성해 원래 파일명으로 `docs/references/garlic-snack/`에 저장했다. 함수 내부에서 전체 응답을 처리했고 본문 전체를 도구 출력에 표시하지 않았다. 패치 저장 과정에서 바뀐 줄바꿈과 끝개행은 저장 전 응답의 수치대로 복원했다. [원문 복사·위치 메모](../richerlen/source-offset-notes.md)의 구분에 따라 아래 수치는 로컬 **바이트** 기준이다.

| 원문 사본 | Drive 원본 | 메타데이터·로컬 크기 | BOM | CRLF / 단독 LF·CR | 끝개행 | 로컬 MD5 | 로컬 SHA-256 |
|---|---|---:|---|---:|---|---|---|
| [고려 신대륙에 떨어지다 [외포완] 1-653.txt](../../../references/garlic-snack/고려%20신대륙에%20떨어지다%20%5B외포완%5D%201-653.txt) | [Drive](https://drive.google.com/file/d/12Gc9wGbK6qs7Y7Ai1TlvHWnAUy3qVJi3/view?usp=drivesdk) | 11,658,340 | 있음 | 207,973 / 0 | 없음 | `030f3fe763a9aacfc53a15f07c8734a7` | `b1f719ca45c171fd28b20d074e3a508946a923b4c8ff64ebd4c0076834d19b82` |
| [폴란드 여왕 키우기 1-524 완결.txt](../../../references/garlic-snack/폴란드%20여왕%20키우기%201-524%20완결.txt) | [Drive](https://drive.google.com/file/d/1-DJl9LGFtkgnP_gZ2aM9bw2UltnbNXAk/view?usp=drivesdk) | 9,587,505 | 없음 | 181,651 / 0 | CRLF 있음 | `aa0c4a9ab71fb3851a8f897801bead3b` | `483360b0f19e6d1c702fe3aec2b338331c9907fb2de796aa1c16ff5526ba9832` |

두 파일 모두 커넥터 응답에서 계산한 UTF-8 바이트 수와 Drive 메타데이터 크기가 같고, 로컬 파일의 크기·BOM·줄바꿈 수·끝개행도 응답과 일치한다. 원격 MD5는 메타데이터 응답에 없어 Drive 원본과 로컬 사본의 바이트 동일성을 독립적으로 증명할 수 없다. 위 해시는 보존된 로컬 사본을 식별한다. 원문 사본은 `docs/references/.gitignore` 규칙으로 Git 추적에서 제외된다.

## 후속 분석 범위

사용자가 확정한 범위는 **회차 구성과 구조 지도 + 초·중·후반 대표 장면**이다. 각 작품의 Luna 담당자가 회차 경계와 표본 위치를 원문에서 확인하고, Sol 담당자가 근거를 대조한다. 이번 사전 점검은 작품 본문 해석을 수행하지 않았다. 두 작품에서 나타난 특성과 한 작품에만 나타난 특성을 구분하고, 확인하지 않은 구간에 대한 판단은 가설로 표시한다.
