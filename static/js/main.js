// Initialize any charts on the growth trend page
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the growth trend page
    const chartCanvas = document.getElementById('profitChart');
    
    if (chartCanvas && window.chartData) {
        const ctx = chartCanvas.getContext('2d');
        
        // Prepare data for chart
        const labels = window.chartData.map(item => item.month);
        const profits = window.chartData.map(item => item.profit);
        
        // Create gradient for chart - Orange theme
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(255, 107, 53, 0.3)');
        gradient.addColorStop(1, 'rgba(255, 140, 66, 0.05)');
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Monthly Profit (GHS)',
                    data: profits,
                    borderColor: '#ff6b35',
                    backgroundColor: gradient,
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#ff8c42',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 6,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            font: {
                                size: 12
                            },
                            color: '#ffffff'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return 'Profit: GHS ' + context.parsed.y.toFixed(2);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return 'GHS ' + value.toFixed(2);
                            },
                            font: {
                                size: 11
                            },
                            color: '#ffffff'
                        },
                        title: {
                            display: true,
                            text: 'Profit (GHS)',
                            font: {
                                size: 12
                            },
                            color: '#ff6b35'
                        },
                        grid: {
                            color: 'rgba(255,255,255,0.1)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Month',
                            font: {
                                size: 12
                            },
                            color: '#ff6b35'
                        },
                        ticks: {
                            font: {
                                size: 11
                            },
                            color: '#ffffff'
                        },
                        grid: {
                            display: false
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                elements: {
                    line: {
                        tension: 0.4
                    }
                }
            }
        });
    }
    
    // Add confirmation for delete actions
    const deleteButtons = document.querySelectorAll('.btn-danger, .btn-warning');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const action = this.classList.contains('btn-warning') ? 'settle/pay' : 'delete';
            if (!confirm(`Are you sure you want to ${action} this item?`)) {
                e.preventDefault();
            }
        });
    });
    
    // Auto-hide flash messages after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const closeButton = alert.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            }
        }, 5000);
    });
    
    // Format currency inputs
    const currencyInputs = document.querySelectorAll('input[type="number"][step="0.01"]');
    currencyInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value) {
                let value = parseFloat(this.value);
                if (!isNaN(value)) {
                    this.value = value.toFixed(2);
                }
            }
        });
    });
    
    // Validate form inputs before submission
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const numberInputs = this.querySelectorAll('input[type="number"]');
            for (let input of numberInputs) {
                if (input.value && parseFloat(input.value) < 0 && !input.hasAttribute('data-allow-negative')) {
                    alert('Please enter non-negative values only.');
                    e.preventDefault();
                    return false;
                }
            }
        });
    });
    
    // PIN input auto-submit (if on PIN page)
    const pinInput = document.querySelector('.pin-input');
    if (pinInput) {
        pinInput.addEventListener('input', function(e) {
            if (this.value.length === 4) {
                this.form.submit();
            }
        });
        
        // Add number pad styling
        pinInput.addEventListener('keypress', function(e) {
            if (!/[0-9]/.test(e.key)) {
                e.preventDefault();
            }
        });
    }
    
    // Add active class to current nav link
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.sidebar-nav .nav-link');
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && (href === currentPath || (currentPath !== '/' && href !== '/' && currentPath.startsWith(href)))) {
            link.classList.add('active');
        }
    });
    
    // Animate numbers on dashboard
    const numberElements = document.querySelectorAll('.card-text h2, .card-text h3, .stat-number');
    numberElements.forEach(el => {
        const originalText = el.innerText;
        const numberMatch = originalText.match(/\d+(?:\.\d+)?/);
        if (numberMatch) {
            const finalNumber = parseFloat(numberMatch[0]);
            if (!isNaN(finalNumber)) {
                let currentNumber = 0;
                const duration = 1000;
                const stepTime = 20;
                const steps = duration / stepTime;
                const increment = finalNumber / steps;
                
                let counter = 0;
                const timer = setInterval(() => {
                    counter++;
                    currentNumber += increment;
                    if (counter >= steps) {
                        currentNumber = finalNumber;
                        clearInterval(timer);
                    }
                    const newText = originalText.replace(/\d+(?:\.\d+)?/, currentNumber.toFixed(2));
                    el.innerText = newText;
                }, stepTime);
            }
        }
    });
});