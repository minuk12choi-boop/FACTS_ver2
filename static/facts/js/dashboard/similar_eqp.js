/**
 * dashboard/similar_eqp.js
 * 역할:
 * - 동종모델 추천 EQP 조회 modal 을 담당한다.
 * - 기준 EQP/MODEL과 추천 후보 목록을 화면에 보여준다.
 */
(function (window) {
    "use strict";

    const App = window.FACTS_DASHBOARD;

    /** 서버에서 유사 EQP 목록을 불러와 modal tbody 를 채운다. */
    App.loadSimilarEqpList = async function loadSimilarEqpList(lineid, processid, stepseq) {
        const similarEqpTbody = App.qs("similarEqpTbody");
        const similarEqpNotice = App.qs("similarEqpNotice");
        const similarEqpBaseInfo = App.qs("similarEqpBaseInfo");

        similarEqpTbody.innerHTML = `<tr><td colspan="6" class="empty-cell">불러오는 중...</td></tr>`;
        similarEqpBaseInfo.textContent = "";

        const url =
            `${App.state.dashboardApiUrls.dashboardSimilarEqpApi}` +
            `?snap_date=${encodeURIComponent(App.getCurrentPrpSnapDate())}` +
            `&lineid=${encodeURIComponent(lineid || "")}` +
            `&processid=${encodeURIComponent(processid)}` +
            `&stepseq=${encodeURIComponent(stepseq)}`;

        const data = await App.apiJson(url, "GET");

        similarEqpNotice.textContent = data.notice || "해당 추천은 GPM 등록된 EQP_MODEL을 기준으로 합니다.";

        const baseEqps = Array.isArray(data.base_eqps) ? data.base_eqps.join(", ") : "";
        const baseModels = Array.isArray(data.base_models) ? data.base_models.join(" / ") : "";
        similarEqpBaseInfo.textContent = `기준 EQP: ${baseEqps || "-"} | 기준 MODEL: ${baseModels || "-"}`;

        if (!data.rows || !data.rows.length) {
            similarEqpTbody.innerHTML = `<tr><td colspan="6" class="empty-cell">추천 가능한 EQP가 없습니다.</td></tr>`;
            return;
        }

        similarEqpTbody.innerHTML = data.rows.map((row) => `
            <tr>
                <td>${App.escapeHtml(row.eqp_id || "")}</td>
                <td>${App.escapeHtml(row.origin_line_id || "")}</td>
                <td>${App.escapeHtml(row.eqp_model || "")}</td>
                <td>${App.escapeHtml(row.match_type || "")}</td>
                <td>${row.match_score != null ? App.escapeHtml(row.match_score) : ""}</td>
                <td>${App.escapeHtml(row.matched_base_model || "")}</td>
            </tr>
        `).join("");
    };

    /** similar eqp modal 버튼과 close 이벤트를 초기화한다. */
    App.initSimilarEqpBindings = function initSimilarEqpBindings() {
        const openSimilarEqpBtn = App.qs("openSimilarEqpBtn");
        const similarEqpModal = App.qs("similarEqpModal");
        const similarEqpCloseBtn = App.qs("similarEqpCloseBtn");

        App.stopEnterSubmitWithinModal(similarEqpModal);

        openSimilarEqpBtn?.addEventListener("click", async () => {
            if (!App.state.currentPlanTargetInfo) {
                await App.showFactsMessage("먼저 호환계획 대상 step을 선택하십시오.");
                return;
            }

            try {
                App.showLoading();
                await App.loadSimilarEqpList(
                    App.state.currentPlanTargetInfo.lineid,
                    App.state.currentPlanTargetInfo.processid,
                    App.state.currentPlanTargetInfo.stepseq
                );
                App.openModal(similarEqpModal);
            } catch (e) {
                console.error(e);
                App.hideLoading();
                await App.showFactsMessage(e.message || "조회 중 오류가 발생했습니다.");
            } finally {
                App.hideLoading();
            }
        });

        similarEqpCloseBtn?.addEventListener("click", () => App.closeModal(similarEqpModal));
    };
})(window);
