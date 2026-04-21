/**
 * dashboard/modals.js
 * 역할:
 * - 공용 메시지 modal / 확인 modal 을 제어한다.
 * - 다른 모듈에서 App.showFactsMessage / App.showFactsConfirm 으로 재사용한다.
 */
(function (window) {
    "use strict";

    const App = window.FACTS_DASHBOARD;

    /**
     * 단순 확인용 메시지 modal 을 띄운다.
     * 사용자가 확인 버튼을 누르면 Promise 가 resolve 된다.
     */
    App.showFactsMessage = function showFactsMessage(message, title = "FACTS의 메시지") {
        return new Promise((resolve) => {
            App.dom.factsMessageTitle.textContent = title;
            App.dom.factsMessageBody.textContent = message;
            App.openModal(App.dom.factsMessageModal);

            const handleOk = () => {
                App.dom.factsMessageOkBtn.removeEventListener("click", handleOk);
                App.closeModal(App.dom.factsMessageModal);
                resolve(true);
            };

            App.dom.factsMessageOkBtn.addEventListener("click", handleOk);
        });
    };

    /**
     * 예/아니오 확인 modal 을 띄운다.
     * 확인이면 true, 취소면 false 로 resolve 된다.
     */
    App.showFactsConfirm = function showFactsConfirm(message, title = "FACTS의 메시지") {
        return new Promise((resolve) => {
            App.dom.factsConfirmTitle.textContent = title;
            App.dom.factsConfirmBody.textContent = message;
            App.openModal(App.dom.factsConfirmModal);

            const cleanup = () => {
                App.dom.factsConfirmOkBtn.removeEventListener("click", handleOk);
                App.dom.factsConfirmCancelBtn.removeEventListener("click", handleCancel);
            };

            const handleOk = () => {
                cleanup();
                App.closeModal(App.dom.factsConfirmModal);
                resolve(true);
            };

            const handleCancel = () => {
                cleanup();
                App.closeModal(App.dom.factsConfirmModal);
                resolve(false);
            };

            App.dom.factsConfirmOkBtn.addEventListener("click", handleOk);
            App.dom.factsConfirmCancelBtn.addEventListener("click", handleCancel);
        });
    };

    /**
     * 공용 modal 들에 Enter submit 방지 로직을 붙인다.
     */
    App.initCommonModals = function initCommonModals() {
        App.stopEnterSubmitWithinModal(App.dom.factsMessageModal);
        App.stopEnterSubmitWithinModal(App.dom.factsConfirmModal);
    };
})(window);
