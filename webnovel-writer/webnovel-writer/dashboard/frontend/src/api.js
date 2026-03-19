/**
 * API 요청 유틸리티 함수
 */

const BASE = '';  // 개발 시 vite proxy가 FastAPI로 프록시

export async function fetchJSON(path, params = {}) {
    const url = new URL(path, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) url.searchParams.set(k, v);
    });
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
}

/**
 * SSE 실시간 이벤트 스트림 구독
 * @param {function} onMessage  data 수신 시 콜백
 * @param {{onOpen?: function, onError?: function}} handlers 연결 상태 콜백
 * @returns {function} 구독 해제 함수
 */
export function subscribeSSE(onMessage, handlers = {}) {
    const { onOpen, onError } = handlers
    const es = new EventSource(`${BASE}/api/events`);
    es.onopen = () => {
        if (onOpen) onOpen()
    };
    es.onmessage = (e) => {
        try {
            onMessage(JSON.parse(e.data));
        } catch { /* ignore parse errors */ }
    };
    es.onerror = (e) => {
        // EventSource가 자동으로 재연결합니다, 여기서는 연결 상태만 업데이트
        if (onError) onError(e)
    };
    return () => es.close();
}
