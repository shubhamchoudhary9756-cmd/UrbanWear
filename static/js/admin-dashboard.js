/* =====================================================
   Zenith — Admin Dashboard
   Revenue Chart + Top Product Bars
===================================================== */

(function () {
    'use strict';

    /* -----------------------------------------
       Revenue Chart
    ----------------------------------------- */
    function initRevenueChart() {
        var canvas = document.getElementById('revenueChart');
        if (!canvas) return;
        if (typeof Chart === 'undefined') return;

        var labels = [];
        var values = [];

        try {
            labels = JSON.parse(canvas.getAttribute('data-labels') || '[]');
            values = JSON.parse(canvas.getAttribute('data-values') || '[]');
        } catch (e) {
            console.error('[admin-dashboard] data parse error', e);
            return;
        }

        var ctx = canvas.getContext('2d');

        var gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(201, 169, 97, 0.35)');
        gradient.addColorStop(1, 'rgba(201, 169, 97, 0.02)');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Revenue (Rs.)',
                    data: values,
                    borderColor: '#c9a961',
                    backgroundColor: gradient,
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.35,
                    pointBackgroundColor: '#c9a961',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1a1a1a',
                        titleColor: '#c9a961',
                        bodyColor: '#faf8f5',
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            label: function (ctx) {
                                return 'Rs. ' + Number(ctx.parsed.y).toFixed(0);
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: {
                            color: '#888',
                            font: { size: 11, family: 'Inter' }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: '#f0ece6' },
                        ticks: {
                            color: '#888',
                            font: { size: 11, family: 'Inter' },
                            callback: function (val) {
                                return 'Rs. ' + val;
                            }
                        }
                    }
                }
            }
        });
    }

    /* -----------------------------------------
       Top Product Bars — data-width se fill karo
    ----------------------------------------- */
    function initTopProductBars() {
        var bars = document.querySelectorAll('.top-product-bar-fill[data-width]');
        for (var i = 0; i < bars.length; i++) {
            var w = parseFloat(bars[i].getAttribute('data-width')) || 0;
            bars[i].style.width = w + '%';
        }
    }

    /* -----------------------------------------
       Run on DOM ready
    ----------------------------------------- */
    function init() {
        initRevenueChart();
        initTopProductBars();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();