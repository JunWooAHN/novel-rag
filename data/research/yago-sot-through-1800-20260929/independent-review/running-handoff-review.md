# YAGO 1899 세계사 초안 스캔: 진행 중 인계 독립 검토

**판정: running handoff accepted; full build/release pending.** 이 판정은 2026-09-29의 고정된 문서·영수증에 대한 인계 가능성만 뜻한다. 현재 프로덕션 acceptance JSON은 작성하지 않았고 불변 릴리스도 수락하지 않는다. 검토자는 이 wave에서 H200 프로세스·PG·원본 파일을 다시 조회하지 않았다.

## 결박한 입력과 확인

| 근거 | SHA-256 | 확인과 경계 |
|---|---|---|
| `tools/yago_history_sot/build.py` | `ad4f94668b380e4344c391deaaecc8b2ec104291100b0b4544879063a8534932` | [앞선 독립 코드 검토](scan-code-acceptance-ad4f9466.md)는 **가역 draft scan 경로만** 수락했다. 당시 실제 full output이나 발행 수락은 하지 않았다. |
| [`facts.receipt.json`](../run-evidence/facts.receipt.json) | `a1a20000092e3a49e859d813475d44547e0683d3eaaa84a2894e2c66453d9f81` | 직접 읽어 `74,497,030 = 918,825 mapped + 4,170,181 excluded + 69,408,024 unknown + 0 failed`를 재계산했다. 원본 `5,087,821,943B`와 SHA `17da906cefea15aa076ccfd5ce0bd2956b2e95ae06b225cca18059bbaf5eb1e4`는 [원본 manifest](../../yago-storage-20260928/manifest-final.json)와 일치한다. receipt의 실행 코드 SHA도 위 ad4f와 일치한다. PG facts claim 918,825행 일치는 엔지니어의 단계 조회·등록 영수증을 통한 보고이며 이 wave의 독립 PG 재조회는 아니다. |
| [Luna 초기 실제 snapshot](../mechanical-review/initial-draft-check.json) | `4f8dbfde67805fb8bad9ee583017498bb73fc55cee6d98a6414d515f6deeb4cf` | facts 첫 7,000,000행 범위의 읽기 전용 snapshot에서 mapped 93,967건, 직접 point의 1899 초과 0, crossing H_state 694건의 원 종료 보존과 조회 상한 1899, 원본 offset 11표본 일치를 기록했다. 이는 전체 facts나 아직 미실행 Meta 연결·문맥·보조층 검증이 아니다. |
| [진행 보고 v0.0.4](../../../../docs/research/20260929-yago-history-sot-through-1899.md) | `391450cb6ad652ad57ddf2ad5421b886cf25097aae49d8a1b47a2b3918bfbe08` | facts 완료와 beyond-wikipedia의 **08:37 KST 무렵 33,000,000행/2,157,461,609B 중간 관찰**을 구별하고, 이후 단계·릴리스 미완료를 명시한다. |
| [체크포인트 v0.0.35](../../../../docs/harness/current-checkpoint.md) | `7468c5cab0ca69423215753c8656545347fec596b523d5b92544bc622f9c69d6` | 같은 진행 상태와 PID 39714 확인·안전 재개 경계, Wikidata PID 38511 별도 실행과 기존 r3 보존을 기록한다. |
| [문서 생애주기 영수증](../run-evidence/document-lifecycle.json) | `c145feb2d3a0663626981390aa60758ecc612f40818e33f0f55397e630a22126` | 파일에서 보고 v0.0.4 `canon=false`·체크포인트 v0.0.35 `canon=true`의 위 SHA 결박과 `verify --files` 290판/40파일/문제0 보고를 확인했다. 이 wave에서 문서 DB 검증 명령을 재실행하지 않았다. |

보고·체크포인트는 `facts` 한 파일의 완료 receipt와 다음 파일의 중간 로그 관찰을 전량 완성이나 역사 사실 확정으로 확대하지 않는다. Meta 첫 실행의 exit 1, bloom 재개 검증, 현재 코드판, 별도 DB/스캔 단계, 발행 전 독립 수락 게이트를 인계받을 수 있는 수준으로 남긴다. `beyond-wikipedia`의 33,000,000행 관찰은 완료 receipt가 아니므로 파일 분모나 원본 SHA를 확정하지 않는다. Luna JSON과 별도 설명 MD 중 Meta 영수증/ledger SHA의 명칭 혼동은 이번 판정에 쓰지 않고, 숫자·범위가 구분된 JSON을 기준으로 삼았다.

## 후속 수락 조건

서버 job 종료 후 실제 `scan-v2.exit`와 모든 단계 receipt, file SHA·회계·PG 행수·Meta FK와 원 byte 표본을 Luna가 전량 범위에서 점검해야 한다. 다른 Sol은 [최종 독립 검증안](final-verification-plan.md)에 따라 1899/1900/BCE/crossing/unknown, `H`/`K`/taxonomy, 명시적 fictional type과 선택 H의 결합, r3의 Hangul `startDate`와 새 `H_boundary`의 의미 차이, 정확한 전체 readback·receipt bundle·코드/manifest hash를 재조회한다. 선택된 명시적 허구 개체를 현실 역사 H로 무표시 노출하는지 역시 그때 판정한다. 그 결과가 일치할 때만 별도 정확한 production acceptance JSON을 작성하고, 구현자의 불변 발행 뒤 새 연결 조회·불변/멱등·백업 복원 증거를 검토한다. 현재 이 조건들은 **pending**이며 이 인계 판정으로 작업 목표를 완료 표시하지 않는다.
