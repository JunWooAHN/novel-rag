# 원문 복사와 표본 위치 확인 메모

이 작업에서 확인한 재사용 절차다. Drive `text/plain` 파일은 메타데이터의 `size`, 가능하면 `md5Checksum`을 먼저 기록한다. 원문을 모델 출력에 풀지 않고 커넥터 응답을 함수 내부에서 다루고, 보존 파일의 바이트 크기·해시·BOM·줄바꿈 수를 확인한다. **크기 일치만으로 원격 원본과 바이트 동일성을 증명할 수는 없다.** 원격 MD5가 없으면 “커넥터가 반환한 텍스트를 UTF-8로 재구성했고 메타데이터 크기와 일치”라고 한정한다.

텍스트를 패치로 저장하면 CRLF가 LF로 바뀔 수 있다. 원문 문자열의 CRLF·단독 LF 수를 먼저 세고, 로컬 저장 후 다시 센다. 원문이 전부 CRLF였다는 검증 없이 모든 줄바꿈을 일괄 치환하지 않는다. 마지막 개행과 BOM도 비교한다.

위치는 단위를 붙여 기록한다. `raw byte offset`은 원본 바이트 위치이고, Python 문자열 인덱스는 디코딩 후 Unicode 코드포인트 위치이며, JavaScript `String` 인덱스는 UTF-16 코드 단위 위치다. 한글 BMP 문자만 앞에 있을 때는 뒤의 두 인덱스가 같지만, 이모지 등 보조 평면 문자가 있으면 달라진다. 줄 번호도 이들과 별개다. CRLF 파일에서 `split('\n')`이 남긴 `\r`까지 길이에 포함하면 원문 위치가 유지될 수 있다. 반면 `splitlines()`, `trim()`, `rstrip()` 등으로 개행 문자를 제거하거나 LF로 정규화한 문자열의 길이를 누적하면 원본 좌표와 어긋난다. 이번 위치 오류의 정확한 중간 변환 원인은 확정하지 못했다. 표제는 반드시 **전체 디코딩 문자열에서 직접 찾은 match 위치**를 사용한다.

```python
import re
from pathlib import Path

raw = Path("원문.txt").read_bytes()
text = raw.decode("utf-8")  # BOM이 있으면 U+FEFF가 보존된다.
for m in re.finditer(r"(?m)^【[^\r\n]+】(?=\r?$)", text):
    cp_start = m.start()
    utf16_start = len(text[:cp_start].encode("utf-16-le")) // 2
    line_start = text.count("\n", 0, cp_start) + 1
    assert text[cp_start:m.end()] == m.group()
    print(m.group(), line_start, cp_start, utf16_start)
```

표본 JSON을 만든 뒤에는 각 시작 위치를 원문에 다시 적용해 기록한 표제나 짧은 인용과 정확히 일치하는지 자동 확인한다. 끝 위치는 다음 표제의 실제 match 위치를 사용하고, `start < end <= len(text)`도 검사한다. 보고서의 장면 해석은 확인한 짧은 구간에만 연결하고, 표제 형식이 변하거나 빠진 구간에는 회차 번호를 추정해 붙이지 않는다.
