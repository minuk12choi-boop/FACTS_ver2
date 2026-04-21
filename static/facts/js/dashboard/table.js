/**
 * dashboard/table.js
 * 역할:
 * - PRP 테이블을 렌더링한다.
 * - PRP only 조회를 처리한다.
 * - shift 범위 체크, 셀 키보드 이동 같은 테이블 UX를 담당한다.
 */
(function (window) {
    "use strict";

    const App = window.FACTS_DASHBOARD;
    let prpLastCheckedIndex = null;

    /** PRP 결과가 없을 때 안내 문구를 tbody에 출력한다. */
    App.renderEmptyPrpMessage = function renderEmptyPrpMessage(message) {
        const tbody = App.qs("prpDashboardTbody");
        if (!tbody) return;
        tbody.innerHTML = `<tr><td colspan="37" class="empty-cell">${App.escapeHtml(message)}</td></tr>`;
    };

    /**
     * PRP 결과 rows 를 HTML table 로 렌더링한다.
     * 버튼 셀은 이후 bindDynamicButtons 에서 실제 이벤트를 붙인다.
     */
    App.renderTable = function renderTable(rows) {
        App.state.currentRows = rows || [];

        if (!rows || rows.length === 0) {
            App.renderEmptyPrpMessage("조회 결과가 없습니다.");
            return;
        }

        let html = "";

        rows.forEach((row) => {
            html += `
                <tr
                    data-lineid="${App.escapeHtml(row.lineid || "")}"
                    data-processid="${App.escapeHtml(row.processid)}"
                    data-step="${App.escapeHtml(row.stepseq)}"
                    data-area="${App.escapeHtml(row.areaname)}"
                    data-layer="${App.escapeHtml(row.layerid)}"
                    data-descript="${App.escapeHtml(row.descript)}"
                    data-recipe="${App.escapeHtml(row.recipeid)}"
                    data-type="${App.escapeHtml(row.stepseq_type)}"
                    data-bodyflag="${App.escapeHtml(row.body_compat_flag)}"
                    data-chamflag="${App.escapeHtml(row.cham_compat_flag)}"
                    data-compattype="${App.escapeHtml(row.compat_type)}"
                    data-always="${App.escapeHtml(row.always_summary_text || `상시:0, 비상시:0`)}"
                    data-major="${App.escapeHtml(row.major_summary_text || `주요:0, 비주요:0`)}"
                    data-plan="${App.escapeHtml(row.plan_flag || "N")}"
                    data-tipmissing="${App.escapeHtml(row.tip_missing_flag || "N")}"
                >
                    <td class="center-cell"><input type="checkbox" class="row-check prp-row-check" tabindex="0"></td>
                    <td class="center-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.lineid || "")}</div></td>
                    <td class="center-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.processid)}</div></td>
                    <td class="center-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.areaname)}</div></td>
                    <td class="center-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.layerid)}</div></td>
                    <td class="center-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.stepseq)}</div></td>
                    <td class="center-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.skiprule)}</div></td>
                    <td class="left-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.descript)}</div></td>
                    <td class="left-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.recipeid)}</div></td>
                    <td class="center-cell eqpgroup-cell">
                        <div class="cell-readonly" tabindex="0">${row.eqpgroup_html || ""}</div>
                    </td>
                    <td class="center-cell">
                        <div class="cell-readonly cham-info-cell" tabindex="0">${row.cham_html || ""}</div>
                    </td>
                    <td class="center-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.stepseq_type)}</div></td>
                    <td class="center-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.body_compat_flag)}</div></td>
                    <td class="center-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.cham_compat_flag)}</div></td>
                    <td class="center-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.body_path_count)}</div></td>
                    <td class="center-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.cham_path_count)}</div></td>
                    <td class="center-cell compat-cell compat-${App.escapeHtml(row.compat_type)}">
                        <div class="cell-readonly compat-label-cell" tabindex="0">${App.escapeHtml(row.compat_type)}</div>
                    </td>
                    <td class="center-cell">
                        ${
                            row.override_editable
                                ? `
                                    <button
                                        type="button"
                                        class="cell-action-btn open-always-modal-btn"
                                        data-lineid="${App.escapeHtml(row.lineid || "")}"
                                        data-processid="${App.escapeHtml(row.processid)}"
                                        data-step="${App.escapeHtml(row.stepseq)}"
                                    >
                                        ${App.escapeHtml(row.always_summary_text || `상시:0, 비상시:0`)}
                                    </button>
                                `
                                : `
                                    <span
                                        class="disabled-action-tooltip-trigger"
                                        data-tooltip="${App.escapeHtml(row.override_disabled_reason || "")}"
                                        tabindex="0"
                                        style="display:inline-block;"
                                    >
                                        <button
                                            type="button"
                                            class="cell-action-btn"
                                            disabled
                                            style="pointer-events:none;"
                                        >
                                            ${App.escapeHtml(row.always_summary_text || `상시:0, 비상시:0`)}
                                        </button>
                                    </span>
                                `
                        }
                    </td>
                    <td class="center-cell">
                        ${
                            row.override_editable
                                ? `
                                    <button
                                        type="button"
                                        class="cell-action-btn open-major-modal-btn"
                                        data-lineid="${App.escapeHtml(row.lineid || "")}"
                                        data-processid="${App.escapeHtml(row.processid)}"
                                        data-step="${App.escapeHtml(row.stepseq)}"
                                    >
                                        ${App.escapeHtml(row.major_summary_text || `주요:0, 비주요:0`)}
                                    </button>
                                `
                                : `
                                    <span
                                        class="disabled-action-tooltip-trigger"
                                        data-tooltip="${App.escapeHtml(row.override_disabled_reason || "")}"
                                        tabindex="0"
                                        style="display:inline-block;"
                                    >
                                        <button
                                            type="button"
                                            class="cell-action-btn"
                                            disabled
                                            style="pointer-events:none;"
                                        >
                                            ${App.escapeHtml(row.major_summary_text || `주요:0, 비주요:0`)}
                                        </button>
                                    </span>
                                `
                        }
                    </td>
                    <td class="center-cell">
                        <button
                            type="button"
                            class="cell-action-btn open-plan-modal-btn"
                            data-lineid="${App.escapeHtml(row.lineid || "")}"
                            data-processid="${App.escapeHtml(row.processid)}"
                            data-step="${App.escapeHtml(row.stepseq)}"
                        >
                            ${App.escapeHtml(row.plan_flag || "N")}
                        </button>
                    </td>
                    <td class="left-cell"><div class="cell-readonly long-cell" tabindex="0">${App.escapeHtml(row.plan_body_names || "")}</div></td>
                    <td class="left-cell"><div class="cell-readonly long-cell" tabindex="0">${App.escapeHtml(row.plan_cham_names || "")}</div></td>
                    <td class="left-cell"><div class="cell-readonly long-cell" tabindex="0">${App.escapeHtml(row.plan_due_dates || "")}</div></td>
                    <td class="left-cell"><div class="cell-readonly long-cell" tabindex="0">${App.escapeHtml(row.plan_eval_lot_ids || "")}</div></td>
                    <td class="left-cell"><div class="cell-readonly long-cell" tabindex="0">${App.escapeHtml(row.plan_eval_stages || "")}</div></td>
                    <td class="left-cell"><div class="cell-readonly long-cell" tabindex="0">${App.escapeHtml(row.plan_memos || "")}</div></td>
                    <td class="center-cell">
                        <button
                            type="button"
                            class="cell-action-btn open-tip-missing-modal-btn"
                            data-lineid="${App.escapeHtml(row.lineid || "")}"
                            data-processid="${App.escapeHtml(row.processid)}"
                            data-step="${App.escapeHtml(row.stepseq)}"
                        >
                            ${App.escapeHtml(row.tip_missing_flag || "N")}
                        </button>
                    </td>
                    <td class="left-cell"><div class="cell-readonly long-cell" tabindex="0">${App.escapeHtml(row.tip_missing_always || "")}</div></td>
                    <td class="left-cell"><div class="cell-readonly long-cell" tabindex="0">${App.escapeHtml(row.tip_missing_major || "")}</div></td>
                    <td class="left-cell"><div class="cell-readonly long-cell" tabindex="0">${App.escapeHtml(row.tip_missing_body || "")}</div></td>
                    <td class="left-cell"><div class="cell-readonly long-cell" tabindex="0">${App.escapeHtml(row.tip_missing_cham || "")}</div></td>
                    <td class="center-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.body_compat_tip)}</div></td>
                    <td class="center-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.cham_compat_tip)}</div></td>
                    <td class="center-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.body_compat_count_tip)}</div></td>
                    <td class="center-cell"><div class="cell-readonly" tabindex="0">${App.escapeHtml(row.cham_compat_count_tip)}</div></td>
                    <td class="left-cell"><div class="cell-readonly long-cell" tabindex="0">${App.escapeHtml(row.tip || "")}</div></td>
                    <td class="left-cell"><div class="cell-readonly long-cell" tabindex="0">${App.escapeHtml(row.childeqp || "")}</div></td>
                </tr>
            `;
        });

        App.qs("prpDashboardTbody").innerHTML = html;
        App.bindPrpShiftRangeCheck();
        App.bindDynamicButtons();
        App.initCellKeyboardNavigation("#prpCellTable");
        if (window.bindFactsTooltipTargets) {
            window.bindFactsTooltipTargets(".disabled-action-tooltip-trigger");
        }
    };

    /**
     * PRP only API를 호출하고 테이블/옵션/다운로드 링크를 갱신한다.
     */
    App.refreshPrpTableOnly = async function refreshPrpTableOnly() {
        const validation = App.validatePrpSearchBeforeRequest();
        if (!validation.ok) {
            App.renderEmptyPrpMessage(validation.message);
            await App.showFactsMessage(validation.message);
            return;
        }

        try {
            App.showLoading();
            App.updateExportLinks();

            const data = await App.apiJson(App.buildDataApiUrl("prp"), "GET");

            App.renderFilterOptions(data);

            if (data.message) {
                App.renderEmptyPrpMessage(data.message);
                await App.showFactsMessage(data.message);
            } else if (data.rows && data.rows.length) {
                App.renderTable(data.rows);
            } else {
                App.renderEmptyPrpMessage("조회 결과가 없습니다.");
            }
        } catch (e) {
            console.error(e);
            App.hideLoading();
            await App.showFactsMessage(e.message || "조회 중 오류가 발생했습니다.");
        } finally {
            App.hideLoading();
        }
    };

    /**
     * row checkbox 에 shift 범위선택 기능을 붙인다.
     */
    App.bindPrpShiftRangeCheck = function bindPrpShiftRangeCheck() {
        const checks = Array.from(document.querySelectorAll(".prp-row-check"));

        checks.forEach((chk) => {
            chk.onclick = function (e) {
                const currentIndex = checks.indexOf(this);

                if (e.shiftKey && prpLastCheckedIndex !== null) {
                    const start = Math.min(prpLastCheckedIndex, currentIndex);
                    const end = Math.max(prpLastCheckedIndex, currentIndex);
                    const checkedValue = this.checked;

                    for (let i = start; i <= end; i++) {
                        checks[i].checked = checkedValue;
                    }
                }

                prpLastCheckedIndex = currentIndex;
            };
        });

        App.qs("prpCheckAll")?.addEventListener("change", function () {
            checks.forEach((chk) => {
                chk.checked = this.checked;
            });
        });
    };

    /**
     * 테이블 셀/체크박스에서 Ctrl + 방향키로 이동할 수 있게 한다.
     * 긴 텍스트 셀은 좌우 이동 전에 scroll 을 먼저 수행한다.
     */
    App.initCellKeyboardNavigation = function initCellKeyboardNavigation(tableSelector) {
        const table = document.querySelector(tableSelector);
        if (!table) return;
        const cells = Array.from(table.querySelectorAll(".cell-readonly, .row-check"));
        cells.forEach((cell) => {
            cell.addEventListener("keydown", function (e) {
                if (!e.ctrlKey) return;
                const current = e.currentTarget;
                const tr = current.closest("tr");
                if (!tr) return;
                const rowCells = Array.from(tr.querySelectorAll(".cell-readonly, .row-check"));
                const currentCol = rowCells.indexOf(current);
                const allRows = Array.from(table.querySelectorAll("tbody tr"));
                const currentRow = allRows.indexOf(tr);

                let target = null;

                if (e.key === "ArrowLeft") {
                    if (current.scrollWidth > current.clientWidth && current.classList.contains("cell-readonly")) {
                        current.scrollLeft = 0;
                    } else if (currentCol > 0) {
                        target = rowCells[currentCol - 1];
                    }
                } else if (e.key === "ArrowRight") {
                    if (current.scrollWidth > current.clientWidth && current.classList.contains("cell-readonly")) {
                        current.scrollLeft = current.scrollWidth;
                    } else if (currentCol < rowCells.length - 1) {
                        target = rowCells[currentCol + 1];
                    }
                } else if (e.key === "ArrowUp") {
                    for (let r = currentRow - 1; r >= 0; r--) {
                        const candidate = Array.from(allRows[r].querySelectorAll(".cell-readonly, .row-check"));
                        if (candidate[currentCol]) {
                            target = candidate[currentCol];
                            break;
                        }
                    }
                } else if (e.key === "ArrowDown") {
                    for (let r = currentRow + 1; r < allRows.length; r++) {
                        const candidate = Array.from(allRows[r].querySelectorAll(".cell-readonly, .row-check"));
                        if (candidate[currentCol]) {
                            target = candidate[currentCol];
                            break;
                        }
                    }
                }

                if (target) {
                    e.preventDefault();
                    target.focus();
                }
            });
        });
    };
})(window);
