/**
 * dashboard/tip_missing.js
 * 역할:
 * - TIP 미등록 호환Path 목록 modal / 수정 modal 을 관리한다.
 * - 조회, 추가, 수정, 삭제 흐름을 담당한다.
 */
(function (window) {
    "use strict";

    const App = window.FACTS_DASHBOARD;

    /** tip missing edit form 을 비운다. */
    App.clearTipMissingEditForm = function clearTipMissingEditForm() {
        App.qs("tipMissingEditId").value = "";
        App.qs("tipMissingAlwaysEmergency").value = "";
        App.qs("tipMissingMajorMinor").value = "";
        App.qs("tipMissingEqpBodyName").value = "";
        App.qs("tipMissingEqpChamName").value = "";
    };

    /** 선택한 row 데이터를 tip missing edit form 에 채운다. */
    App.fillTipMissingEditForm = function fillTipMissingEditForm(row) {
        if (!row) return;
        App.qs("tipMissingEditId").value = row.id || "";
        App.qs("tipMissingAlwaysEmergency").value = row.always_emergency || "";
        App.qs("tipMissingMajorMinor").value = row.major_minor || "";
        App.qs("tipMissingEqpBodyName").value = row.eqp_body_name || "";
        App.qs("tipMissingEqpChamName").value = row.eqp_cham_name || "";
    };

    /**
     * 현재 step 기준 tip missing 목록을 불러와 list modal tbody 를 채운다.
     * edit/delete 버튼도 함께 바인딩한다.
     */
    App.loadTipMissingList = async function loadTipMissingList(lineid, processid, stepseq) {
        const tipMissingListTbody = App.qs("tipMissingListTbody");
        tipMissingListTbody.innerHTML = `<tr><td colspan="6" class="empty-cell">불러오는 중...</td></tr>`;

        const url =
            `${App.state.dashboardApiUrls.dashboardTipMissingDetailApi}` +
            `?snap_date=${encodeURIComponent(App.getCurrentPrpSnapDate())}` +
            `&lineid=${encodeURIComponent(lineid || "")}` +
            `&processid=${encodeURIComponent(processid)}` +
            `&stepseq=${encodeURIComponent(stepseq)}`;

        const data = await App.apiJson(url, "GET");

        if (!data.rows.length) {
            tipMissingListTbody.innerHTML = `<tr><td colspan="6" class="empty-cell">입력된 미등록TIP호환Path가 없습니다.</td></tr>`;
            return;
        }

        tipMissingListTbody.innerHTML = data.rows.map((row) => `
            <tr>
                <td>${App.escapeHtml(row.always_emergency || "")}</td>
                <td>${App.escapeHtml(row.major_minor || "")}</td>
                <td>${App.escapeHtml(row.eqp_body_name || "")}</td>
                <td>${App.escapeHtml(row.eqp_cham_name || "")}</td>
                <td><button type="button" class="btn-secondary btn-sm tip-missing-edit-btn" data-id="${App.escapeHtml(row.id)}">수정</button></td>
                <td><button type="button" class="btn-secondary btn-sm tip-missing-delete-btn" data-id="${App.escapeHtml(row.id)}">삭제</button></td>
            </tr>
        `).join("");

        const rowMap = new Map(data.rows.map((r) => [String(r.id), r]));

        tipMissingListTbody.querySelectorAll(".tip-missing-edit-btn").forEach((btn) => {
            btn.addEventListener("click", async () => {
                if (!(await App.ensureCurrentPrpDateEditable())) return;
                const row = rowMap.get(String(btn.dataset.id));
                App.clearTipMissingEditForm();
                App.fillTipMissingEditForm(row);
                App.openModal(App.qs("tipMissingEditModal"));
            });
        });

        tipMissingListTbody.querySelectorAll(".tip-missing-delete-btn").forEach((btn) => {
            btn.addEventListener("click", async () => {
                if (!(await App.ensureCurrentPrpDateEditable())) return;
                const ok = await App.showFactsConfirm("해당 미등록TIP호환Path를 삭제하시겠습니까?");
                if (!ok) return;

                try {
                    App.showLoading();
                    await App.apiJson(App.state.dashboardApiUrls.dashboardTipMissingDeleteApi, "POST", {
                        snap_date: App.getCurrentPrpSnapDate(),
                        lineid: App.state.currentTipMissingTargetInfo.lineid,
                        tip_missing_id: btn.dataset.id,
                    });

                    await App.loadTipMissingList(
                        App.state.currentTipMissingTargetInfo.lineid,
                        App.state.currentTipMissingTargetInfo.processid,
                        App.state.currentTipMissingTargetInfo.stepseq
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

    /** tip missing modal 관련 이벤트를 초기화한다. */
    App.initTipMissingBindings = function initTipMissingBindings() {
        const tipMissingListModal = App.qs("tipMissingListModal");
        const tipMissingEditModal = App.qs("tipMissingEditModal");
        const tipMissingListCloseBtn = App.qs("tipMissingListCloseBtn");
        const tipMissingAddNewBtn = App.qs("tipMissingAddNewBtn");
        const tipMissingCancelBtn = App.qs("tipMissingCancelBtn");
        const tipMissingSaveBtn = App.qs("tipMissingSaveBtn");
        const tipMissingEqpBodyName = App.qs("tipMissingEqpBodyName");
        const tipMissingEqpChamName = App.qs("tipMissingEqpChamName");

        App.bindUppercaseInput(tipMissingEqpBodyName);
        App.bindUppercaseInput(tipMissingEqpChamName);

        App.stopEnterSubmitWithinModal(tipMissingListModal);
        App.stopEnterSubmitWithinModal(tipMissingEditModal);

        tipMissingListCloseBtn?.addEventListener("click", () => App.closeModal(tipMissingListModal));

        tipMissingAddNewBtn?.addEventListener("click", async () => {
            if (!(await App.ensureCurrentPrpDateEditable())) return;
            App.clearTipMissingEditForm();
            App.openModal(tipMissingEditModal);
        });

        tipMissingCancelBtn?.addEventListener("click", () => App.closeModal(tipMissingEditModal));

        tipMissingSaveBtn?.addEventListener("click", async () => {
            const tipMissingAlwaysEmergency = App.qs("tipMissingAlwaysEmergency");
            const tipMissingMajorMinor = App.qs("tipMissingMajorMinor");

            if (!(await App.ensureCurrentPrpDateEditable())) return;

            App.normalizeUpperInput(tipMissingEqpBodyName);
            App.normalizeUpperInput(tipMissingEqpChamName);

            if (!String(tipMissingAlwaysEmergency.value || "").trim()) {
                await App.showFactsMessage("상시/비상시는 필수기재입니다.");
                return;
            }

            if (!String(tipMissingMajorMinor.value || "").trim()) {
                await App.showFactsMessage("주요/비주요는 필수기재입니다.");
                return;
            }

            if (!String(tipMissingEqpBodyName.value || "").trim()) {
                await App.showFactsMessage("호환EQPBODY명은 필수기재입니다.");
                return;
            }

            try {
                App.showLoading();

                await App.apiJson(App.state.dashboardApiUrls.dashboardTipMissingSaveApi, "POST", {
                    snap_date: App.getCurrentPrpSnapDate(),
                    lineid: App.state.currentTipMissingTargetInfo.lineid,
                    tip_missing_id: App.qs("tipMissingEditId").value || "",
                    items: App.state.currentTipMissingTargetItems,
                    always_emergency: tipMissingAlwaysEmergency.value,
                    major_minor: tipMissingMajorMinor.value,
                    eqp_body_name: tipMissingEqpBodyName.value,
                    eqp_cham_name: tipMissingEqpChamName.value,
                });

                App.closeModal(tipMissingEditModal);

                await App.loadTipMissingList(
                    App.state.currentTipMissingTargetInfo.lineid,
                    App.state.currentTipMissingTargetInfo.processid,
                    App.state.currentTipMissingTargetInfo.stepseq
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
