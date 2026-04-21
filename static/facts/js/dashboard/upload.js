/**
 * dashboard/upload.js
 * 역할:
 * - 엑셀/CSV bulk upload modal 을 담당한다.
 * - FormData 방식 업로드와 성공 후 PRP 테이블 재조회까지 처리한다.
 */
(function (window) {
    "use strict";

    const App = window.FACTS_DASHBOARD;

    /** 업로드 modal 버튼과 저장 이벤트를 초기화한다. */
    App.initUploadBindings = function initUploadBindings() {
        const uploadModal = App.qs("uploadModal");

        App.qs("openUploadModalBtn")?.addEventListener("click", () => App.openModal(uploadModal));
        App.qs("uploadCancelBtn")?.addEventListener("click", () => App.closeModal(uploadModal));

        App.qs("uploadSaveBtn")?.addEventListener("click", async () => {
            const file = App.qs("bulkUploadFile").files[0];

            if (!file) {
                await App.showFactsMessage("파일을 선택하십시오.");
                return;
            }

            try {
                App.showLoading();

                const fd = new FormData();
                fd.append("file", file);
                fd.append("snap_date", App.state.dashboardMeta.snap_date);
                fd.append("lineid", App.getSelectedLineId());

                const res = await fetch(App.state.dashboardApiUrls.dashboardBulkUploadApi, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": App.getCsrfToken(),
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: fd,
                });

                const text = await res.text();

                let data = null;
                try {
                    data = JSON.parse(text);
                } catch (e) {
                    console.error("[dashboard.js] bulk upload non-json response:", {
                        status: res.status,
                        text: text,
                    });
                    throw new Error("서버 응답이 JSON 형식이 아닙니다. URL 또는 서버 응답을 확인하십시오.");
                }

                if (!res.ok || !data.ok) {
                    throw new Error(data.message || "업로드 실패");
                }

                App.closeModal(uploadModal);
                App.qs("bulkUploadFile").value = "";
                await App.refreshPrpTableOnly();
            } catch (e) {
                console.error(e);
                App.hideLoading();
                await App.showFactsMessage(e.message || "업로드 중 오류가 발생했습니다.");
            } finally {
                App.hideLoading();
            }
        });
    };
})(window);
