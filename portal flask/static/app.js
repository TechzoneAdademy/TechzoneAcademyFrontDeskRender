/* ========================================
   TECHZONE ACADEMY - ENHANCED UI/UX JAVASCRIPT
   Premium Interactive Features & Accessibility
   Features: Theme System, Mobile UX, Toast Notifications
======================================== */

class TechZoneUI {
    constructor() {
        this.currentTheme = localStorage.getItem('techzone-theme') || 'light';
        this.isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        this.toastContainer = null;
        this.init();
    }

    init() {
        this.setupThemeSystem();
        this.setupToastSystem();
        this.setupAccessibility();
        this.setupMobileEnhancements();
        this.setupFormEnhancements();
        this.setupTableEnhancements();
        this.setupLoadingStates();
        this.setupAnimations();
    }

    // Theme System
    setupThemeSystem() {
        this.applyTheme(this.currentTheme);
        this.createThemeToggle();
        
        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (this.currentTheme === 'auto') {
                this.applyTheme('auto');
            }
        });
    }

    createThemeToggle() {
        // Don't show theme toggle on login page
        if (this.isLoginPage()) {
            return;
        }
        
        const themeToggle = document.createElement('div');
        themeToggle.className = 'theme-toggle';
        themeToggle.innerHTML = `
            <button type="button" data-theme="light" aria-label="Light Theme">
                <i class="fas fa-sun"></i>
            </button>
            <button type="button" data-theme="dark" aria-label="Dark Theme">
                <i class="fas fa-moon"></i>
            </button>
            <button type="button" data-theme="high-contrast" aria-label="High Contrast Theme">
                <i class="fas fa-adjust"></i>
            </button>
        `;

        document.body.appendChild(themeToggle);

        // Add event listeners
        themeToggle.addEventListener('click', (e) => {
            const button = e.target.closest('button');
            if (button) {
                const theme = button.dataset.theme;
                this.setTheme(theme);
            }
        });

        this.updateThemeToggle();
    }

    setTheme(theme) {
        this.currentTheme = theme;
        localStorage.setItem('techzone-theme', theme);
        this.applyTheme(theme);
        this.updateThemeToggle();
        this.showToast('Theme Changed', `Switched to ${theme} theme`, 'success');
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
    }

    updateThemeToggle() {
        const buttons = document.querySelectorAll('.theme-toggle button');
        buttons.forEach(button => {
            button.classList.toggle('active', button.dataset.theme === this.currentTheme);
        });
    }

    // Toast Notification System
    setupToastSystem() {
        this.toastContainer = document.createElement('div');
        this.toastContainer.className = 'toast-container';
        document.body.appendChild(this.toastContainer);
    }

    showToast(title, message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-header">
                <h6 class="toast-title">${title}</h6>
                <button type="button" class="toast-close" aria-label="Close">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="toast-body">${message}</div>
        `;

        this.toastContainer.appendChild(toast);

        // Show toast
        setTimeout(() => toast.classList.add('show'), 100);

        // Auto dismiss
        const dismissTimer = setTimeout(() => this.dismissToast(toast), duration);

        // Manual dismiss
        toast.querySelector('.toast-close').addEventListener('click', () => {
            clearTimeout(dismissTimer);
            this.dismissToast(toast);
        });

        return toast;
    }

    dismissToast(toast) {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    // Accessibility Enhancements
    setupAccessibility() {
        this.addSkipLink();
        this.enhanceKeyboardNavigation();
        this.addFocusManagement();
        this.setupScreenReaderSupport();
    }

    addSkipLink() {
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.className = 'skip-link';
        skipLink.textContent = 'Skip to main content';
        document.body.insertBefore(skipLink, document.body.firstChild);

        // Ensure main content has ID
        const main = document.querySelector('main') || document.querySelector('.container-fluid');
        if (main && !main.id) {
            main.id = 'main-content';
        }
    }

    enhanceKeyboardNavigation() {
        // Add keyboard support to cards
        document.querySelectorAll('.dashboard-card, .card').forEach(card => {
            if (!card.hasAttribute('tabindex')) {
                card.setAttribute('tabindex', '0');
            }

            card.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    const link = card.querySelector('a');
                    if (link) {
                        e.preventDefault();
                        link.click();
                    }
                }
            });
        });

        // Improve button keyboard navigation
        document.querySelectorAll('.btn-group').forEach(group => {
            const buttons = group.querySelectorAll('.btn');
            buttons.forEach((button, index) => {
                button.addEventListener('keydown', (e) => {
                    let targetIndex;
                    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                        targetIndex = (index + 1) % buttons.length;
                        e.preventDefault();
                    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                        targetIndex = (index - 1 + buttons.length) % buttons.length;
                        e.preventDefault();
                    }

                    if (targetIndex !== undefined) {
                        buttons[targetIndex].focus();
                    }
                });
            });
        });
    }

    addFocusManagement() {
        // Focus management for modals
        document.addEventListener('shown.bs.modal', (e) => {
            const firstInput = e.target.querySelector('input, select, textarea, button');
            if (firstInput) {
                firstInput.focus();
            }
        });

        // Visible focus indicators
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('using-keyboard');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('using-keyboard');
        });
    }

    setupScreenReaderSupport() {
        // Add live region for dynamic content
        const liveRegion = document.createElement('div');
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.className = 'sr-only';
        liveRegion.id = 'live-region';
        document.body.appendChild(liveRegion);

        // Announce important changes
        this.announceToScreenReader = (message) => {
            liveRegion.textContent = message;
            setTimeout(() => liveRegion.textContent = '', 1000);
        };
    }

    // Mobile Enhancements
    setupMobileEnhancements() {
        this.setupTouchGestures();
        this.setupMobileNavigation();
        this.setupPullToRefresh();
        this.setupResponsiveTables();
    }

    setupTouchGestures() {
        let startX, startY, startTime;

        document.addEventListener('touchstart', (e) => {
            const touch = e.touches[0];
            startX = touch.clientX;
            startY = touch.clientY;
            startTime = Date.now();
        });

        document.addEventListener('touchend', (e) => {
            if (!startX || !startY) return;

            const touch = e.changedTouches[0];
            const deltaX = touch.clientX - startX;
            const deltaY = touch.clientY - startY;
            const deltaTime = Date.now() - startTime;

            // Quick swipe detection
            if (Math.abs(deltaX) > 100 && deltaTime < 300) {
                if (deltaX > 0) {
                    this.handleSwipeRight();
                } else {
                    this.handleSwipeLeft();
                }
            }

            startX = startY = null;
        });
    }

    handleSwipeRight() {
        // Navigate back if applicable
        if (window.history.length > 1) {
            const backButton = document.querySelector('[data-action="back"]');
            if (backButton) {
                backButton.click();
            }
        }
    }

    handleSwipeLeft() {
        // Show mobile menu if applicable
        const mobileMenu = document.querySelector('.navbar-toggler');
        if (mobileMenu && !mobileMenu.classList.contains('collapsed')) {
            mobileMenu.click();
        }
    }

    setupMobileNavigation() {
        // Add mobile-friendly navigation
        const navbar = document.querySelector('.navbar');
        if (navbar && window.innerWidth < 768) {
            navbar.classList.add('mobile-nav');
        }

        // Handle orientation change
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.adjustForOrientation();
            }, 100);
        });
    }

    adjustForOrientation() {
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', `${vh}px`);
    }

    setupPullToRefresh() {
        if ('serviceWorker' in navigator) {
            let startY = 0;
            let refreshing = false;

            document.addEventListener('touchstart', (e) => {
                startY = e.touches[0].clientY;
            });

            document.addEventListener('touchmove', (e) => {
                const currentY = e.touches[0].clientY;
                const pullDistance = currentY - startY;

                if (pullDistance > 100 && window.scrollY === 0 && !refreshing) {
                    refreshing = true;
                    this.showToast('Refreshing', 'Updating content...', 'info', 2000);
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                }
            });
        }
    }

    setupResponsiveTables() {
        document.querySelectorAll('.table').forEach(table => {
            if (!table.closest('.table-responsive')) {
                const wrapper = document.createElement('div');
                wrapper.className = 'table-responsive';
                table.parentNode.insertBefore(wrapper, table);
                wrapper.appendChild(table);
            }
        });
    }

    // Form Enhancements
    setupFormEnhancements() {
        this.setupFloatingLabels();
        this.setupFileUpload();
        this.setupFormValidation();
        this.setupProgressBars();
    }

    setupFloatingLabels() {
        document.querySelectorAll('.form-floating').forEach(container => {
            const input = container.querySelector('input, textarea, select');
            const label = container.querySelector('label');

            if (input && label) {
                input.addEventListener('focus', () => {
                    container.classList.add('focused');
                });

                input.addEventListener('blur', () => {
                    container.classList.remove('focused');
                    if (input.value) {
                        container.classList.add('filled');
                    } else {
                        container.classList.remove('filled');
                    }
                });

                // Check initial state
                if (input.value) {
                    container.classList.add('filled');
                }
            }
        });
    }

    setupFileUpload() {
        document.querySelectorAll('input[type="file"]').forEach(input => {
            const wrapper = document.createElement('div');
            wrapper.className = 'file-drop-zone';
            wrapper.innerHTML = `
                <div class="file-drop-icon">
                    <i class="fas fa-cloud-upload-alt"></i>
                </div>
                <div class="file-drop-text">
                    Drop files here or click to browse
                </div>
                <div class="file-drop-hint">
                    Supported formats: PDF, DOCX, XLSX, PPTX, MP4
                </div>
            `;

            input.parentNode.insertBefore(wrapper, input);
            wrapper.appendChild(input);

            // Handle drag and drop
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                wrapper.addEventListener(eventName, this.handleDragEvent);
            });

            wrapper.addEventListener('drop', (e) => {
                e.preventDefault();
                wrapper.classList.remove('dragover');
                input.files = e.dataTransfer.files;
                this.updateFileDisplay(wrapper, input.files);
            });

            wrapper.addEventListener('click', () => {
                input.click();
            });

            input.addEventListener('change', () => {
                this.updateFileDisplay(wrapper, input.files);
            });
        });
    }

    handleDragEvent(e) {
        e.preventDefault();
        e.stopPropagation();

        if (e.type === 'dragenter' || e.type === 'dragover') {
            this.classList.add('dragover');
        } else {
            this.classList.remove('dragover');
        }
    }

    updateFileDisplay(wrapper, files) {
        const text = wrapper.querySelector('.file-drop-text');
        if (files.length > 0) {
            text.textContent = `${files.length} file(s) selected`;
            this.showToast('Files Selected', `Selected ${files.length} file(s)`, 'success');
        } else {
            text.textContent = 'Drop files here or click to browse';
        }
    }

    setupFormValidation() {
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', (e) => {
                const requiredFields = form.querySelectorAll('[required]');
                let isValid = true;

                requiredFields.forEach(field => {
                    if (!field.value.trim()) {
                        isValid = false;
                        field.classList.add('is-invalid');
                        this.showFieldError(field, 'This field is required');
                    } else {
                        field.classList.remove('is-invalid');
                        this.clearFieldError(field);
                    }
                });

                if (!isValid) {
                    e.preventDefault();
                    this.showToast('Validation Error', 'Please fill in all required fields', 'error');
                    return false;
                }

                this.showFormSubmitting(form);
            });
        });
    }

    showFieldError(field, message) {
        let errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            field.parentNode.appendChild(errorDiv);
        }
        errorDiv.textContent = message;
    }

    clearFieldError(field) {
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    showFormSubmitting(form) {
        const submitButton = form.querySelector('[type="submit"]');
        if (submitButton) {
            submitButton.innerHTML = '<span class="loading-spinner"></span> Processing...';
            submitButton.disabled = true;
        }
    }

    setupProgressBars() {
        document.querySelectorAll('.progress').forEach(progress => {
            const bar = progress.querySelector('.progress-bar');
            if (bar) {
                const value = bar.style.width || bar.getAttribute('data-value') + '%';
                this.animateProgressBar(bar, value);
            }
        });
    }

    animateProgressBar(bar, targetValue) {
        let currentValue = 0;
        const target = parseInt(targetValue);
        const increment = target / 50;

        const animate = () => {
            currentValue += increment;
            if (currentValue >= target) {
                currentValue = target;
            }
            bar.style.width = currentValue + '%';
            
            if (currentValue < target) {
                requestAnimationFrame(animate);
            }
        };

        if (!this.isReducedMotion) {
            animate();
        } else {
            bar.style.width = targetValue;
        }
    }

    // Table Enhancements
    setupTableEnhancements() {
        this.setupSortableTables();
        this.setupTableSearch();
        this.setupTablePagination();
    }

    setupSortableTables() {
        document.querySelectorAll('.data-table').forEach(table => {
            const headers = table.querySelectorAll('th[data-sortable]');
            headers.forEach(header => {
                header.classList.add('sort-header');
                header.addEventListener('click', () => {
                    this.sortTable(table, header);
                });
            });
        });
    }

    sortTable(table, header) {
        const columnIndex = Array.from(header.parentNode.children).indexOf(header);
        const rows = Array.from(table.querySelectorAll('tbody tr'));
        const isAscending = !header.classList.contains('asc');

        // Remove existing sort classes
        table.querySelectorAll('.sort-header').forEach(h => {
            h.classList.remove('asc', 'desc');
        });

        // Add sort class to current header
        header.classList.add(isAscending ? 'asc' : 'desc');

        // Sort rows
        rows.sort((a, b) => {
            const aValue = a.children[columnIndex].textContent.trim();
            const bValue = b.children[columnIndex].textContent.trim();
            
            const comparison = isNaN(aValue) ? 
                aValue.localeCompare(bValue) : 
                parseFloat(aValue) - parseFloat(bValue);
                
            return isAscending ? comparison : -comparison;
        });

        // Reappend sorted rows
        const tbody = table.querySelector('tbody');
        rows.forEach(row => tbody.appendChild(row));

        this.announceToScreenReader(`Table sorted by ${header.textContent} ${isAscending ? 'ascending' : 'descending'}`);
    }

    setupTableSearch() {
        document.querySelectorAll('.data-table-search input').forEach(searchInput => {
            const table = searchInput.closest('.data-table-container').querySelector('.data-table');
            
            searchInput.addEventListener('input', () => {
                this.filterTable(table, searchInput.value);
            });
        });
    }

    filterTable(table, searchTerm) {
        const rows = table.querySelectorAll('tbody tr');
        const term = searchTerm.toLowerCase();
        let visibleCount = 0;

        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            const isVisible = text.includes(term);
            row.style.display = isVisible ? '' : 'none';
            if (isVisible) visibleCount++;
        });

        this.announceToScreenReader(`${visibleCount} results found`);
    }

    setupTablePagination() {
        // This would be implemented based on your pagination needs
        // For now, we'll add basic functionality
        document.querySelectorAll('.pagination').forEach(pagination => {
            pagination.addEventListener('click', (e) => {
                const item = e.target.closest('.pagination-item');
                if (item && !item.classList.contains('disabled')) {
                    pagination.querySelectorAll('.pagination-item').forEach(p => {
                        p.classList.remove('active');
                    });
                    item.classList.add('active');
                }
            });
        });
    }

    // Loading States
    setupLoadingStates() {
        document.querySelectorAll('.btn').forEach(button => {
            const originalText = button.innerHTML;
            
            button.addEventListener('click', (e) => {
                if (button.closest('form')) {
                    setTimeout(() => {
                        button.innerHTML = '<span class="loading-spinner"></span> Loading...';
                        button.disabled = true;
                    }, 100);
                }
            });
        });
    }

    // Animations
    setupAnimations() {
        if (this.isReducedMotion) return;

        this.setupScrollAnimations();
        this.setupHoverEffects();
    }

    setupScrollAnimations() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in-up');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        document.querySelectorAll('.card, .dashboard-card, .stats-card').forEach(element => {
            observer.observe(element);
        });
    }

    setupHoverEffects() {
        // Add subtle hover effects to interactive elements
        document.querySelectorAll('.btn, .card, .list-group-item').forEach(element => {
            element.addEventListener('mouseenter', () => {
                if (!this.isReducedMotion) {
                    element.style.transform = 'translateY(-2px)';
                }
            });

            element.addEventListener('mouseleave', () => {
                element.style.transform = '';
            });
        });
    }

    // Helper Methods
    isLoginPage() {
        return window.location.pathname === '/' || 
               window.location.pathname.includes('login') ||
               document.querySelector('.login-box') !== null ||
               document.querySelector('.role-card') !== null;
    }

    // Utility Methods
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    }

    // Public API methods
    static showToast(title, message, type = 'info') {
        if (window.techZoneUI) {
            window.techZoneUI.showToast(title, message, type);
        }
    }

    static setTheme(theme) {
        if (window.techZoneUI) {
            window.techZoneUI.setTheme(theme);
        }
    }

    static announce(message) {
        if (window.techZoneUI && window.techZoneUI.announceToScreenReader) {
            window.techZoneUI.announceToScreenReader(message);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.techZoneUI = new TechZoneUI();
    
    // Expose API for backward compatibility
    window.TechZone = {
        showToast: TechZoneUI.showToast,
        setTheme: TechZoneUI.setTheme,
        announce: TechZoneUI.announce
    };
    
    console.log('🎨 TechZone Academy Enhanced UI/UX System Loaded');
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && window.techZoneUI) {
        // Refresh data or UI when page becomes visible
        const lastActivity = localStorage.getItem('techzone-last-activity');
        const now = Date.now();
        if (lastActivity && (now - parseInt(lastActivity)) > 300000) { // 5 minutes
            window.techZoneUI.showToast('Welcome Back', 'Checking for updates...', 'info');
        }
    }
    
    localStorage.setItem('techzone-last-activity', Date.now());
});

// Handle network status
window.addEventListener('online', () => {
    if (window.techZoneUI) {
        window.techZoneUI.showToast('Connection Restored', 'You are back online', 'success');
    }
});

window.addEventListener('offline', () => {
    if (window.techZoneUI) {
        window.techZoneUI.showToast('Connection Lost', 'You are currently offline', 'warning');
    }
});
