/**
 * dashboard/tooltip.js
 * 역할:
 * - table header 도움말과 disabled 버튼 설명 tooltip 을 직접 띄운다.
 * - 동적으로 렌더링된 요소에도 재바인딩할 수 있게 window 함수로 노출한다.
 */
(function (window) {
    "use strict";

    const App = window.FACTS_DASHBOARD;

    /** tooltip 기능 전체를 초기화한다. */
    App.initHeaderTooltips = function initHeaderTooltips() {
        let tooltipEl = null;

        /** 현재 떠있는 tooltip DOM 을 제거한다. */
        function removeTooltip() {
            if (tooltipEl) {
                tooltipEl.remove();
                tooltipEl = null;
            }
        }

        /** tooltip DOM 을 생성하고 body 에 붙인다. */
        function createTooltip(text) {
            removeTooltip();
            tooltipEl = document.createElement("div");
            tooltipEl.className = "custom-th-tooltip";
            tooltipEl.textContent = text;
            document.body.appendChild(tooltipEl);
            return tooltipEl;
        }

        /** 기준 요소 위치에 맞게 tooltip 위치를 계산한다. */
        function positionTooltip(target) {
            if (!tooltipEl || !target) return;

            const rect = target.getBoundingClientRect();
            const tooltipRect = tooltipEl.getBoundingClientRect();

            let top = rect.top - tooltipRect.height - 8;
            let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);

            if (left < 8) left = 8;
            if (left + tooltipRect.width > window.innerWidth - 8) {
                left = window.innerWidth - tooltipRect.width - 8;
            }
            if (top < 8) top = rect.bottom + 8;

            tooltipEl.style.top = `${top}px`;
            tooltipEl.style.left = `${left}px`;
        }

        /**
         * selector 에 해당하는 요소들에 tooltip 이벤트를 붙인다.
         * 동적 렌더링 이후 재실행 가능하도록 외부에 노출한다.
         */
        function bindTooltipTargets(selector) {
            document.querySelectorAll(selector).forEach((el) => {
                if (el.dataset.tooltipBound === "1") return;
                el.dataset.tooltipBound = "1";

                el.addEventListener("mouseenter", () => {
                    const text = el.getAttribute("data-tooltip");
                    if (!text) return;
                    createTooltip(text);
                    positionTooltip(el);
                });
                el.addEventListener("mousemove", () => positionTooltip(el));
                el.addEventListener("mouseleave", removeTooltip);
                el.addEventListener("focus", () => {
                    const text = el.getAttribute("data-tooltip");
                    if (!text) return;
                    createTooltip(text);
                    positionTooltip(el);
                });
                el.addEventListener("blur", removeTooltip);
                el.addEventListener("click", () => {
                    const text = el.getAttribute("data-tooltip");
                    if (!text) return;
                    createTooltip(text);
                    positionTooltip(el);
                });
            });
        }

        bindTooltipTargets(".th-help");
        window.bindFactsTooltipTargets = bindTooltipTargets;

        window.addEventListener("scroll", removeTooltip, true);
        window.addEventListener("resize", removeTooltip);
    };
})(window);
