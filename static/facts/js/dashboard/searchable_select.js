/**
 * dashboard/searchable_select.js
 * 역할:
 * - TomSelect 기반 searchable select 를 초기화한다.
 * - 동일 select 재초기화 시 기존 인스턴스를 destroy 한 뒤 다시 만든다.
 */
(function (window) {
    "use strict";

    const App = window.FACTS_DASHBOARD;

    /** 지정 scope 내부의 searchable-select 들을 TomSelect 로 감싼다. */
    App.initSearchableSelects = function initSearchableSelects(scope) {
        const root = scope || document;
        const selects = root.querySelectorAll("select.searchable-select");

        selects.forEach((el) => {
            if (el.tomselect) {
                el.tomselect.destroy();
            }

            new TomSelect(el, {
                create: false,
                allowEmptyOption: true,
                maxOptions: 5000,
                searchField: ["text"],
                valueField: "value",
                labelField: "text",
                sortField: [
                    { field: "text", direction: "asc" }
                ],
                placeholder: el.dataset.placeholder || "선택 또는 검색"
            });
        });
    };
})(window);
