// Main JavaScript for AI Sports Coach

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Handle flash message fadeout
    setupFlashMessages();
    
    // Setup mobile navigation
    setupMobileNav();
    
    // Sport card click handler
    setupSportCards();
});

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Flash message automatic fadeout
function setupFlashMessages() {
    const flashMessages = document.querySelectorAll('.alert');
    
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            // Fade out the message
            message.style.opacity = '1';
            
            (function fadeOut() {
                if ((message.style.opacity -= 0.1) < 0) {
                    message.style.display = 'none';
                } else {
                    requestAnimationFrame(fadeOut);
                }
            })();
            
        }, 5000); // Fade out after 5 seconds
    });
}

// Mobile navigation toggle
function setupMobileNav() {
    const navToggle = document.querySelector('.navbar-toggler');
    
    if (navToggle) {
        navToggle.addEventListener('click', function() {
            const navMenu = document.querySelector('.navbar-collapse');
            navMenu.classList.toggle('show');
        });
    }
}

// Sport card click handler
function setupSportCards() {
    const sportCards = document.querySelectorAll('.sport-card');
    
    sportCards.forEach(function(card) {
        card.addEventListener('click', function() {
            const sportId = this.getAttribute('data-sport-id');
            window.location.href = `/upload?sport=${sportId}`;
        });
    });
}

// Date picker initialization
function initDatePickers() {
    const dateInputs = document.querySelectorAll('input[type="date"]');
    
    dateInputs.forEach(function(input) {
        // Set default value to today if empty
        if (!input.value) {
            const today = new Date();
            const year = today.getFullYear();
            let month = today.getMonth() + 1;
            let day = today.getDate();
            
            month = month < 10 ? '0' + month : month;
            day = day < 10 ? '0' + day : day;
            
            input.value = `${year}-${month}-${day}`;
        }
    });
}

// Form validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    
    if (!form) return true;
    
    let isValid = true;
    const requiredInputs = form.querySelectorAll('[required]');
    
    requiredInputs.forEach(function(input) {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('is-invalid');
            
            // Create or update error message
            let errorDiv = input.nextElementSibling;
            if (!errorDiv || !errorDiv.classList.contains('invalid-feedback')) {
                errorDiv = document.createElement('div');
                errorDiv.classList.add('invalid-feedback');
                input.parentNode.insertBefore(errorDiv, input.nextSibling);
            }
            errorDiv.textContent = 'This field is required';
        } else {
            input.classList.remove('is-invalid');
            const errorDiv = input.nextElementSibling;
            if (errorDiv && errorDiv.classList.contains('invalid-feedback')) {
                errorDiv.textContent = '';
            }
        }
    });
    
    return isValid;
}

// Helper function to format date
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', options);
}

// Helper function to create risk level badge
function createRiskBadge(riskLevel) {
    const badge = document.createElement('span');
    badge.classList.add('risk-level');
    
    switch(riskLevel.toLowerCase()) {
        case 'low':
            badge.classList.add('risk-low');
            badge.innerText = 'Low Risk';
            break;
        case 'medium':
            badge.classList.add('risk-medium');
            badge.innerText = 'Medium Risk';
            break;
        case 'high':
            badge.classList.add('risk-high');
            badge.innerText = 'High Risk';
            break;
        default:
            badge.classList.add('risk-medium');
            badge.innerText = 'Unknown Risk';
    }
    
    return badge;
}
