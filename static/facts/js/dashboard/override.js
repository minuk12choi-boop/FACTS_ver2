/**
 * dashboard/override.js
 * 역할:
 * - 상시/비상시, 주요/비주요 override modal 을 담당한다.
 * - 선택 row 기준 override 대상 member 목록을 렌더링하고 저장한다.
 */
(function (window) {
    "use strict";

    const App = window.FACTS_DASHBOARD;

    /** override modal 을 열기 전에 제목/대상 정보를 세팅한다. */
    App.openOverrideModal = function openOverrideModal(fieldType, lineid, processid, stepseq) {
        const overrideModal = App.qs("overrideModal");
        const overrideModalTitle = App.qs("overrideModalTitle");
        const overrideFieldType = App.qs("overrideFieldType");

        App.state.currentOverrideFieldType = fieldType;
        App.state.currentOverrideTargetInfo = { lineid, processid, stepseq };
        overrideFieldType.value = fieldType;
        overrideModalTitle.textContent = fieldType === "always_emergency" ? "상시/비상시 선택" : "주요/비주요 선택";

        const panel = overrideModal?.querySelector(".modal-panel");
        if (panel) {
            panel.style.width = "520px";
            panel.style.maxWidth = "92vw";
        }

        App.openModal(overrideModal);
    };

    /**
     * 이미 row 안에 들어있는 override_target_list 정보를 그대로 modal 목록으로 렌더링한다.
     * SOURCE_PATH 는 화면에서는 보이되 수정은 막고 tooltip 로 사유를 보여준다.
     */
    App.renderOverrideMembersFromRow = function renderOverrideMembersFromRow(row, fieldType) {
        const overrideMemberList = App.qs("overrideMemberList");
        if (!overrideMemberList) return;

        const items = Array.isArray(row?.override_target_list) ? row.override_target_list : [];
        if (!items.length) {
            overrideMemberList.innerHTML = `<div class="empty-cell">조회 결과가 없습니다.</div>`;
            return;
        }

        const labelY = fieldType === "always_emergency" ? "상시" : "주요";
        const labelN = fieldType === "always_emergency" ? "비상시" : "비주요";

        overrideMemberList.innerHTML = items.map((item) => {
            const sourceTypes = item.source_types || [];
            const isSourcePath = sourceTypes.includes("SOURCE_PATH");
            const isTipMissingOnly = sourceTypes.includes("TIP_MISSING") && !isSourcePath;

            const sourceDisplayParts = [];
            if (isSourcePath) sourceDisplayParts.push("TIP등록 Path");
            if (sourceTypes.includes("TIP_MISSING")) sourceDisplayParts.push("TIP미등록 호환Path");

            const current = isSourcePath
                ? "Y"
                : (
                    fieldType === "always_emergency"
                        ? (item.has_always ? "Y" : "N")
                        : (item.has_major ? "Y" : "N")
                );

            const disabledReason = "TIP등록된 설비는 상시, 주요 설정으로 변경이 불가합니다.";

            return `
                <div class="override-member-row" style="display:flex; align-items:center; justify-content:space-between; gap:8px; padding:8px 0;">
                    <div class="override-member-left" style="flex:1 1 auto; min-width:0;">
                        <div class="override-member-name" style="font-weight:700;">${App.escapeHtml(item.display_name || "")}</div>
                        <div class="override-member-source" style="font-size:11px; color:#6b7a90; max-width:120px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${App.escapeHtml(sourceDisplayParts.join(" / "))}">${App.escapeHtml(sourceDisplayParts.join(" / "))}</div>
                    </div>
                    <div class="override-member-right" style="flex:0 0 96px;">
                        ${
                            isTipMissingOnly
                                ? `
                                    <select
                                        class="override-member-flag"
                                        style="width:96px;"
                                        data-member-key="${App.escapeHtml(item.member_key || "")}"
                                        data-eqp-body-name="${App.escapeHtml(item.eqp_body_name || "")}"
                                        data-eqp-cham-name="${App.escapeHtml(item.eqp_cham_name || "")}"
                                        data-source-types='${App.escapeHtml(JSON.stringify(item.source_types || []))}'
                                        data-path-refs='${App.escapeHtml(JSON.stringify(item.path_refs || []))}'
                                    >
                                        <option value="Y" ${current === "Y" ? "selected" : ""}>${labelY}</option>
                                        <option value="N" ${current !== "Y" ? "selected" : ""}>${labelN}</option>
                                    </select>
                                `
                                : `
                                    <span
                                        class="disabled-action-tooltip-trigger"
                                        data-tooltip="${App.escapeHtml(disabledReason)}"
                                        tabindex="0"
                                        style="display:inline-block;"
                                    >
                                        <select
                                            class="override-member-flag"
                                            style="width:96px; pointer-events:none;"
                                            disabled
                                            data-member-key="${App.escapeHtml(item.member_key || "")}"
                                            data-eqp-body-name="${App.escapeHtml(item.eqp_body_name || "")}"
                                            data-eqp-cham-name="${App.escapeHtml(item.eqp_cham_name || "")}"
                                            data-source-types='${App.escapeHtml(JSON.stringify(item.source_types || []))}'
                                            data-path-refs='${App.escapeHtml(JSON.stringify(item.path_refs || []))}'
                                        >
                                            <option value="Y" selected>${labelY}</option>
                                            <option value="N">${labelN}</option>
                                        </select>
                                    </span>
                                `
                        }
                    </div>
                </div>
            `;
        }).join("");

        if (window.bindFactsTooltipTargets) {
            window.bindFactsTooltipTargets(".disabled-action-tooltip-trigger");
        }
    };

    /**
     * 서버 detail API를 호출해서 override member 목록을 가져온다.
     * 현재 구조에서는 row 안에 override_target_list 가 있어 주로 renderOverrideMembersFromRow 를 사용하지만,
     * API 기반이 필요할 때를 위해 유지한다.
     */
    App.loadOverrideMembers = async function loadOverrideMembers(lineid, processid, stepseq, fieldType) {
        const overrideMemberList = App.qs("overrideMemberList");
        const url =
            `${App.state.dashboardApiUrls.dashboardOverrideDetailApi}` +
            `?snap_date=${encodeURIComponent(App.getCurrentPrpSnapDate())}` +
            `&lineid=${encodeURIComponent(lineid || "")}` +
            `&processid=${encodeURIComponent(processid)}` +
            `&stepseq=${encodeURIComponent(stepseq)}`;

        const data = await App.apiJson(url, "GET");

        if (!overrideMemberList) return;

        if (!data.rows || !data.rows.length) {
            overrideMemberList.innerHTML = `<div class="empty-cell">조회 결과가 없습니다.</div>`;
            return;
        }

        const labelY = fieldType === "always_emergency" ? "상시" : "주요";
        const labelN = fieldType === "always_emergency" ? "비상시" : "비주요";

        overrideMemberList.innerHTML = data.rows.map((row) => {
            const current = fieldType === "always_emergency"
                ? (row.current_flag || "N")
                : (row.current_major_flag || "N");

            return `
                <div class="override-member-row">
                    <div class="override-member-left">
                        <div class="override-member-name">${App.escapeHtml(row.member_display || "")}</div>
                        <div class="override-member-source">${App.escapeHtml(row.source_display || "")}</div>
                    </div>
                    <div class="override-member-right">
                        <select
                            class="override-member-flag"
                            data-member-key="${App.escapeHtml(row.member_key || "")}"
                            data-eqp-body-name="${App.escapeHtml(row.eqp_body_name || "")}"
                            data-eqp-cham-name="${App.escapeHtml(row.eqp_cham_name || "")}"
                            data-source-types='${App.escapeHtml(JSON.stringify(row.source_types || []))}'
                            data-path-refs='${App.escapeHtml(JSON.stringify(row.path_refs || []))}'
                        >
                            <option value="Y" ${current === "Y" ? "selected" : ""}>${labelY}</option>
                            <option value="N" ${current !== "Y" ? "selected" : ""}>${labelN}</option>
                        </select>
                    </div>
                </div>
            `;
        }).join("");
    };

    /** override modal 버튼과 저장 이벤트를 초기화한다. */
    App.initOverrideBindings = function initOverrideBindings() {
        const overrideModal = App.qs("overrideModal");
        const overrideCancelBtn = App.qs("overrideCancelBtn");
        const overrideSaveBtn = App.qs("overrideSaveBtn");

        overrideCancelBtn?.addEventListener("click", () => App.closeModal(overrideModal));

        overrideSaveBtn?.addEventListener("click", async () => {
            if (!(await App.ensureCurrentPrpDateEditable())) return;
            const selected = Array.from(document.querySelectorAll(".override-member-flag")).map((el) => ({
                member_key: el.dataset.memberKey || "",
                eqp_body_name: el.dataset.eqpBodyName || "",
                eqp_cham_name: el.dataset.eqpChamName || "",
                source_types: JSON.parse(el.dataset.sourceTypes || "[]"),
                path_refs: JSON.parse(el.dataset.pathRefs || "[]"),
                selected_flag: el.value || "N",
            }));

            try {
                App.showLoading();
                await App.apiJson(App.state.dashboardApiUrls.dashboardOverrideMemberSaveApi, "POST", {
                    snap_date: App.getCurrentPrpSnapDate(),
                    lineid: App.state.currentOverrideTargetInfo.lineid,
                    processid: App.state.currentOverrideTargetInfo.processid,
                    stepseq: App.state.currentOverrideTargetInfo.stepseq,
                    field_type: App.state.currentOverrideFieldType,
                    member_items: selected,
                });
                App.closeModal(overrideModal);
                await App.refreshPrpTableOnly();
            } catch (e) {
                console.error(e);
                App.hideLoading();
                await App.showFactsMessage(e.message || "저장 중 오류가 발생했습니다.");
            } finally {
                App.hideLoading();
            }
        });

        App.stopEnterSubmitWithinModal(overrideModal);
    };
})(window);
