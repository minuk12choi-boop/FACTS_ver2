/**
 * dashboard/guide.js
 * 역할:
 * - 사용 가이드 modal 을 페이지 단위로 넘겨 보여준다.
 * - 버튼/휠 스크롤로 페이지 이동을 제어한다.
 */
(function (window) {
    "use strict";

    const App = window.FACTS_DASHBOARD;

    /** 현재 guide index 기준으로 이미지/페이지정보/UI 상태를 갱신한다. */
    App.renderGuidePage = function renderGuidePage() {
        const guidePages = Array.isArray(App.state.guidePagesData) ? App.state.guidePagesData : [];
        const guideModal = App.qs("guideModal");
        const guidePrevBtn = App.qs("guidePrevBtn");
        const guideNextBtn = App.qs("guideNextBtn");
        const guidePageInfo = App.qs("guidePageInfo");
        const guideImageViewer = App.qs("guideImageViewer");
        const guideEmptyMessage = App.qs("guideEmptyMessage");

        if (!guidePages.length) {
            guideImageViewer.classList.add("hidden");
            guideEmptyMessage.classList.remove("hidden");
            guidePageInfo.textContent = "0 / 0";
            guidePrevBtn.disabled = true;
            guideNextBtn.disabled = true;
            return;
        }

        const page = guidePages[App.state.guideCurrentIndex];
        guideImageViewer.src = page.image_url;
        guideImageViewer.classList.remove("hidden");
        guideEmptyMessage.classList.add("hidden");
        guidePageInfo.textContent = `${App.state.guideCurrentIndex + 1} / ${guidePages.length}`;
        guidePrevBtn.disabled = App.state.guideCurrentIndex === 0;
        guideNextBtn.disabled = App.state.guideCurrentIndex === guidePages.length - 1;

        // guideModal 변수는 함수 사용처를 맞추기 위해 읽어만 둔다.
        void guideModal;
    };

    /** guide modal 을 열기 전에 현재 페이지를 다시 렌더링한다. */
    App.openGuideModal = function openGuideModal() {
        App.renderGuidePage();
        App.openModal(App.qs("guideModal"));
    };

    /** guide 페이지를 앞/뒤로 이동한다. */
    App.moveGuidePage = function moveGuidePage(delta) {
        const guidePages = Array.isArray(App.state.guidePagesData) ? App.state.guidePagesData : [];
        if (!guidePages.length) return;
        const nextIndex = App.state.guideCurrentIndex + delta;
        if (nextIndex < 0 || nextIndex >= guidePages.length) return;
        App.state.guideCurrentIndex = nextIndex;
        App.renderGuidePage();
    };

    /** guide 관련 버튼/휠 이벤트를 초기화한다. */
    App.initGuideBindings = function initGuideBindings() {
        const calcInfoBtn = App.qs("calcInfoBtn");
        const guideModal = App.qs("guideModal");
        const guidePrevBtn = App.qs("guidePrevBtn");
        const guideNextBtn = App.qs("guideNextBtn");
        const guideCloseBtn = App.qs("guideCloseBtn");

        calcInfoBtn?.addEventListener("click", App.openGuideModal);
        guideCloseBtn?.addEventListener("click", () => App.closeModal(guideModal));
        guidePrevBtn?.addEventListener("click", () => App.moveGuidePage(-1));
        guideNextBtn?.addEventListener("click", () => App.moveGuidePage(1));

        guideModal?.addEventListener("wheel", (e) => {
            const guidePages = Array.isArray(App.state.guidePagesData) ? App.state.guidePagesData : [];
            if (!guidePages.length) return;
            e.preventDefault();

            if (App.state.guideWheelLock) return;
            App.state.guideWheelLock = true;

            if (e.deltaY > 0) App.moveGuidePage(1);
            else if (e.deltaY < 0) App.moveGuidePage(-1);

            setTimeout(() => {
                App.state.guideWheelLock = false;
            }, 180);
        }, { passive: false });

        App.stopEnterSubmitWithinModal(guideModal);
    };
})(window);
