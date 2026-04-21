/**
 * dashboard/plan.js
 * 역할:
 * - 호환계획 목록 modal / 수정 modal 을 관리한다.
 * - 조회, 추가, 수정, 삭제 흐름을 담당한다.
 */
(function (window) {
    "use strict";

    const App = window.FACTS_DASHBOARD;

    /** plan edit form 을 비운다. */
    App.clearPlanEditForm = function clearPlanEditForm() {
        App.qs("planEditId").value = "";
        App.qs("planAlwaysEmergency").value = "";
        App.qs("planMajorMinor").value = "";
        App.qs("planEqpBodyName").value = "";
        App.qs("planEqpChamName").value = "";
        App.qs("planDueDate").value = "";
        App.qs("planEvalLotId").value = "";
        App.qs("planEvalStage").value = "";
        App.qs("planMemo").value = "";
    };

    /** 선택한 row 데이터를 plan edit form 에 채운다. */
    App.fillPlanEditForm = function fillPlanEditForm(row) {
        if (!row) return;
        App.qs("planEditId").value = row.id || "";
        App.qs("planAlwaysEmergency").value = row.always_emergency || "";
        App.qs("planMajorMinor").value = row.major_minor || "";
        App.qs("planEqpBodyName").value = row.eqp_body_name || "";
        App.qs("planEqpChamName").value = row.eqp_cham_name || "";
        App.qs("planDueDate").value = row.compatibility_due_date || "";
        App.qs("planEvalLotId").value = row.eval_lot_id || "";
        App.qs("planEvalStage").value = row.required_eval_stage_id || "";
        App.qs("planMemo").value = row.memo || "";
    };

    /**
     * 현재 step 기준 plan 목록을 불러와 list modal tbody 를 채운다.
     * edit/delete 버튼까지 함께 바인딩한다.
     */
    App.loadPlanList = async function loadPlanList(lineid, processid, stepseq) {
        const planListTbody = App.qs("planListTbody");
        planListTbody.innerHTML = `<tr><td colspan="10" class="empty-cell">불러오는 중...</td></tr>`;

        const url =
            `${App.state.dashboardApiUrls.dashboardPlanDetailApi}` +
            `?snap_date=${encodeURIComponent(App.getCurrentPrpSnapDate())}` +
            `&lineid=${encodeURIComponent(lineid || "")}` +
            `&processid=${encodeURIComponent(processid)}` +
            `&stepseq=${encodeURIComponent(stepseq)}`;

        const data = await App.apiJson(url, "GET");

        if (!data.rows.length) {
            planListTbody.innerHTML = `<tr><td colspan="10" class="empty-cell">입력된 호환계획이 없습니다.</td></tr>`;
            return;
        }

        planListTbody.innerHTML = data.rows.map((row) => `
            <tr>
                <td>${App.escapeHtml(row.always_emergency || "")}</td>
                <td>${App.escapeHtml(row.major_minor || "")}</td>
                <td>${App.escapeHtml(row.eqp_body_name || "")}</td>
                <td>${App.escapeHtml(row.eqp_cham_name || "")}</td>
                <td>${App.escapeHtml(row.compatibility_due_date || "")}</td>
                <td>${App.escapeHtml(row.eval_lot_id || "")}</td>
                <td>${App.escapeHtml(row.required_eval_stage_name || "")}</td>
                <td>${App.escapeHtml(row.memo || "")}</td>
                <td><button type="button" class="btn-secondary btn-sm plan-edit-btn" data-id="${App.escapeHtml(row.id)}">수정</button></td>
                <td><button type="button" class="btn-secondary btn-sm plan-delete-btn" data-id="${App.escapeHtml(row.id)}">삭제</button></td>
            </tr>
        `).join("");

        const rowMap = new Map(data.rows.map((r) => [String(r.id), r]));

        planListTbody.querySelectorAll(".plan-edit-btn").forEach((btn) => {
            btn.addEventListener("click", async () => {
                if (!(await App.ensureCurrentPrpDateEditable())) return;
                const row = rowMap.get(String(btn.dataset.id));
                App.clearPlanEditForm();
                App.fillPlanEditForm(row);
                App.openModal(App.qs("planEditModal"));
            });
        });

        planListTbody.querySelectorAll(".plan-delete-btn").forEach((btn) => {
            btn.addEventListener("click", async () => {
                if (!(await App.ensureCurrentPrpDateEditable())) return;
                const ok = await App.showFactsConfirm("해당 호환계획을 삭제하시겠습니까?");
                if (!ok) return;

                try {
                    App.showLoading();
                    await App.apiJson(App.state.dashboardApiUrls.dashboardPlanDeleteApi, "POST", {
                        snap_date: App.getCurrentPrpSnapDate(),
                        lineid: App.state.currentPlanTargetInfo.lineid,
                        plan_id: btn.dataset.id,
                    });
                    await App.loadPlanList(
                        App.state.currentPlanTargetInfo.lineid,
                        App.state.currentPlanTargetInfo.processid,
                        App.state.currentPlanTargetInfo.stepseq
                    );
                    await App.refreshPrpTableOnly();
                } catch (e) {
                    console.error(e);
                    App.hideLoading();
                    await App.showFactsMessage(e.message || "삭제 중 오류가 발생했습니다.");
                } finally {
                    App.hideLoading();
                }
            });
        });
    };

    /** plan modal 관련 이벤트를 초기화한다. */
    App.initPlanBindings = function initPlanBindings() {
        const planListModal = App.qs("planListModal");
        const planEditModal = App.qs("planEditModal");
        const planListCloseBtn = App.qs("planListCloseBtn");
        const planAddNewBtn = App.qs("planAddNewBtn");
        const planCancelBtn = App.qs("planCancelBtn");
        const planSaveBtn = App.qs("planSaveBtn");

        App.bindUppercaseInput(App.qs("planEqpBodyName"));
        App.bindUppercaseInput(App.qs("planEqpChamName"));
        App.bindUppercaseInput(App.qs("planEvalLotId"));

        App.stopEnterSubmitWithinModal(planListModal);
        App.stopEnterSubmitWithinModal(planEditModal);

        planListCloseBtn?.addEventListener("click", () => App.closeModal(planListModal));

        planAddNewBtn?.addEventListener("click", async () => {
            if (!(await App.ensureCurrentPrpDateEditable())) return;
            App.clearPlanEditForm();
            App.openModal(planEditModal);
        });

        planCancelBtn?.addEventListener("click", () => App.closeModal(planEditModal));

        planSaveBtn?.addEventListener("click", async () => {
            const planEqpBodyName = App.qs("planEqpBodyName");
            const planEqpChamName = App.qs("planEqpChamName");
            const planEvalLotId = App.qs("planEvalLotId");

            if (!(await App.ensureCurrentPrpDateEditable())) return;
            App.normalizeUpperInput(planEqpBodyName);
            App.normalizeUpperInput(planEqpChamName);
            App.normalizeUpperInput(planEvalLotId);

            if (!String(planEqpBodyName.value || "").trim()) {
                await App.showFactsMessage("호환EQPBODY명은 필수기재입니다.");
                return;
            }

            try {
                App.showLoading();
                await App.apiJson(App.state.dashboardApiUrls.dashboardPlanSaveApi, "POST", {
                    snap_date: App.getCurrentPrpSnapDate(),
                    lineid: App.state.currentPlanTargetInfo.lineid,
                    plan_id: App.qs("planEditId").value || "",
                    items: App.state.currentPlanTargetItems,
                    always_emergency: App.qs("planAlwaysEmergency").value,
                    major_minor: App.qs("planMajorMinor").value,
                    eqp_body_name: planEqpBodyName.value,
                    eqp_cham_name: planEqpChamName.value,
                    compatibility_due_date: App.qs("planDueDate").value,
                    eval_lot_id: planEvalLotId.value,
                    required_eval_stage_id: App.qs("planEvalStage").value,
                    memo: App.qs("planMemo").value,
                });
                App.closeModal(planEditModal);
                await App.loadPlanList(
                    App.state.currentPlanTargetInfo.lineid,
                    App.state.currentPlanTargetInfo.processid,
                    App.state.currentPlanTargetInfo.stepseq
                );
                await App.refreshPrpTableOnly();
            } catch (e) {
                console.error(e);
                App.hideLoading();
                await App.showFactsMessage(e.message || "저장 중 오류가 발생했습니다.");
            } finally {
                App.hideLoading();
            }
        });
    };
})(window);
