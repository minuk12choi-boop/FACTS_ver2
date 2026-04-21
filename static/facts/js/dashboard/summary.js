/**
 * dashboard/summary.js
 * 역할:
 * - 상단 요약 카드 렌더링
 * - 메인 차트 렌더링
 * - summary_only API 호출 처리
 */
(function (window) {
    "use strict";

    const App = window.FACTS_DASHBOARD;

    /** 요약 카드 숫자를 화면에 뿌린다. */
    App.renderSummary = function renderSummary(data) {
        if (App.qs("summaryCompatRate")) {
            App.qs("summaryCompatRate").textContent = `${Number(data.summary?.compat_rate ?? 0).toFixed(1)}%`;
        }
        if (App.qs("summaryTotalSteps")) {
            App.qs("summaryTotalSteps").textContent = String(data.summary?.total_steps ?? 0);
        }
        if (App.qs("summarySingleCnt")) {
            App.qs("summarySingleCnt").textContent = String(data.summary?.single_cnt ?? 0);
        }
        if (App.qs("summaryBodyCnt")) {
            App.qs("summaryBodyCnt").textContent = String(data.summary?.body_cnt ?? 0);
        }
        if (App.qs("summaryChamCnt")) {
            App.qs("summaryChamCnt").textContent = String(data.summary?.cham_cnt ?? 0);
        }
        if (App.qs("summaryTargetMonthly")) {
            App.qs("summaryTargetMonthly").textContent =
                data.target_monthly === null || data.target_monthly === undefined
                    ? "-"
                    : `${Number(data.target_monthly).toFixed(1)}%`;
        }
    };

    /**
     * 메인 차트를 렌더링한다.
     * 월/주/일 구간 구분선과 TOTAL/BODY 값 라벨을 함께 표시한다.
     */
    App.renderChart = function renderChart(chartData) {
        const canvas = App.qs("factsMainChart");
        const emptyMsg = App.qs("chartEmptyMessage");

        if (!canvas) {
            console.error("[dashboard.js] #factsMainChart canvas not found");
            if (emptyMsg) {
                emptyMsg.textContent = "그래프 캔버스를 찾을 수 없습니다.";
                emptyMsg.classList.remove("hidden");
            }
            return;
        }

        if (typeof Chart === "undefined") {
            console.error("[dashboard.js] Chart is undefined. Chart.js 로드 여부를 확인하십시오.");
            if (emptyMsg) {
                emptyMsg.textContent = "Chart.js가 로드되지 않았습니다.";
                emptyMsg.classList.remove("hidden");
            }
            return;
        }

        const labels = chartData?.labels || [];
        const totalValues = chartData?.total_values || [];
        const bodyValues = chartData?.body_values || [];
        const chamValues = chartData?.cham_values || [];
        const targetValues = chartData?.target_values || [];

        const hasAnyXAxis = labels.length > 0;
        const hasAnyValue = [...totalValues, ...bodyValues, ...chamValues, ...targetValues].some(
            (v) => v !== null && v !== undefined
        );

        if (!hasAnyXAxis || !hasAnyValue) {
            if (emptyMsg) emptyMsg.classList.remove("hidden");
            if (App.state.chart) {
                App.state.chart.destroy();
                App.state.chart = null;
            }
            return;
        }

        if (emptyMsg) emptyMsg.classList.add("hidden");

        /**
         * 월/주/일 구간 사이에 얇은 세로선을 그리는 플러그인.
         */
        const segmentDividerPlugin = {
            id: "segmentDividerPlugin",
            afterDraw(chart) {
                const { ctx, scales } = chart;
                const x = scales.x;
                if (!x) return;

                const labels = chart.data.labels || [];
                const boundaries = [];
                for (let i = 1; i < labels.length; i++) {
                    const prev = labels[i - 1];
                    const curr = labels[i];
                    if ((prev === "" && curr !== "") || (prev !== "" && curr === "")) {
                        boundaries.push(i - 0.5);
                    }
                }

                ctx.save();
                ctx.strokeStyle = "rgba(15,93,160,0.18)";
                ctx.lineWidth = 1;

                boundaries.forEach((idx) => {
                    const xPos = x.getPixelForValue(idx);
                    ctx.beginPath();
                    ctx.moveTo(xPos, chart.chartArea.top);
                    ctx.lineTo(xPos, chart.chartArea.bottom);
                    ctx.stroke();
                });

                ctx.restore();
            }
        };

        /**
         * TOTAL/BODY 라인 값 위아래에 퍼센트 라벨을 직접 그리는 플러그인.
         */
        const smartValueLabelPlugin = {
            id: "smartValueLabelPlugin",
            afterDatasetsDraw(chart) {
                const { ctx } = chart;
                const totalMeta = chart.getDatasetMeta(0);
                const totalDataset = chart.data.datasets[0];
                const bodyMeta = chart.getDatasetMeta(1);
                const bodyDataset = chart.data.datasets[1];

                ctx.save();
                ctx.font = "12px Arial";
                ctx.textAlign = "center";

                totalMeta.data.forEach((point, index) => {
                    const totalVal = totalDataset.data[index];
                    if (totalVal === null || totalVal === undefined || Number.isNaN(totalVal)) return;
                    ctx.fillStyle = "#0f5da0";
                    ctx.textBaseline = "bottom";
                    ctx.fillText(`${Number(totalVal).toFixed(1)}%`, point.x, point.y - 8);
                });

                bodyMeta.data.forEach((point, index) => {
                    const bodyVal = bodyDataset.data[index];
                    if (bodyVal === null || bodyVal === undefined || Number.isNaN(bodyVal)) return;
                    ctx.fillStyle = "#22a06b";
                    ctx.textBaseline = "top";
                    ctx.fillText(`${Number(bodyVal).toFixed(1)}%`, point.x, point.y + 8);
                });

                ctx.restore();
            }
        };

        try {
            if (App.state.chart) {
                App.state.chart.destroy();
            }

            App.state.chart = new Chart(canvas.getContext("2d"), {
                type: "line",
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: "TOTAL",
                            data: totalValues,
                            borderWidth: 2,
                            tension: 0.15,
                            fill: false,
                            borderColor: "#0f5da0",
                            backgroundColor: "#0f5da0",
                            pointRadius: 3,
                            spanGaps: false,
                        },
                        {
                            label: "BODY",
                            data: bodyValues,
                            borderWidth: 2,
                            tension: 0.15,
                            fill: false,
                            borderColor: "#22a06b",
                            backgroundColor: "#22a06b",
                            pointRadius: 3,
                            spanGaps: false,
                        },
                        {
                            label: "CHAM",
                            data: chamValues,
                            borderWidth: 2,
                            tension: 0.15,
                            fill: false,
                            borderColor: "#6f42c1",
                            backgroundColor: "#6f42c1",
                            pointRadius: 3,
                            spanGaps: false,
                        },
                        {
                            label: "TARGET",
                            data: targetValues,
                            borderWidth: 2,
                            tension: 0,
                            fill: false,
                            borderColor: "#e55353",
                            backgroundColor: "#e55353",
                            borderDash: [8, 6],
                            pointRadius: 0,
                            spanGaps: false,
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    interaction: {
                        mode: "nearest",
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            position: "top"
                        },
                        tooltip: {
                            enabled: true,
                            callbacks: {
                                label: function (context) {
                                    if (context.raw === null || context.raw === undefined) return "";
                                    return `${context.dataset.label}: ${Number(context.raw).toFixed(1)}%`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                autoSkip: false,
                                maxRotation: 0,
                                minRotation: 0
                            }
                        },
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                },
                plugins: [smartValueLabelPlugin, segmentDividerPlugin]
            });
        } catch (e) {
            console.error("Chart render error:", e);
            if (emptyMsg) emptyMsg.classList.remove("hidden");
        }
    };

    /**
     * summary_only API를 호출해서 상단 카드/차트만 갱신한다.
     */
    App.refreshSummaryOnly = async function refreshSummaryOnly() {
        const validation = App.validateDashboardSummarySearch();
        if (!validation.ok) {
            await App.showFactsMessage(validation.message);
            return;
        }

        try {
            App.showLoading();
            const data = await App.apiJson(App.buildDataApiUrl("summary"), "GET");

            App.renderSummary(data);

            App.state.combinedSeries = data.combined_series || {
                labels: [],
                total_values: [],
                body_values: [],
                cham_values: [],
                target_values: [],
            };

            App.renderChart(App.state.combinedSeries);
        } catch (e) {
            console.error(e);
            App.hideLoading();
            await App.showFactsMessage(e.message || "조회 중 오류가 발생했습니다.");
        } finally {
            App.hideLoading();
        }
    };
})(window);
