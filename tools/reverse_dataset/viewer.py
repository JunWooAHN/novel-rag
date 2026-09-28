#!/usr/bin/env python3
"""Build a self-contained HTML reader from one accepted DB release."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from export import read_release

ROOT = Path(__file__).resolve().parents[2]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def render_html(release, db_path: Path, import_id: str) -> str:
    items = release["rows"]
    if len(items) != 272:
        raise ValueError("fixed reviewed release must contain 272 accepted rows")
    provenance = {"kind": "derived_from_analysis_db", "db_path": str(db_path.resolve()),
                  "import_id": import_id, "release_id": release["release_id"],
                  "source_hashes": release["source_hashes"],
                  "selection_policy_hashes": release["selection_policy_hashes"],
                  "records": len(items)}
    # Script-data is inert, but HTML's parser still recognizes </script>.
    payload = json.dumps(items, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    metadata = json.dumps(provenance, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c")
    return (HTML.replace("__COUNT__", str(len(items)))
            .replace("__PROVENANCE__", metadata)
            .replace("__DATA__", payload))


def build(db_path: Path, import_id: str, output: Path):
    release = read_release(db_path, import_id)
    html = render_html(release, db_path, import_id)
    output = output.resolve()
    for original in (ROOT / "data/training/reverse-20260925", ROOT / "data/training/reverse-full-20260925"):
        if output.is_relative_to(original.resolve()):
            raise ValueError("do not overwrite legacy source artifacts")
    if output.exists():
        raise ValueError("output already exists")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        stream.write(html)
    print(json.dumps({"path": str(output), "release_id": release["release_id"],
                      "records": len(release["rows"]), "bytes": output.stat().st_size,
                      "sha256": digest(output.read_bytes())}, ensure_ascii=False))


HTML = r'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>역설계 데이터셋 · 실제 예시 __COUNT__건</title>
<style>
  :root { color-scheme: light; --paper:#f8f5ed; --surface:#fffdf7; --ink:#203633; --muted:#62736e; --teal:#164f4c; --line:#d8ded5; --gold:#bd8c4a; --shade:#edf1e9; }
  * { box-sizing:border-box; }
  html { scroll-behavior:smooth; }
  body { margin:0; background:var(--paper); color:var(--ink); font-family:system-ui,-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif; line-height:1.6; }
  button,input,select { font:inherit; }
  button { cursor:pointer; }
  .wrap { max-width:1560px; margin:auto; padding:24px clamp(16px,3vw,48px) 56px; }
  header { border-bottom:1px solid var(--line); padding-bottom:22px; }
  .eyebrow { color:var(--teal); font-size:.8rem; font-weight:800; letter-spacing:.13em; text-transform:uppercase; }
  h1 { margin:8px 0 8px; font-family:Georgia,"Noto Serif KR",serif; font-size:clamp(2rem,4vw,3.4rem); line-height:1.18; font-weight:650; }
  header p { margin:0; max-width:72ch; color:var(--muted); }
  .summary { display:flex; flex-wrap:wrap; gap:9px; margin:20px 0 0; }
  .pill { border:1px solid var(--line); background:var(--surface); padding:5px 12px; border-radius:999px; font-size:.86rem; }
  .pill strong { color:var(--teal); }
  .toolbar { display:grid; grid-template-columns:minmax(220px,2fr) repeat(4,minmax(120px,1fr)) auto; gap:10px; align-items:end; margin:24px 0 18px; }
  label { display:grid; gap:5px; color:var(--muted); font-size:.8rem; font-weight:700; }
  input,select { width:100%; border:1px solid var(--line); border-radius:8px; background:var(--surface); color:var(--ink); padding:9px 10px; min-height:42px; }
  input:focus,select:focus,button:focus-visible { outline:2px solid var(--gold); outline-offset:2px; }
  .button { background:var(--teal); border:1px solid var(--teal); color:white; border-radius:8px; padding:8px 14px; min-height:42px; font-weight:700; }
  .button.secondary { color:var(--teal); background:var(--surface); border-color:var(--line); }
  .button:disabled { opacity:.45; cursor:not-allowed; }
  .layout { display:grid; grid-template-columns:minmax(250px,300px) minmax(0,1fr); gap:20px; align-items:start; }
  .listbox,.detail { background:var(--surface); border:1px solid var(--line); border-radius:12px; box-shadow:0 9px 28px rgba(20,50,45,.035); }
  .listbox { position:sticky; top:16px; overflow:hidden; }
  .listhead { padding:15px 16px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; gap:10px; font-weight:800; }
  .list { overflow-y:auto; max-height:min(72vh,800px); }
  .item { display:block; width:100%; text-align:left; border:0; border-bottom:1px solid var(--line); background:transparent; padding:12px 16px; color:var(--ink); }
  .item:hover,.item.active { background:var(--shade); }
  .item.active { border-left:4px solid var(--teal); padding-left:12px; }
  .item strong { display:block; font-size:.88rem; line-height:1.3; overflow-wrap:anywhere; }
  .item small { color:var(--muted); display:block; margin-top:3px; }
  .detail { min-width:0; padding:clamp(16px,2vw,28px); }
  .detailtop { display:flex; flex-wrap:wrap; justify-content:space-between; gap:12px; align-items:start; }
  .detail h2 { margin:2px 0 6px; font-size:1.45rem; overflow-wrap:anywhere; }
  .sub { color:var(--muted); font-size:.9rem; }
  .nav { display:flex; flex-wrap:wrap; gap:7px; }
  .note { border-left:3px solid var(--gold); padding:10px 13px; background:#f6f0e3; margin:20px 0; font-size:.9rem; }
  .panes { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  .pane { min-width:0; border:1px solid var(--line); border-radius:10px; overflow:hidden; }
  .pane h3 { font-size:1rem; margin:0; padding:11px 14px; background:var(--shade); border-bottom:1px solid var(--line); }
  .pane .hint { display:block; font-weight:400; font-size:.78rem; color:var(--muted); }
  pre { white-space:pre-wrap; overflow-wrap:anywhere; margin:0; padding:16px; font-family:ui-monospace,SFMono-Regular,Consolas,"Noto Sans Mono CJK KR",monospace; line-height:1.72; font-size:.85rem; max-height:690px; overflow:auto; }
  .prose { font-family:Georgia,"Noto Serif KR",serif; font-size:1rem; line-height:1.85; }
  .meta { display:flex; flex-wrap:wrap; gap:8px 16px; color:var(--muted); font-size:.79rem; padding:15px 0 0; }
  details { border-top:1px solid var(--line); margin-top:18px; padding-top:13px; }
  summary { color:var(--teal); font-weight:800; cursor:pointer; }
  .actions { display:flex; flex-wrap:wrap; gap:8px; margin-top:19px; }
  dialog { border:1px solid var(--line); border-radius:12px; width:min(1100px,94vw); max-height:90vh; background:var(--surface); color:var(--ink); padding:0; }
  dialog::backdrop { background:rgba(19,38,36,.6); }
  .dialoghead { padding:12px 16px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--line); }
  dialog pre { max-height:77vh; }
  .empty { padding:30px 16px; color:var(--muted); }
  footer { color:var(--muted); font-size:.8rem; padding-top:26px; }
  @media(max-width:960px) { .toolbar { grid-template-columns:1fr 1fr; } .layout { grid-template-columns:1fr; } .listbox { position:static; } .list { max-height:240px; } }
  @media(max-width:650px) { .toolbar,.panes { grid-template-columns:1fr; } .wrap { padding:16px 12px 40px; } .detail { padding:14px; } .pane pre { max-height:420px; } }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="eyebrow">Reviewed development data · local reader</div>
    <h1>역설계 데이터셋, 실제 예시</h1>
    <p>검토를 거쳐 수락한 __COUNT__건의 실제 입력과 정답을 읽어 보세요. 원문 근거는 고정된 원문판의 정확한 범위를 확인한 것입니다. 이 페이지는 파일 안에서만 작동하며 외부로 데이터를 보내지 않습니다.</p>
    <div class="summary" id="summary"></div>
  </header>
  <div class="toolbar" aria-label="예시 필터">
    <label>내용 검색<input id="search" type="search" placeholder="인물, 문장, ID, JSON 키 검색"></label>
    <label>작품<select id="work"><option value="">모든 작품</option><option value="gogjong">폭군 고종대왕 일대기</option><option value="goryeo">고려</option><option value="poland">폴란드</option></select></label>
    <label>용도<select id="role"><option value="">모든 용도</option><option value="gemma_style">문체 재현</option><option value="sota_planning">기획 역구성</option></select></label>
    <label>분할<select id="split"><option value="">모든 분할</option><option value="train">학습 후보</option><option value="development_validation">개발 검증</option><option value="development_holdout">개발 홀드아웃</option></select></label>
    <label>판본<select id="release"><option value="">초반 + 추가판</option><option value="initial">초반 50구간</option><option value="full">전편 확장</option></select></label>
    <button class="button secondary" id="reset" type="button">필터 지우기</button>
  </div>
  <div class="layout">
    <aside class="listbox" aria-label="예시 목록"><div class="listhead"><span>예시 목록</span><span id="matchCount"></span></div><div class="list" id="list"></div></aside>
    <main class="detail" id="detail" aria-live="polite"></main>
  </div>
  <footer>관찰된 개발 자료입니다. 수락은 자료 검토 결과이며 모델 훈련·성능 평가·토크나이저 검증을 뜻하지 않습니다.</footer>
</div>
<dialog id="allDialog"><div class="dialoghead"><strong>전체 JSONL · __COUNT__건</strong><button class="button secondary" type="button" id="closeDialog">닫기</button></div><pre id="allJson"></pre></dialog>
<script type="application/json" id="build-provenance">__PROVENANCE__</script>
<script type="application/json" id="dataset">__DATA__</script>
<script>
(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('dataset').textContent);
  const $ = id => document.getElementById(id);
  const workNames = {gogjong:'폭군 고종대왕 일대기',goryeo:'고려',poland:'폴란드'};
  const splitNames = {train:'학습 후보',development_validation:'개발 검증',development_holdout:'개발 홀드아웃'};
  const releaseNames = {initial:'초반 50구간',full:'전편 확장'};
  const roleNames = {gemma_style:'문체 재현',sota_planning:'기획 역구성'};
  let filtered = data.map((_,i) => i);
  let selected = filtered[0];
  const make = (tag, className, content) => { const el=document.createElement(tag); if(className) el.className=className; if(content!==undefined) el.textContent=content; return el; };
  const formatInput = value => { try { return JSON.stringify(JSON.parse(value),null,2); } catch { return value; } };
  const text = item => {
    const r=item.record, m=r.metadata;
    return [r.sample_id,workNames[m.work_id],m.role,m.split,item.release,r.messages[0].content,r.messages[1].content,item.source_answer].join(' ').toLocaleLowerCase();
  };
  const searchable=data.map(text);
  const summary=$('summary');
  const totalBy = key => data.reduce((out,item) => { const value=key(item);out[value]=(out[value]||0)+1;return out; },{});
  const byWork=totalBy(item=>item.record.metadata.work_id), byRelease=totalBy(item=>item.release);
  for(const [name,count] of [['전체',data.length],['초반 50구간',byRelease.initial],['전편 확장',byRelease.full],...Object.entries(byWork).map(([w,n])=>[workNames[w],n])]) {
    const pill=make('span','pill');pill.append(make('strong','',String(count)),' '+name);summary.append(pill);
  }
  function renderList() {
    const list=$('list');list.replaceChildren();$('matchCount').textContent=filtered.length+'건';
    if(!filtered.length){list.append(make('div','empty','검색 결과가 없습니다.'));return;}
    const fragment=document.createDocumentFragment();
    for(const index of filtered){
      const item=data[index],r=item.record,m=r.metadata;
      const b=make('button','item'+(index===selected?' active':''));b.type='button';
      b.append(make('strong','',r.sample_id),make('small','',`${workNames[m.work_id]} · ${releaseNames[item.release]} · ${splitNames[m.split]}`));
      b.addEventListener('click',()=>select(index));fragment.append(b);
    }
    list.append(fragment);
  }
  function select(index) { selected=index;renderList();renderDetail(); }
  function addMeta(parent,label,value){const span=make('span','',`${label}: ${value}`);parent.append(span);}
  function renderDetail(){
    const detail=$('detail');detail.replaceChildren();
    if(selected===undefined){detail.append(make('div','empty','필터에 맞는 예시가 없습니다.'));return;}
    const item=data[selected],r=item.record,m=r.metadata,position=filtered.indexOf(selected);
    const top=make('div','detailtop'),title=make('div');title.append(make('div','eyebrow',`${workNames[m.work_id]} · ${roleNames[m.role]}`),make('h2','',r.sample_id),make('div','sub',`${releaseNames[item.release]} · ${splitNames[m.split]} · ${position+1} / ${filtered.length}`));
    const nav=make('div','nav');
    for(const [label,offset] of [['이전',-1],['다음',1]]){const b=make('button','button secondary',label);b.type='button';b.disabled=position+offset<0||position+offset>=filtered.length;b.addEventListener('click',()=>select(filtered[position+offset]));nav.append(b);}
    top.append(title,nav);detail.append(top);
    const explanation=m.role==='gemma_style'
      ? '고종: 왼쪽은 작가에게 줄 수 있는 역구성 입력, 오른쪽 정답은 원문에서 가져온 실제 소설 문장입니다.'
      : '마늘맛스낵 작품: 왼쪽은 장면 기획 입력, 오른쪽 정답은 원문을 바탕으로 검토한 역구성 기획입니다. 원저자의 실제 기획 의도를 뜻하지 않습니다.';
    detail.append(make('div','note',explanation));
    const panes=make('div','panes');
    const answer=m.role==='gemma_style'?r.messages[1].content:formatInput(r.messages[1].content);
    const answerHint=m.role==='gemma_style'?'assistant message · 원본 문자열 그대로':'assistant message · 가독성을 위한 JSON 들여쓰기 · JSON 별도 제공';
    for(const [heading,hint,content,cls] of [['입력','user message · JSON 키와 내용을 읽기 좋게 들여씀',formatInput(r.messages[0].content),''],['정답',answerHint,answer,m.role==='gemma_style'?'prose':'']]){
      const pane=make('section','pane'),h=make('h3','',heading),small=make('span','hint',hint),pre=make('pre',cls,content);h.append(small);pane.append(h,pre);panes.append(pane);
    }
    detail.append(panes);
    const meta=make('div','meta');addMeta(meta,'출처 범위',`${m.answer_start_cp}–${m.answer_end_cp} CP`);addMeta(meta,'근거 유형',m.target_basis);addMeta(meta,'검토자',m.reviewed_by);addMeta(meta,'토큰 검증',m.token_validation||'미실행');addMeta(meta,'원문 SHA-256',m.answer_sha256);detail.append(meta);
    const evidence=make('details'),sum=make('summary','','원문 근거 장면 펼치기'),source=make('pre','prose',item.source_answer);evidence.append(sum,source);detail.append(evidence);
    const actions=make('div','actions');
    const copy=make('button','button secondary','선택 예시 JSON 복사');copy.type='button';copy.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(item.raw_line);copy.textContent='복사됨';setTimeout(()=>copy.textContent='선택 예시 JSON 복사',1800);}catch{showRaw(item.raw_line,'선택 예시 JSON');}});
    const show=make('button','button secondary','전체 JSONL 보기');show.type='button';show.addEventListener('click',()=>showRaw(data.map(x=>x.raw_line).join('\n')+'\n','전체 JSONL · __COUNT__건'));
    const download=make('button','button','전체 JSONL 다운로드');download.type='button';download.addEventListener('click',()=>{const blob=new Blob([data.map(x=>x.raw_line).join('\n')+'\n'],{type:'application/x-ndjson;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='reviewed-reverse-dataset-__COUNT__.jsonl';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
    actions.append(copy,show,download);detail.append(actions);
  }
  function showRaw(value,heading){$('allDialog').querySelector('strong').textContent=heading;$('allJson').textContent=value;$('allDialog').showModal();}
  $('closeDialog').addEventListener('click',()=>{$('allDialog').close();$('allJson').textContent='';});
  $('allDialog').addEventListener('close',()=>{$('allJson').textContent='';});
  function filter(){
    const q=$('search').value.trim().toLocaleLowerCase(),work=$('work').value,role=$('role').value,split=$('split').value,release=$('release').value;
    filtered=data.map((_,i)=>i).filter(i=>{const x=data[i],m=x.record.metadata;return (!work||m.work_id===work)&&(!role||m.role===role)&&(!split||m.split===split)&&(!release||x.release===release)&&(!q||searchable[i].includes(q));});
    if(!filtered.includes(selected))selected=filtered[0];renderList();renderDetail();
  }
  for(const id of ['search','work','role','split','release']) $(id).addEventListener(id==='search'?'input':'change',filter);
  $('reset').addEventListener('click',()=>{$('search').value='';for(const id of ['work','role','split','release'])$(id).value='';filter();});
  renderList();renderDetail();
})();
</script>
</body>
</html>'''


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "data/analysis/novel-corpus.sqlite3")
    parser.add_argument("--import-id", required=True, help="fixed, imported reviewed release ID")
    parser.add_argument("--output", type=Path, required=True, help="new DB-derived standalone HTML path")
    args = parser.parse_args()
    try:
        build(args.db, args.import_id, args.output)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(1, f"error: {exc}\n")
