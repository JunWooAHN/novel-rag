import { useState, useEffect, useCallback } from 'react'
import { fetchJSON, subscribeSSE } from './api.js'
import ForceGraph3D from 'react-force-graph-3d'

// ====================================================================
// 메인 애플리케이션
// ====================================================================

export default function App() {
    const [page, setPage] = useState('dashboard')
    const [projectInfo, setProjectInfo] = useState(null)
    const [refreshKey, setRefreshKey] = useState(0)
    const [connected, setConnected] = useState(false)

    const loadProjectInfo = useCallback(() => {
        fetchJSON('/api/project/info')
            .then(setProjectInfo)
            .catch(() => setProjectInfo(null))
    }, [])

    useEffect(() => { loadProjectInfo() }, [loadProjectInfo, refreshKey])

    // SSE 구독
    useEffect(() => {
        const unsub = subscribeSSE(
            () => {
                setRefreshKey(k => k + 1)
            },
            {
                onOpen: () => setConnected(true),
                onError: () => setConnected(false),
            },
        )
        return () => { unsub(); setConnected(false) }
    }, [])

    const title = projectInfo?.project_info?.title || '미로드'

    return (
        <div className="app-layout">
            <aside className="sidebar">
                <div className="sidebar-header">
                    <h1>PIXEL WRITER HUB</h1>
                    <div className="subtitle">{title}</div>
                </div>
                <nav className="sidebar-nav">
                    {NAV_ITEMS.map(item => (
                        <button
                            key={item.id}
                            className={`nav-item ${page === item.id ? 'active' : ''}`}
                            onClick={() => setPage(item.id)}
                        >
                            <span className="icon">{item.icon}</span>
                            <span>{item.label}</span>
                        </button>
                    ))}
                </nav>
                <div className="live-indicator">
                    <span className={`live-dot ${connected ? '' : 'disconnected'}`} />
                    {connected ? '실시간 동기화 중' : '미연결'}
                </div>
            </aside>

            <main className="main-content">
                {page === 'dashboard' && <DashboardPage data={projectInfo} key={refreshKey} />}
                {page === 'entities' && <EntitiesPage key={refreshKey} />}
                {page === 'graph' && <GraphPage key={refreshKey} />}
                {page === 'chapters' && <ChaptersPage key={refreshKey} />}
                {page === 'files' && <FilesPage />}
                {page === 'reading' && <ReadingPowerPage key={refreshKey} />}
            </main>
        </div>
    )
}

const NAV_ITEMS = [
    { id: 'dashboard', icon: '📊', label: '데이터 총람' },
    { id: 'entities', icon: '👤', label: '설정 사전' },
    { id: 'graph', icon: '🕸️', label: '관계 그래프' },
    { id: 'chapters', icon: '📝', label: '챕터 목록' },
    { id: 'files', icon: '📁', label: '문서 탐색' },
    { id: 'reading', icon: '🔥', label: '추독력' },
]

const FULL_DATA_GROUPS = [
    { key: 'entities', title: '엔티티', columns: ['id', 'canonical_name', 'type', 'tier', 'first_appearance', 'last_appearance'], domain: 'core' },
    { key: 'chapters', title: '챕터', columns: ['chapter', 'title', 'word_count', 'location', 'characters'], domain: 'core' },
    { key: 'scenes', title: '장면', columns: ['chapter', 'scene_index', 'location', 'time', 'summary'], domain: 'core' },
    { key: 'aliases', title: '별명', columns: ['alias', 'entity_id', 'entity_type'], domain: 'core' },
    { key: 'stateChanges', title: '상태 변화', columns: ['entity_id', 'field', 'old_value', 'new_value', 'chapter'], domain: 'core' },
    { key: 'relationships', title: '관계', columns: ['from_entity', 'to_entity', 'type', 'chapter', 'description'], domain: 'network' },
    { key: 'relationshipEvents', title: '관계 이벤트', columns: ['from_entity', 'to_entity', 'type', 'chapter', 'event_type', 'description'], domain: 'network' },
    { key: 'readingPower', title: '추독력', columns: ['chapter', 'hook_type', 'hook_strength', 'is_transition', 'override_count', 'debt_balance'], domain: 'network' },
    { key: 'overrides', title: 'Override 계약', columns: ['chapter', 'constraint_type', 'constraint_id', 'due_chapter', 'status'], domain: 'network' },
    { key: 'debts', title: '추독 부채', columns: ['id', 'debt_type', 'current_amount', 'interest_rate', 'due_chapter', 'status'], domain: 'network' },
    { key: 'debtEvents', title: '부채 이벤트', columns: ['debt_id', 'event_type', 'amount', 'chapter', 'note'], domain: 'network' },
    { key: 'reviewMetrics', title: '심사 지표', columns: ['start_chapter', 'end_chapter', 'overall_score', 'severity_counts', 'created_at'], domain: 'quality' },
    { key: 'invalidFacts', title: '무효 사실', columns: ['source_type', 'source_id', 'reason', 'status', 'chapter_discovered'], domain: 'quality' },
    { key: 'checklistScores', title: '작문 체크리스트 점수', columns: ['chapter', 'template', 'score', 'completion_rate', 'completed_items', 'total_items'], domain: 'quality' },
    { key: 'ragQueries', title: 'RAG 쿼리 로그', columns: ['query_type', 'query', 'results_count', 'latency_ms', 'chapter', 'created_at'], domain: 'ops' },
    { key: 'toolStats', title: '도구 호출 통계', columns: ['tool_name', 'success', 'retry_count', 'error_code', 'chapter', 'created_at'], domain: 'ops' },
]

const FULL_DATA_DOMAINS = [
    { id: 'overview', label: '총람' },
    { id: 'core', label: '기본 파일' },
    { id: 'network', label: '관계와 스토리' },
    { id: 'quality', label: '품질 심사' },
    { id: 'ops', label: 'RAG 및 도구' },
]


// ====================================================================
// 페이지 1: 데이터 총람
// ====================================================================

function DashboardPage({ data }) {
    if (!data) return <div className="loading">로딩 중…</div>

    const info = data.project_info || {}
    const progress = data.progress || {}
    const protagonist = data.protagonist_state || {}
    const strand = data.strand_tracker || {}
    const foreshadowing = data.plot_threads?.foreshadowing || []

    const totalWords = progress.total_words || 0
    const targetWords = info.target_words || 2000000
    const pct = targetWords > 0 ? Math.min(100, (totalWords / targetWords * 100)).toFixed(1) : 0

    const unresolvedForeshadow = foreshadowing.filter(f => {
        const s = (f.status || '').toLowerCase()
        return s !== '已回收' && s !== '已兑现' && s !== 'resolved'
    })

    // Strand 히스토리 통계
    const history = strand.history || []
    const strandCounts = { quest: 0, fire: 0, constellation: 0 }
    history.forEach(h => { if (strandCounts[h.strand] !== undefined) strandCounts[h.strand]++ })
    const total = history.length || 1

    return (
        <>
            <div className="page-header">
                <h2>📊 데이터 총람</h2>
                <span className="card-badge badge-blue">{info.genre || '미정 장르'}</span>
            </div>

            <div className="dashboard-grid">
                <div className="card stat-card">
                    <span className="stat-label">총 글자 수</span>
                    <span className="stat-value">{formatNumber(totalWords)}</span>
                    <span className="stat-sub">목표 {formatNumber(targetWords)} 자 · {pct}%</span>
                    <div className="progress-track">
                        <div className="progress-fill" style={{ width: `${pct}%` }} />
                    </div>
                </div>

                <div className="card stat-card">
                    <span className="stat-label">현재 챕터</span>
                    <span className="stat-value">제 {progress.current_chapter || 0} 장</span>
                    <span className="stat-sub">목표 {info.target_chapters || '?'} 장 · 권 {progress.current_volume || 1}</span>
                </div>

                <div className="card stat-card">
                    <span className="stat-label">주인공 상태</span>
                    <span className="stat-value plain">{protagonist.name || '미설정'}</span>
                    <span className="stat-sub">
                        {protagonist.power?.realm || '미지 경계'}
                        {protagonist.location?.current ? ` · ${protagonist.location.current}` : ''}
                    </span>
                </div>

                <div className="card stat-card">
                    <span className="stat-label">미회수 복선</span>
                    <span className="stat-value" style={{ color: unresolvedForeshadow.length > 10 ? 'var(--accent-red)' : 'var(--accent-amber)' }}>
                        {unresolvedForeshadow.length}
                    </span>
                    <span className="stat-sub">총 {foreshadowing.length} 개 복선</span>
                </div>
            </div>

            {/* Strand Weave 비율 */}
            <div className="card dashboard-section-card">
                <div className="card-header">
                    <span className="card-title">Strand Weave 리듬 분포</span>
                    <span className="card-badge badge-purple">{strand.current_dominant || '?'}</span>
                </div>
                <div className="strand-bar">
                    <div className="segment strand-quest" style={{ width: `${(strandCounts.quest / total * 100).toFixed(1)}%` }} />
                    <div className="segment strand-fire" style={{ width: `${(strandCounts.fire / total * 100).toFixed(1)}%` }} />
                    <div className="segment strand-constellation" style={{ width: `${(strandCounts.constellation / total * 100).toFixed(1)}%` }} />
                </div>
                <div className="strand-legend">
                    <span>🔵 Quest {(strandCounts.quest / total * 100).toFixed(0)}%</span>
                    <span>🔴 Fire {(strandCounts.fire / total * 100).toFixed(0)}%</span>
                    <span>🟣 Constellation {(strandCounts.constellation / total * 100).toFixed(0)}%</span>
                </div>
            </div>

            {/* 복선 목록 */}
            {unresolvedForeshadow.length > 0 ? (
                <div className="card dashboard-section-card">
                    <div className="card-header">
                        <span className="card-title">⚠️ 미회수 복선 (Top 20)</span>
                    </div>
                    <div className="table-wrap">
                        <table className="data-table">
                            <thead><tr><th>내용</th><th>상태</th><th>설치 챕터</th></tr></thead>
                            <tbody>
                                {unresolvedForeshadow.slice(0, 20).map((f, i) => (
                                    <tr key={i}>
                                        <td className="truncate" style={{ maxWidth: 400 }}>{f.content || f.description || '—'}</td>
                                        <td><span className="card-badge badge-amber">{f.status || '미정'}</span></td>
                                        <td>{f.chapter || f.planted_chapter || '—'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            ) : null}

            <MergedDataView />
        </>
    )
}


// ====================================================================
// 페이지 2: 설정 사전
// ====================================================================

function EntitiesPage() {
    const [entities, setEntities] = useState([])
    const [typeFilter, setTypeFilter] = useState('')
    const [selected, setSelected] = useState(null)
    const [changes, setChanges] = useState([])

    useEffect(() => {
        fetchJSON('/api/entities').then(setEntities).catch(() => { })
    }, [])

    useEffect(() => {
        if (selected) {
            fetchJSON('/api/state-changes', { entity: selected.id, limit: 30 }).then(setChanges).catch(() => setChanges([]))
        }
    }, [selected])

    const types = [...new Set(entities.map(e => e.type))].sort()
    const filteredEntities = typeFilter ? entities.filter(e => e.type === typeFilter) : entities

    return (
        <>
            <div className="page-header">
                <h2>👤 설정 사전</h2>
                <span className="card-badge badge-green">{filteredEntities.length} / {entities.length} 개 엔티티</span>
            </div>

            <div className="filter-group">
                <button className={`filter-btn ${typeFilter === '' ? 'active' : ''}`} onClick={() => setTypeFilter('')}>전체</button>
                {types.map(t => (
                    <button key={t} className={`filter-btn ${typeFilter === t ? 'active' : ''}`} onClick={() => setTypeFilter(t)}>{t}</button>
                ))}
            </div>

            <div className="split-layout">
                <div className="split-main">
                    <div className="card">
                        <div className="table-wrap">
                            <table className="data-table">
                                <thead><tr><th>이름</th><th>유형</th><th>등급</th><th>첫 등장</th><th>마지막 등장</th></tr></thead>
                                <tbody>
                                    {filteredEntities.map(e => (
                                        <tr
                                            key={e.id}
                                            role="button"
                                            tabIndex={0}
                                            className={`entity-row ${selected?.id === e.id ? 'selected' : ''}`}
                                            onKeyDown={evt => (evt.key === 'Enter' || evt.key === ' ') && (evt.preventDefault(), setSelected(e))}
                                            onClick={() => setSelected(e)}
                                        >
                                            <td className={e.is_protagonist ? 'entity-name protagonist' : 'entity-name'}>
                                                {e.canonical_name} {e.is_protagonist ? '⭐' : ''}
                                            </td>
                                            <td><span className="card-badge badge-blue">{e.type}</span></td>
                                            <td>{e.tier}</td>
                                            <td>{e.first_appearance || '—'}</td>
                                            <td>{e.last_appearance || '—'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {selected && (
                    <div className="split-side">
                        <div className="card">
                            <div className="card-header">
                                <span className="card-title">{selected.canonical_name}</span>
                                <span className="card-badge badge-purple">{selected.tier}</span>
                            </div>
                            <div className="entity-detail">
                                <p><strong>유형:</strong>{selected.type}</p>
                                <p><strong>ID:</strong><code>{selected.id}</code></p>
                                {selected.desc && <p className="entity-desc">{selected.desc}</p>}
                                {selected.current_json && (
                                    <div className="entity-current-block">
                                        <strong>현재 상태:</strong>
                                        <pre className="entity-json">
                                            {formatJSON(selected.current_json)}
                                        </pre>
                                    </div>
                                )}
                            </div>
                            {changes.length > 0 ? (
                                <div className="entity-history">
                                    <div className="card-title">상태 변화 이력</div>
                                    <div className="table-wrap">
                                        <table className="data-table">
                                            <thead><tr><th>장</th><th>필드</th><th>변화</th></tr></thead>
                                            <tbody>
                                                {changes.map((c, i) => (
                                                    <tr key={i}>
                                                        <td>{c.chapter}</td>
                                                        <td>{c.field}</td>
                                                        <td>{c.old_value} → {c.new_value}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            ) : null}
                        </div>
                    </div>
                )}
            </div>
        </>
    )
}


// ====================================================================
// 페이지 3: 3D 우주 관계 그래프
// ====================================================================

function GraphPage() {
    const [relationships, setRelationships] = useState([])
    const [graphData, setGraphData] = useState({ nodes: [], links: [] })

    useEffect(() => {
        Promise.all([
            fetchJSON('/api/relationships', { limit: 1000 }),
            fetchJSON('/api/entities'),
        ]).then(([rels, ents]) => {
            setRelationships(rels)
            const typeColors = {
                '角色': '#4f8ff7', '地点': '#34d399', '星球': '#22d3ee', '神仙': '#f59e0b',
                '势力': '#8b5cf6', '招式': '#ef4444', '法宝': '#ec4899'
            }
            const relatedIds = new Set()
            rels.forEach(r => { relatedIds.add(r.from_entity); relatedIds.add(r.to_entity) })
            const entityMap = {}
            ents.forEach(e => { entityMap[e.id] = e })

            const nodes = [...relatedIds].map(id => ({
                id,
                name: entityMap[id]?.canonical_name || id,
                val: (entityMap[id]?.tier === 'S' ? 8 : entityMap[id]?.tier === 'A' ? 5 : 2),
                color: typeColors[entityMap[id]?.type] || '#5c6078'
            }))
            const links = rels.map(r => ({
                source: r.from_entity,
                target: r.to_entity,
                name: r.type
            }))
            setGraphData({ nodes, links })
        }).catch(() => { })
    }, [])

    return (
        <>
            <div className="page-header">
                <h2>🕸️ 관계 그래프</h2>
                <span className="card-badge badge-blue">{relationships.length} 개 인력 링크</span>
            </div>
            <div className="card graph-shell">
                <ForceGraph3D
                    graphData={graphData}
                    nodeLabel="name"
                    nodeColor="color"
                    nodeRelSize={6}
                    linkColor={() => 'rgba(127, 90, 240, 0.35)'}
                    linkWidth={1}
                    linkDirectionalParticles={2}
                    linkDirectionalParticleWidth={1.5}
                    linkDirectionalParticleSpeed={d => 0.005 + Math.random() * 0.005}
                    backgroundColor="#fffaf0"
                    showNavInfo={false}
                />
            </div>
        </>
    )
}



// ====================================================================
// 페이지 4: 챕터 목록
// ====================================================================

function ChaptersPage() {
    const [chapters, setChapters] = useState([])

    useEffect(() => {
        fetchJSON('/api/chapters').then(setChapters).catch(() => { })
    }, [])

    const totalWords = chapters.reduce((s, c) => s + (c.word_count || 0), 0)

    return (
        <>
            <div className="page-header">
                <h2>📝 챕터 목록</h2>
                <span className="card-badge badge-green">{chapters.length} 장 · {formatNumber(totalWords)} 자</span>
            </div>
            <div className="card">
                <div className="table-wrap">
                    <table className="data-table">
                        <thead><tr><th>챕터</th><th>제목</th><th>글자 수</th><th>장소</th><th>등장인물</th></tr></thead>
                        <tbody>
                            {chapters.map(c => (
                                <tr key={c.chapter}>
                                    <td className="chapter-no">제 {c.chapter} 장</td>
                                    <td>{c.title || '—'}</td>
                                    <td>{formatNumber(c.word_count || 0)}</td>
                                    <td>{c.location || '—'}</td>
                                    <td className="truncate chapter-characters">{c.characters || '—'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {chapters.length === 0 ? <div className="empty-state"><div className="empty-icon">📭</div><p>챕터 데이터가 없습니다</p></div> : null}
            </div>
        </>
    )
}


// ====================================================================
// 페이지 5: 문서 탐색
// ====================================================================

function FilesPage() {
    const [tree, setTree] = useState({})
    const [selectedPath, setSelectedPath] = useState(null)
    const [content, setContent] = useState('')

    useEffect(() => {
        fetchJSON('/api/files/tree').then(setTree).catch(() => { })
    }, [])

    useEffect(() => {
        if (selectedPath) {
            fetchJSON('/api/files/read', { path: selectedPath })
                .then(d => setContent(d.content))
                .catch(() => setContent('[읽기 실패]'))
        }
    }, [selectedPath])

    useEffect(() => {
        if (selectedPath) return
        const first = findFirstFilePath(tree)
        if (first) setSelectedPath(first)
    }, [tree, selectedPath])

    return (
        <>
            <div className="page-header">
                <h2>📁 문서 탐색</h2>
            </div>
            <div className="file-layout">
                <div className="file-tree-pane">
                    {Object.entries(tree).map(([folder, items]) => (
                        <div key={folder} className="folder-block">
                            <div className="folder-title">📂 {folder}</div>
                            <ul className="file-tree">
                                <TreeNodes items={items} selected={selectedPath} onSelect={setSelectedPath} />
                            </ul>
                        </div>
                    ))}
                </div>
                <div className="file-content-pane">
                    {selectedPath ? (
                        <div>
                            <div className="selected-path">{selectedPath}</div>
                            <div className="file-preview">{content}</div>
                        </div>
                    ) : (
                        <div className="empty-state"><div className="empty-icon">📄</div><p>왼쪽 파일을 선택하여 내용을 미리보기</p></div>
                    )}
                </div>
            </div>
        </>
    )
}


// ====================================================================
// 페이지 6: 추독력
// ====================================================================

function ReadingPowerPage() {
    const [data, setData] = useState([])

    useEffect(() => {
        fetchJSON('/api/reading-power', { limit: 50 }).then(setData).catch(() => { })
    }, [])

    return (
        <>
            <div className="page-header">
                <h2>🔥 추독력 분석</h2>
                <span className="card-badge badge-amber">{data.length} 장 데이터</span>
            </div>
            <div className="card">
                <div className="table-wrap">
                    <table className="data-table">
                        <thead><tr><th>챕터</th><th>훅 유형</th><th>훅 강도</th><th>전환 챕터</th><th>Override</th><th>부채 잔액</th></tr></thead>
                        <tbody>
                            {data.map(r => (
                                <tr key={r.chapter}>
                                    <td className="chapter-no">제 {r.chapter} 장</td>
                                    <td>{r.hook_type || '—'}</td>
                                    <td>
                                        <span className={`card-badge ${r.hook_strength === 'strong' ? 'badge-green' : r.hook_strength === 'weak' ? 'badge-red' : 'badge-amber'}`}>
                                            {r.hook_strength || '—'}
                                        </span>
                                    </td>
                                    <td>{r.is_transition ? '✅' : '—'}</td>
                                    <td>{r.override_count || 0}</td>
                                    <td className={r.debt_balance > 0 ? 'debt-positive' : 'debt-normal'}>{(r.debt_balance || 0).toFixed(2)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {data.length === 0 ? <div className="empty-state"><div className="empty-icon">🔥</div><p>추독력 데이터가 없습니다</p></div> : null}
            </div>
        </>
    )
}

function findFirstFilePath(tree) {
    const roots = Object.values(tree || {})
    for (const items of roots) {
        const p = walkFirstFile(items)
        if (p) return p
    }
    return null
}

function walkFirstFile(items) {
    if (!Array.isArray(items)) return null
    for (const item of items) {
        if (item?.type === 'file' && item?.path) return item.path
        if (item?.type === 'dir' && Array.isArray(item.children)) {
            const p = walkFirstFile(item.children)
            if (p) return p
        }
    }
    return null
}


// ====================================================================
// 데이터 총람 내장: 전체 데이터 뷰
// ====================================================================

function MergedDataView() {
    const [loading, setLoading] = useState(true)
    const [payload, setPayload] = useState({})
    const [domain, setDomain] = useState('overview')

    useEffect(() => {
        let disposed = false

        async function loadAll() {
            setLoading(true)
            const requests = [
                ['entities', fetchJSON('/api/entities')],
                ['chapters', fetchJSON('/api/chapters')],
                ['scenes', fetchJSON('/api/scenes', { limit: 200 })],
                ['relationships', fetchJSON('/api/relationships', { limit: 300 })],
                ['relationshipEvents', fetchJSON('/api/relationship-events', { limit: 200 })],
                ['readingPower', fetchJSON('/api/reading-power', { limit: 100 })],
                ['reviewMetrics', fetchJSON('/api/review-metrics', { limit: 50 })],
                ['stateChanges', fetchJSON('/api/state-changes', { limit: 120 })],
                ['aliases', fetchJSON('/api/aliases')],
                ['overrides', fetchJSON('/api/overrides', { limit: 120 })],
                ['debts', fetchJSON('/api/debts', { limit: 120 })],
                ['debtEvents', fetchJSON('/api/debt-events', { limit: 150 })],
                ['invalidFacts', fetchJSON('/api/invalid-facts', { limit: 120 })],
                ['ragQueries', fetchJSON('/api/rag-queries', { limit: 150 })],
                ['toolStats', fetchJSON('/api/tool-stats', { limit: 200 })],
                ['checklistScores', fetchJSON('/api/checklist-scores', { limit: 120 })],
            ]

            const entries = await Promise.all(
                requests.map(async ([key, p]) => {
                    try {
                        const val = await p
                        return [key, val]
                    } catch {
                        return [key, []]
                    }
                }),
            )
            if (!disposed) {
                setPayload(Object.fromEntries(entries))
                setLoading(false)
            }
        }

        loadAll()
        return () => { disposed = true }
    }, [])

    if (loading) return <div className="loading">전체 데이터 로딩 중…</div>

    const groups = domain === 'overview'
        ? FULL_DATA_GROUPS
        : FULL_DATA_GROUPS.filter(g => g.domain === domain)
    const totalRows = FULL_DATA_GROUPS.reduce((sum, g) => sum + (payload[g.key] || []).length, 0)
    const nonEmptyGroups = FULL_DATA_GROUPS.filter(g => (payload[g.key] || []).length > 0).length
    const maxChapter = FULL_DATA_GROUPS.reduce((max, g) => {
        const rows = payload[g.key] || []
        rows.slice(0, 120).forEach(r => {
            const c = extractChapter(r)
            if (c > max) max = c
        })
        return max
    }, 0)
    const domainStats = FULL_DATA_DOMAINS.filter(d => d.id !== 'overview').map(d => {
        const ds = FULL_DATA_GROUPS.filter(g => g.domain === d.id)
        const rowCount = ds.reduce((sum, g) => sum + (payload[g.key] || []).length, 0)
        const filled = ds.filter(g => (payload[g.key] || []).length > 0).length
        return { ...d, rowCount, filled, total: ds.length }
    })

    return (
        <>
            <div className="page-header section-page-header">
                <h2>🧪 전체 데이터 뷰</h2>
                <span className="card-badge badge-cyan">{FULL_DATA_GROUPS.length} 개 데이터 소스</span>
            </div>

            <div className="demo-summary-grid">
                <div className="card stat-card">
                    <span className="stat-label">총 레코드 수</span>
                    <span className="stat-value">{formatNumber(totalRows)}</span>
                    <span className="stat-sub">현재 반환된 전체 데이터 행</span>
                </div>
                <div className="card stat-card">
                    <span className="stat-label">커버된 데이터 소스</span>
                    <span className="stat-value plain">{nonEmptyGroups}/{FULL_DATA_GROUPS.length}</span>
                    <span className="stat-sub">데이터가 있는 테이블 / 전체 테이블 수</span>
                </div>
                <div className="card stat-card">
                    <span className="stat-label">최신 챕터 도달</span>
                    <span className="stat-value plain">{maxChapter > 0 ? `제 ${maxChapter} 장` : '—'}</span>
                    <span className="stat-sub">식별 가능한 chapter 필드 기준 추정</span>
                </div>
                <div className="card stat-card">
                    <span className="stat-label">현재 뷰</span>
                    <span className="stat-value plain">{FULL_DATA_DOMAINS.find(d => d.id === domain)?.label}</span>
                    <span className="stat-sub">{groups.length} 개 데이터 그룹</span>
                </div>
            </div>

            <div className="demo-domain-tabs">
                {FULL_DATA_DOMAINS.map(item => (
                    <button
                        key={item.id}
                        className={`demo-domain-tab ${domain === item.id ? 'active' : ''}`}
                        onClick={() => setDomain(item.id)}
                    >
                        {item.label}
                    </button>
                ))}
            </div>

            {domain === 'overview' ? (
                <div className="demo-domain-grid">
                    {domainStats.map(ds => (
                        <div className="card" key={ds.id}>
                            <div className="card-header">
                                <span className="card-title">{ds.label}</span>
                                <span className="card-badge badge-purple">{ds.filled}/{ds.total}</span>
                            </div>
                            <div className="domain-stat-number">{formatNumber(ds.rowCount)}</div>
                            <div className="stat-sub">해당 데이터 도메인의 총 레코드 수</div>
                        </div>
                    ))}
                </div>
            ) : null}

            {groups.map(g => {
                const count = (payload[g.key] || []).length
                return (
                    <div className="card demo-group-card" key={g.key}>
                        <div className="card-header">
                            <span className="card-title">{g.title}</span>
                            <span className={`card-badge ${count > 0 ? 'badge-blue' : 'badge-amber'}`}>{count} 건</span>
                        </div>
                        <MiniTable
                            rows={payload[g.key] || []}
                            columns={g.columns}
                            pageSize={12}
                        />
                    </div>
                )
            })}
        </>
    )
}

function MiniTable({ rows, columns, pageSize = 12 }) {
    const [page, setPage] = useState(1)

    useEffect(() => {
        setPage(1)
    }, [rows, columns, pageSize])

    if (!rows || rows.length === 0) {
        return <div className="empty-state compact"><p>데이터가 없습니다</p></div>
    }

    const totalPages = Math.max(1, Math.ceil(rows.length / pageSize))
    const safePage = Math.min(page, totalPages)
    const start = (safePage - 1) * pageSize
    const list = rows.slice(start, start + pageSize)

    return (
        <>
            <div className="table-wrap">
                <table className="data-table">
                    <thead>
                        <tr>{columns.map(c => <th key={c}>{c}</th>)}</tr>
                    </thead>
                    <tbody>
                        {list.map((row, i) => (
                            <tr key={i}>
                                {columns.map(c => (
                                    <td key={c} className="truncate" style={{ maxWidth: 240 }}>
                                        {formatCell(row?.[c])}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <div className="table-pagination">
                <button
                    className="page-btn"
                    type="button"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={safePage <= 1}
                >
                    이전 페이지
                </button>
                <span className="page-info">
                    {safePage} / {totalPages} 페이지 · 총 {rows.length} 건
                </span>
                <button
                    className="page-btn"
                    type="button"
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={safePage >= totalPages}
                >
                    다음 페이지
                </button>
            </div>
        </>
    )
}

function extractChapter(row) {
    if (!row || typeof row !== 'object') return 0
    const candidates = [
        row.chapter,
        row.start_chapter,
        row.end_chapter,
        row.chapter_discovered,
        row.first_appearance,
        row.last_appearance,
    ]
    for (const c of candidates) {
        const n = Number(c)
        if (Number.isFinite(n) && n > 0) return n
    }
    return 0
}


// ====================================================================
// 하위 컴포넌트: 파일 트리 재귀
// ====================================================================

function TreeNodes({ items, selected, onSelect, depth = 0 }) {
    const [expanded, setExpanded] = useState({})
    if (!items || items.length === 0) return null

    return items.map((item, i) => {
        const key = item.path || `${depth}-${i}`
        if (item.type === 'dir') {
            const isOpen = expanded[key]
            return (
                <li key={key}>
                    <div
                        className="tree-item"
                        role="button"
                        tabIndex={0}
                        onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), setExpanded(prev => ({ ...prev, [key]: !prev[key] })))}
                        onClick={() => setExpanded(prev => ({ ...prev, [key]: !prev[key] }))}
                    >
                        <span className="tree-icon">{isOpen ? '📂' : '📁'}</span>
                        <span>{item.name}</span>
                    </div>
                    {isOpen && item.children && (
                        <ul className="tree-children">
                            <TreeNodes items={item.children} selected={selected} onSelect={onSelect} depth={depth + 1} />
                        </ul>
                    )}
                </li>
            )
        }
        return (
            <li key={key}>
                <div
                    className={`tree-item ${selected === item.path ? 'active' : ''}`}
                    role="button"
                    tabIndex={0}
                    onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onSelect(item.path))}
                    onClick={() => onSelect(item.path)}
                >
                    <span className="tree-icon">📄</span>
                    <span>{item.name}</span>
                </div>
            </li>
        )
    })
}


// ====================================================================
// 유틸리티: 숫자 포맷
// ====================================================================

function formatNumber(n) {
    if (n >= 10000) return new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 1 }).format(n / 10000) + ' 만'
    return new Intl.NumberFormat('ko-KR').format(n)
}

function formatJSON(str) {
    try {
        return JSON.stringify(JSON.parse(str), null, 2)
    } catch {
        return str
    }
}

function formatCell(v) {
    if (v === null || v === undefined) return '—'
    if (typeof v === 'boolean') return v ? 'true' : 'false'
    if (typeof v === 'object') {
        try {
            return JSON.stringify(v)
        } catch {
            return String(v)
        }
    }
    const s = String(v)
    return s.length > 180 ? `${s.slice(0, 180)}...` : s
}
