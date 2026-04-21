/**
 * dashboard/bindings.js
 * 역할:
 * - 동적 버튼 클릭 이벤트를 row 데이터와 연결한다.
 * - 최초 bootstrap 시 필요한 모든 모듈 초기화/이벤트 바인딩을 수행한다.
 */
(function (window) {
    "use strict";

    const App = window.FACTS_DASHBOARD;

    /**
     * 테이블 내 동적으로 생성된 버튼들에 클릭 이벤트를 붙인다.
     * - override
     * - plan
     * - tip missing
     */
    App.bindDynamicButtons = function bindDynamicButtons() {
        document.querySelectorAll(".open-always-modal-btn").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const lineid = btn.dataset.lineid || "";
                const processid = btn.dataset.processid;
                const stepseq = btn.dataset.step;

                const row = App.state.currentRows.find(
                    (x) =>
                        (x.lineid || "") === lineid &&
                        x.processid === processid &&
                        x.stepseq === stepseq
                );

                if (!row) {
                    await App.showFactsMessage("조회 대상 row를 찾을 수 없습니다.");
                    return;
                }

                App.renderOverrideMembersFromRow(row, "always_emergency");
                App.openOverrideModal("always_emergency", lineid, processid, stepseq);
            });
        });

        document.querySelectorAll(".open-major-modal-btn").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const lineid = btn.dataset.lineid || "";
                const processid = btn.dataset.processid;
                const stepseq = btn.dataset.step;

                const row = App.state.currentRows.find(
                    (x) =>
                        (x.lineid || "") === lineid &&
                        x.processid === processid &&
                        x.stepseq === stepseq
                );

                if (!row) {
                    await App.showFactsMessage("조회 대상 row를 찾을 수 없습니다.");
                    return;
                }

                App.renderOverrideMembersFromRow(row, "major_minor");
                App.openOverrideModal("major_minor", lineid, processid, stepseq);
            });
        });

        document.querySelectorAll(".open-plan-modal-btn").forEach((btn) => {
            btn.addEventListener("click", async () => {
                App.state.currentPlanTargetItems = [{
                    lineid: btn.dataset.lineid || "",
                    processid: btn.dataset.processid,
                    stepseq: btn.dataset.step,
                }];
                App.state.currentPlanTargetInfo = App.state.currentPlanTargetItems[0];
                App.clearPlanEditForm();

                try {
                    App.showLoading();
                    await App.loadPlanList(
                        App.state.currentPlanTargetInfo.lineid,
                        App.state.currentPlanTargetInfo.processid,
                        App.state.currentPlanTargetInfo.stepseq
                    );
                    App.openModal(App.qs("planListModal"));
                } catch (e) {
                    console.error(e);
                    App.hideLoading();
                    await App.showFactsMessage(e.message || "조회 중 오류가 발생했습니다.");
                } finally {
                    App.hideLoading();
                }
            });
        });

        document.querySelectorAll(".open-tip-missing-modal-btn").forEach((btn) => {
            btn.addEventListener("click", async () => {
                App.state.currentTipMissingTargetItems = [{
                    lineid: btn.dataset.lineid || "",
                    processid: btn.dataset.processid,
                    stepseq: btn.dataset.step,
                }];
                App.state.currentTipMissingTargetInfo = App.state.currentTipMissingTargetItems[0];
                App.clearTipMissingEditForm();

                try {
                    App.showLoading();
                    await App.loadTipMissingList(
                        App.state.currentTipMissingTargetInfo.lineid,
                        App.state.currentTipMissingTargetInfo.processid,
                        App.state.currentTipMissingTargetInfo.stepseq
                    );
                    App.openModal(App.qs("tipMissingListModal"));
                } catch (e) {
                    console.error(e);
                    App.hideLoading();
                    await App.showFactsMessage(e.message || "조회 중 오류가 발생했습니다.");
                } finally {
                    App.hideLoading();
                }
            });
        });
    };

    /**
     * modal 안 Enter submit 방지 전역판.
     * 개별 modal 방지 로직의 보조 안전장치다.
     */
    App.preventUnexpectedEnterSubmit = function preventUnexpectedEnterSubmit() {
        document.addEventListener("keydown", function (e) {
            const target = e.target;
            if (!target) return;
            const inModal = target.closest(".modal");

            if (e.key === "Enter" && inModal && target.tagName !== "TEXTAREA") {
                e.preventDefault();
            }
        });
    };

    /**
     * 최초 로딩 시 필요한 정적 버튼/스크롤/필터 change 이벤트를 묶는다.
     */
    App.initStaticBindings = function initStaticBindings() {
        App.qs("prpScrollTopBtn")?.addEventListener("click", () => {
            App.dom.prpWrap?.scrollTo({ top: 0, behavior: "smooth" });
        });

        App.qs("prpScrollBottomBtn")?.addEventListener("click", () => {
            App.dom.prpWrap?.scrollTo({ top: App.dom.prpWrap.scrollHeight, behavior: "smooth" });
        });

        App.qs("dashboardSearchBtn")?.addEventListener("click", App.refreshSummaryOnly);
        App.qs("tblFilterSearchBtn")?.addEventListener("click", App.refreshPrpTableOnly);

        function exportByButton(buttonId) {
            const btn = App.qs(buttonId);
            const url = btn?.getAttribute("data-export-url");
            if (!url) return;
            window.location.href = url;
        }

        App.qs("prpExcelDownloadBtn")?.addEventListener("click", () => exportByButton("prpExcelDownloadBtn"));
        App.qs("prpExcelDownloadAllBtn")?.addEventListener("click", () => exportByButton("prpExcelDownloadAllBtn"));

        [
            "tblFilterSnapDate",
            "tblFilterLine",
            "tblFilterPrp",
            "tblFilterArea",
            "tblFilterLayer",
            "tblFilterStep",
            "tblFilterType",
            "tblFilterBodyFlag",
            "tblFilterChamFlag",
            "tblFilterCompatType",
            "tblFilterAlways",
            "tblFilterMajor",
            "tblFilterPlan",
        ].forEach((id) => {
            App.qs(id)?.addEventListener("change", async () => {
                try {
                    await App.loadPrpOptionsOnly();
                } catch (e) {
                    console.error(e);
                }
            });
        });
    };

    /**
     * dashboard 분리 모듈 전체를 한 번에 초기화한다.
     * 현재 템플릿이 기존 dashboard.js 1개만 보던 구조여도,
     * 마지막 bootstrap 파일만 호출되면 동작하도록 만든다.
     */
    App.bootstrap = function bootstrap() {
        App.initMeta();
        App.initDomRefs();
        App.initCommonModals();
        App.initGuideBindings();
        App.initHeaderTooltips();
        App.initOverrideBindings();
        App.initPlanBindings();
        App.initSimilarEqpBindings();
        App.initTipMissingBindings();
        App.initUploadBindings();
        App.initSearchableSelects(document);
        App.initStaticBindings();
        App.preventUnexpectedEnterSubmit();

        App.updateExportLinks();
        App.renderChart(App.state.combinedSeries);
        App.bindDynamicButtons();
        App.initCellKeyboardNavigation("#prpCellTable");

        App.loadPrpOptionsOnly().catch((e) => console.error(e));

        // 원본 코드 기준 최초 접속 자동조회는 의도적으로 막혀 있다.
    };
})(window);
