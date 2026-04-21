/**
 * static/facts/js/dashboard.js
 * 역할:
 * - 분리된 dashboard 모듈들을 최종 부팅한다.
 * - 이 파일은 가장 마지막에 로드되어야 한다.
 */
(function (window) {
    "use strict";

    const App = window.FACTS_DASHBOARD;

    /**
     * DOM 준비 상태에 따라 bootstrap 시점을 안전하게 맞춘다.
     * defer 로 로드하든, body 끝에서 로드하든 둘 다 대응한다.
     */
    function start() {
        if (!App || typeof App.bootstrap !== "function") {
            console.error("[dashboard.js] FACTS_DASHBOARD.bootstrap 이 없습니다. script load order를 확인하십시오.");
            return;
        }
        App.bootstrap();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start, { once: true });
    } else {
        start();
    }
})(window);
