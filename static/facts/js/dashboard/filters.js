/**
 * dashboard/filters.js
 * 역할:
 * - 상단 대시보드 조회조건과 PRP 테이블 조회조건을 URL querystring 으로 조합한다.
 * - 필수 조건 검증과 필터 옵션 드롭다운 갱신을 담당한다.
 */
(function (window) {
    "use strict";

    const App = window.FACTS_DASHBOARD;

    /** 대시보드 상단 filter 의 LINE 값을 읽는다. */
    App.getSelectedLineId = function getSelectedLineId() {
        const form = App.qs("dashboardFilterForm");
        if (!form) return "";
        const el = form.querySelector('select[name="lineid"]');
        return el ? (el.value || "") : "";
    };

    /**
     * 상단 대시보드 요약/차트 조회용 querystring 을 만든다.
     * checkbox 는 명시적으로 1/0 으로 치환한다.
     */
    App.buildDashboardQueryString = function buildDashboardQueryString() {
        const form = App.qs("dashboardFilterForm");
        const fd = new FormData(form);

        ["include_measure", "include_emergency", "exclude_skiprule_100", "tip_mode"].forEach((name) => {
            fd.delete(name);
            const checked = form.querySelector(`input[name="${name}"][type="checkbox"]`)?.checked;
            fd.append(name, checked ? "1" : "0");
        });

        const params = new URLSearchParams();
        for (const [k, v] of fd.entries()) {
            params.set(k, v);
        }
        return params.toString();
    };

    /** PRP 테이블 기준일 값을 읽는다. */
    App.getCurrentPrpSnapDate = function getCurrentPrpSnapDate() {
        return App.qs("tblFilterSnapDate")?.value || App.state.dashboardMeta.snap_date || "";
    };

    /** 현재 PRP 조회 기준일이 수정 가능한 현재일인지 판단한다. */
    App.isCurrentPrpDateEditable = function isCurrentPrpDateEditable() {
        const selected = App.getCurrentPrpSnapDate();
        const today = App.state.dashboardMeta.snap_date || "";
        return !!selected && !!today && selected === today;
    };

    /**
     * 현재일이 아니면 수정 금지 메시지를 보여준다.
     * 저장/삭제 계열 액션에서 공통으로 사용한다.
     */
    App.ensureCurrentPrpDateEditable = async function ensureCurrentPrpDateEditable() {
        if (App.isCurrentPrpDateEditable()) {
            return true;
        }
        await App.showFactsMessage("현재일로 조회 후 수정바랍니다.");
        return false;
    };

    /** PRP 테이블 조회용 querystring 을 만든다. */
    App.buildPrpQueryString = function buildPrpQueryString() {
        const params = new URLSearchParams();
        const mapping = {
            prp_snap_date: App.qs("tblFilterSnapDate")?.value || "",
            prp_lineid: App.qs("tblFilterLine")?.value || "",
            prp_processid: App.qs("tblFilterPrp")?.value || "",
            prp_area: App.qs("tblFilterArea")?.value || "",
            prp_layer: App.qs("tblFilterLayer")?.value || "",
            prp_step: App.qs("tblFilterStep")?.value || "",
            prp_descript: App.qs("tblFilterDescript")?.value || "",
            prp_recipe: App.qs("tblFilterRecipe")?.value || "",
            prp_type: App.qs("tblFilterType")?.value || "",
            prp_body_flag: App.qs("tblFilterBodyFlag")?.value || "",
            prp_cham_flag: App.qs("tblFilterChamFlag")?.value || "",
            prp_compat_type: App.qs("tblFilterCompatType")?.value || "",
            prp_always: App.qs("tblFilterAlways")?.value || "",
            prp_major: App.qs("tblFilterMajor")?.value || "",
            prp_plan: App.qs("tblFilterPlan")?.value || "",
        };

        Object.entries(mapping).forEach(([k, v]) => {
            params.set(k, v);
        });

        return params.toString();
    };

    /**
     * PRP 테이블 조회 전 필수조건을 점검한다.
     * - PRP는 필수
     * - PRP 외 조건 최소 1개 필수
     */
    App.validatePrpSearchBeforeRequest = function validatePrpSearchBeforeRequest() {
        const prp = App.qs("tblFilterPrp")?.value || "";
        const others = [
            App.qs("tblFilterLine")?.value || "",
            App.qs("tblFilterArea")?.value || "",
            App.qs("tblFilterLayer")?.value || "",
            App.qs("tblFilterStep")?.value || "",
            App.qs("tblFilterDescript")?.value || "",
            App.qs("tblFilterRecipe")?.value || "",
            App.qs("tblFilterType")?.value || "",
            App.qs("tblFilterBodyFlag")?.value || "",
            App.qs("tblFilterChamFlag")?.value || "",
            App.qs("tblFilterCompatType")?.value || "",
            App.qs("tblFilterAlways")?.value || "",
            App.qs("tblFilterMajor")?.value || "",
            App.qs("tblFilterPlan")?.value || "",
        ];

        if (!prp) {
            return {
                ok: false,
                message: "PRP조건은 필수입니다."
            };
        }

        if (!others.some((x) => String(x).trim() !== "")) {
            return {
                ok: false,
                message: "PRP조건과 그 외 1개 이상의 필터 조건 선택 후 조회 해주십시오."
            };
        }

        return { ok: true, message: "" };
    };

    /** 상단 요약/차트 조회 전 PRP 선택 여부를 점검한다. */
    App.validateDashboardSummarySearch = function validateDashboardSummarySearch() {
        const prp = document.querySelector('select[name="processid"]')?.value || "";
        if (!String(prp).trim()) {
            return {
                ok: false,
                message: "PRP 선택은 필수조건입니다."
            };
        }
        return { ok: true, message: "" };
    };

    /**
     * data-api 호출 URL 을 만든다.
     * mode:
     * - summary: 요약/차트만 조회
     * - prp: PRP 테이블만 조회
     * - all: 둘 다 조회
     */
    App.buildDataApiUrl = function buildDataApiUrl(mode = "all") {
        const merged = new URLSearchParams();

        if (mode === "summary") {
            const dashboardQs = App.buildDashboardQueryString();
            for (const [k, v] of new URLSearchParams(dashboardQs).entries()) {
                merged.set(k, v);
            }
            merged.set("summary_only", "1");
        } else if (mode === "prp") {
            const prpQs = App.buildPrpQueryString();
            for (const [k, v] of new URLSearchParams(prpQs).entries()) {
                merged.set(k, v);
            }
            merged.set("prp_only", "1");
        } else {
            const dashboardQs = App.buildDashboardQueryString();
            const prpQs = App.buildPrpQueryString();

            for (const [k, v] of new URLSearchParams(dashboardQs).entries()) {
                merged.set(k, v);
            }
            for (const [k, v] of new URLSearchParams(prpQs).entries()) {
                merged.set(k, v);
            }
        }

        return `${App.state.dashboardApiUrls.dashboardDataApi}?${merged.toString()}`;
    };

    /**
     * 현재 PRP 필터 상태 기준으로 CSV 다운로드 URL 을 버튼에 박아 넣는다.
     */
    App.updateExportLinks = function updateExportLinks() {
        const filteredBtn = App.qs("prpExcelDownloadBtn");
        const allBtn = App.qs("prpExcelDownloadAllBtn");
        const prpQs = new URLSearchParams(App.buildPrpQueryString());

        if (filteredBtn) {
            filteredBtn.setAttribute(
                "data-export-url",
                `${App.state.dashboardApiUrls.prpExportCsvApi}?${prpQs.toString()}`
            );
        }

        if (allBtn) {
            const merged = new URLSearchParams();
            merged.set("prp_snap_date", App.qs("tblFilterSnapDate")?.value || "");
            merged.set("prp_lineid", App.qs("tblFilterLine")?.value || "");
            merged.set("prp_processid", App.qs("tblFilterPrp")?.value || "");
            allBtn.setAttribute(
                "data-export-url",
                `${App.state.dashboardApiUrls.prpExportCsvAllApi}?${merged.toString()}`
            );
        }
    };

    /**
     * 서버에서 받은 필터 옵션으로 select box 를 다시 채운다.
     * 이전 선택값이 살아있으면 그대로 복원한다.
     */
    App.renderFilterOptions = function renderFilterOptions(data) {
        const mappings = [
            ["tblFilterLine", data.table_line_options || [], "전체"],
            ["tblFilterPrp", data.table_prp_options || [], "선택"],
            ["tblFilterArea", data.table_area_options || [], "전체"],
            ["tblFilterLayer", data.table_layer_options || [], "전체"],
            ["tblFilterStep", data.table_step_options || [], "전체"],
            ["tblFilterType", data.table_type_options || [], "전체"],
        ];

        mappings.forEach(([id, values, placeholder]) => {
            const el = App.qs(id);
            if (!el) return;

            const prev = el.value;
            el.innerHTML =
                `<option value="">${placeholder}</option>` +
                values.map((v) => `<option value="${App.escapeHtml(v)}">${App.escapeHtml(v)}</option>`).join("");

            if (values.includes(prev)) {
                el.value = prev;
            } else {
                el.value = "";
            }
        });
    };

    /**
     * PRP 옵션만 별도로 새로 불러온다.
     * 필터 change 시 option 종속관계를 맞추기 위해 사용한다.
     */
    App.loadPrpOptionsOnly = async function loadPrpOptionsOnly() {
        const prpQs = App.buildPrpQueryString();
        const url = `${App.state.dashboardApiUrls.dashboardPrpOptionsApi}?${prpQs}`;
        const data = await App.apiJson(url, "GET");
        App.renderFilterOptions(data);
    };
})(window);
