/**
 * dashboard/_base.js
 * 역할:
 * - dashboard 전역 네임스페이스를 만든다.
 * - 서버가 내려준 JSON 메타(script tag)를 읽는다.
 * - 여러 모듈에서 공통으로 쓰는 DOM/네트워크/문자열 헬퍼를 제공한다.
 *
 * 주의:
 * - 이 파일은 dashboard 관련 분리 파일 중 가장 먼저 로드되어야 한다.
 */
(function (window) {
    "use strict";

    const App = window.FACTS_DASHBOARD = window.FACTS_DASHBOARD || {};

    /**
     * 전역 상태 저장소.
     * 여러 모듈이 함께 참조하는 현재 차트, 현재 선택 row, 현재 modal 대상 정보 등을 보관한다.
     */
    App.state = App.state || {
        chart: null,
        currentPlanTargetItems: [],
        currentPlanTargetInfo: null,
        currentTipMissingTargetItems: [],
        currentTipMissingTargetInfo: null,
        currentOverrideTargetInfo: null,
        currentOverrideFieldType: "",
        guideCurrentIndex: 0,
        guideWheelLock: false,
        currentRows: [],
        metaLoaded: false,
        domLoaded: false,
    };

    /**
     * 자주 쓰는 DOM 요소 캐시.
     * bootstrap 시점에 채워지고 이후 각 모듈에서 재사용된다.
     */
    App.dom = App.dom || {};

    /**
     * id 기반 DOM 조회 함수.
     * 짧게 쓰기 위한 래퍼다.
     */
    App.qs = function qs(id) {
        return document.getElementById(id);
    };

    /**
     * script[type="application/json"] 같은 태그 안 JSON을 안전하게 읽는다.
     * 실패 시 fallback 값을 반환한다.
     */
    App.parseJsonScript = function parseJsonScript(id, fallback) {
        const el = App.qs(id);
        if (!el) return fallback;
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            console.error(`[dashboard.js] JSON parse failed: ${id}`, e);
            return fallback;
        }
    };

    /**
     * 서버가 내려준 메타 데이터를 1회만 읽어 App.state에 저장한다.
     */
    App.initMeta = function initMeta() {
        if (App.state.metaLoaded) return;

        App.state.dashboardMeta = App.parseJsonScript("dashboard-meta", {});
        App.state.guidePagesData = App.parseJsonScript("guide-pages-data", []);
        App.state.dashboardApiUrls = App.parseJsonScript("dashboard-api-urls", {});
        App.state.combinedSeries = App.parseJsonScript("facts-combined-series-data", {
            labels: [],
            total_values: [],
            body_values: [],
            cham_values: [],
            target_values: [],
        });

        App.state.metaLoaded = true;
    };

    /**
     * 자주 쓰는 DOM 참조를 App.dom 에 채운다.
     * DOM이 모두 준비된 이후 호출되어야 한다.
     */
    App.initDomRefs = function initDomRefs() {
        if (App.state.domLoaded) return;

        App.dom.prpWrap = App.qs("prpTableWrap");
        App.dom.factsMessageModal = App.qs("factsMessageModal");
        App.dom.factsMessageTitle = App.qs("factsMessageTitle");
        App.dom.factsMessageBody = App.qs("factsMessageBody");
        App.dom.factsMessageOkBtn = App.qs("factsMessageOkBtn");

        App.dom.factsConfirmModal = App.qs("factsConfirmModal");
        App.dom.factsConfirmTitle = App.qs("factsConfirmTitle");
        App.dom.factsConfirmBody = App.qs("factsConfirmBody");
        App.dom.factsConfirmCancelBtn = App.qs("factsConfirmCancelBtn");
        App.dom.factsConfirmOkBtn = App.qs("factsConfirmOkBtn");

        App.state.domLoaded = true;
    };

    /**
     * Django CSRF 토큰을 쿠키에서 읽는다.
     * POST/PUT/DELETE 성격 요청에 사용한다.
     */
    App.getCsrfToken = function getCsrfToken() {
        const cookie = document.cookie
            .split("; ")
            .find((row) => row.startsWith("csrftoken="));
        return cookie ? cookie.split("=")[1] : "";
    };

    /** 전역 로딩 UI를 연다. */
    App.showLoading = function showLoading() {
        if (window.showGlobalLoading) window.showGlobalLoading();
    };

    /** 전역 로딩 UI를 닫는다. */
    App.hideLoading = function hideLoading() {
        if (window.hideGlobalLoading) window.hideGlobalLoading();
    };

    /** modal wrapper에서 hidden 클래스를 제거한다. */
    App.openModal = function openModal(el) {
        if (el) el.classList.remove("hidden");
    };

    /** modal wrapper에 hidden 클래스를 추가한다. */
    App.closeModal = function closeModal(el) {
        if (el) el.classList.add("hidden");
    };

    /**
     * input 값을 즉시 대문자로 바꾼다.
     * BODY, CHAM, LOT ID처럼 서버에서 대문자 정규화를 기대하는 필드에 사용한다.
     */
    App.normalizeUpperInput = function normalizeUpperInput(el) {
        if (!el) return;
        el.value = String(el.value || "").toUpperCase();
    };

    /**
     * 사용자가 입력하는 도중에도 값이 대문자로 유지되도록 이벤트를 묶는다.
     */
    App.bindUppercaseInput = function bindUppercaseInput(el) {
        if (!el) return;
        el.addEventListener("input", () => {
            const start = el.selectionStart;
            const end = el.selectionEnd;
            el.value = String(el.value || "").toUpperCase();
            try {
                el.setSelectionRange(start, end);
            } catch (e) {
                // selection 복구가 불가능한 브라우저/상황은 무시
            }
        });
    };

    /**
     * modal 내부에서 textarea가 아닌 곳에서 Enter를 누를 때
     * 의도치 않은 form submit 이 일어나지 않도록 막는다.
     */
    App.stopEnterSubmitWithinModal = function stopEnterSubmitWithinModal(modalEl) {
        if (!modalEl) return;
        modalEl.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && e.target && e.target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    };

    /**
     * 서버 응답값을 HTML에 넣기 전에 이스케이프한다.
     * XSS 성격 문자열 삽입 방지용이다.
     */
    App.escapeHtml = function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    };

    /**
     * dashboard 공통 fetch 래퍼.
     * - JSON 응답만 허용한다.
     * - Django AJAX 헤더를 기본으로 넣는다.
     * - 오류 응답은 Error 로 통일한다.
     */
    App.apiJson = async function apiJson(url, method = "GET", body = null) {
        const options = {
            method,
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        };

        if (body !== null) {
            options.headers["Content-Type"] = "application/json";
            options.headers["X-CSRFToken"] = App.getCsrfToken();
            options.body = JSON.stringify(body);
        }

        const res = await fetch(url, options);
        const text = await res.text();

        let data = null;
        try {
            data = JSON.parse(text);
        } catch (e) {
            console.error("[dashboard.js] non-json response:", {
                url: url,
                status: res.status,
                text: text,
            });
            throw new Error("서버 응답이 JSON 형식이 아닙니다. URL 또는 서버 응답을 확인하십시오.");
        }

        if (!res.ok || !data.ok) {
            throw new Error(data.message || "요청 처리 중 오류가 발생했습니다.");
        }

        return data;
    };
})(window);
