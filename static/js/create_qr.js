// Global variables to track form state
let currentQRType = 'link';
let formChanged = false;
let changeHistory = [];

// Initialize toastr notification library
toastr.options = {
    closeButton: true,
    newestOnTop: true,
    progressBar: true,
    positionClass: "toast-bottom-right",
    preventDuplicates: false,
    showDuration: "300",
    hideDuration: "1000",
    timeOut: "5000",
    extendedTimeOut: "1000",
    showEasing: "swing",
    hideEasing: "linear",
    showMethod: "fadeIn",
    hideMethod: "fadeOut"
};

// Main initialization function
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all UI components
    setupQRTypeSwitching();
    setupTemplateSelection();
    setupTabSwitching();
    setupFormValidation();
    setupFormChangeDetection();
    setupTemplateGuidanceModal();
    setupColorPickers();
    setupEyeCustomization();
    setupFrameText();
    setupGradientOptions();
    setupSliders();
    setupAccordions();
    setupPasswordToggle();
    setupLogoHandling();
    
    // Set up preview refresh button
    const refreshPreviewBtn = document.getElementById('refreshPreviewBtn');
    if (refreshPreviewBtn) {
        refreshPreviewBtn.addEventListener('click', function() {
            updateQRPreview('Manually refreshed preview');
            toastr.info('QR code preview refreshed', 'Preview Updated');
        });
    }
    
    // Set up download preview button
    const downloadPreviewBtn = document.getElementById('downloadPreviewBtn');
    if (downloadPreviewBtn) {
        downloadPreviewBtn.addEventListener('click', function() {
            const previewImage = document.getElementById('qr-preview-image');
            if (!previewImage || previewImage.src.includes('placeholder')) {
                toastr.warning('Please generate a QR code first', 'Cannot Download');
                return;
            }
            
            // Create a temporary anchor element
            const link = document.createElement('a');
            link.href = previewImage.src;
            link.download = `qr-preview-${new Date().getTime()}.png`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            toastr.success('QR code preview downloaded', 'Download Complete');
        });
    }

    // Initial preview after a short delay to allow form to initialize
    setTimeout(() => {
        updateQRPreview();
    }, 500);
});

// Function to update QR code preview
function updateQRPreview(reason = null) {
    const previewContainer = document.querySelector('.qr-preview');
    const previewImage = document.getElementById('qr-preview-image');
    
    // Create or update loading overlay
    let loadingOverlay = document.querySelector('.preview-loading');
    if (!loadingOverlay) {
        loadingOverlay = document.createElement('div');
        loadingOverlay.className = 'preview-loading absolute inset-0 bg-white bg-opacity-80 flex flex-col items-center justify-center rounded-lg';
        loadingOverlay.innerHTML = `
            <div class="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-secondary-600"></div>
            <p class="mt-2 text-sm font-medium text-gray-700">Updating preview...</p>`;
        previewContainer.appendChild(loadingOverlay);
    } else {
        loadingOverlay.style.display = 'flex';
    }
    
    // Build form data from current values
    const form = document.getElementById('create-qr-form');
    const formData = new FormData(form);

    // Ensure all color values are included and properly formatted
    const colorFields = ['color', 'background_color', 'inner_eye_color', 'outer_eye_color'];
    colorFields.forEach(fieldId => {
        const input = document.getElementById(fieldId);
        if (input && input.value) {
            // Format the color properly
            let colorValue = formatColorValue(input.value);
            formData.set(fieldId, colorValue);
        }
    });

    // Handle logo file properly
    const logoInput = document.getElementById('logo');
    if (logoInput && logoInput.files && logoInput.files[0]) {
        formData.set('logo', logoInput.files[0]);
        
        // Ensure logo options are included
        const logoSizeSlider = document.getElementById('logo_size_percentage');
        const roundLogoCheckbox = document.getElementById('round_logo');
        
        if (logoSizeSlider) {
            formData.set('logo_size_percentage', logoSizeSlider.value);
        }
        if (roundLogoCheckbox) {
            formData.set('round_logo', roundLogoCheckbox.checked ? 'true' : 'false');
        }
    }

    // Ensure custom eyes options are included
    const customEyesCheckbox = document.getElementById('custom_eyes');
    if (customEyesCheckbox) {
        formData.set('custom_eyes', customEyesCheckbox.checked ? 'true' : 'false');
        if (customEyesCheckbox.checked) {
            formData.set('using_custom_eyes', 'true');
        }
    }

    // Handle gradient colors if in gradient mode
    const exportType = document.getElementById('export_type');
    if (exportType && exportType.value === 'gradient') {
        const gradientStart = document.getElementById('gradient_start_color');
        const gradientEnd = document.getElementById('gradient_end_color');
        if (gradientStart && gradientStart.value) {
            formData.set('gradient_start', formatColorValue(gradientStart.value));
        }
        if (gradientEnd && gradientEnd.value) {
            formData.set('gradient_end', formatColorValue(gradientEnd.value));
        }
        formData.set('using_gradient', 'true');
    } else {
        // Explicitly set to non-gradient mode
        formData.set('export_type', 'png');
        formData.set('using_gradient', 'false');
    }
    
    // Make AJAX request
    fetch('/preview-qr', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Preview request failed with status: ${response.status}`);
        }
        return response.blob();
    })
    .then(blob => {
        // Hide loading overlay
        loadingOverlay.style.display = 'none';
        
        // Update preview image
        const url = URL.createObjectURL(blob);
        previewImage.src = url;
        
        // Add to change history if reason is provided
        if (reason) {
            addToChangeHistory(reason);
        }
        
        return true;
    })
    .catch(error => {
        console.error('Error updating preview:', error);
        
        // Hide loading overlay
        loadingOverlay.style.display = 'none';
        
        // Show error toast with more details
        toastr.error(
            'Could not generate preview. Try different settings or refresh the page.', 
            'Preview Error'
        );
    });
}

// Add to change history
function addToChangeHistory(changeText) {
    const timestamp = new Date();
    const timeString = timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    // Add to history array
    changeHistory.unshift({
        text: changeText,
        time: timeString,
        timestamp: timestamp
    });
    
    // Keep only the last 10 changes
    if (changeHistory.length > 10) {
        changeHistory.pop();
    }
    
    // Update UI
    updateChangeHistoryUI();
}

// Update change history UI
function updateChangeHistoryUI() {
    const historyList = document.getElementById('changeHistoryList');
    
    // Clear existing content
    historyList.innerHTML = '';
    
    // Add each history item
    if (changeHistory.length === 0) {
        historyList.innerHTML = `
            <div class="text-center text-gray-500 py-3">
                <i class="fas fa-info-circle block mb-2"></i>
                <p class="text-sm">Make changes to see history</p>
            </div>
        `;
        return;
    }
    
    changeHistory.forEach(item => {
        const historyItem = document.createElement('div');
        historyItem.className = 'mb-2 p-2 text-sm bg-gray-50 rounded flex items-center text-gray-700 hover:bg-gray-100 transition-colors';
        historyItem.innerHTML = `
            <i class="fas fa-circle-notch text-secondary-500 mr-2 text-xs"></i>
            <span class="flex-grow">${item.text}</span>
            <span class="text-xs text-gray-500">${item.time}</span>
        `;
        historyList.appendChild(historyItem);
    });
}

// Format color value
function formatColorValue(color) {
    if (!color) return '#000000';
    
    // Convert to string and trim whitespace
    color = String(color).trim();
    
    // Remove any spaces
    color = color.replace(/\s/g, '');
    
    // If color doesn't start with #, add it
    if (!color.startsWith('#')) {
        color = '#' + color;
    }
    
    // Handle 3-digit hex colors by expanding them
    if (/^#[0-9A-Fa-f]{3}$/.test(color)) {
        color = '#' + color[1] + color[1] + color[2] + color[2] + color[3] + color[3];
    }
    
    // Validate hex format with improved regex
    if (!/^#[0-9A-Fa-f]{6}$/.test(color)) {
        console.warn('Invalid color format:', color);
        return '#000000'; // Default to black for invalid colors
    }
    
    return color.toUpperCase();
}

// Debounce function to prevent too many preview updates
function debounce(func, wait) {
    let timeout;
    return function() {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            func.apply(context, args);
        }, wait);
    };
}

// Setup QR type switching
function setupQRTypeSwitching() {
    const qrTypeBtns = document.querySelectorAll('.qr-type-option');
    const qrTypeContents = document.querySelectorAll('.qr-type-content');
    
    // Style all QR type options initially
    qrTypeBtns.forEach((option, index) => {
        if (index === 0) {
            option.classList.add('active');
            option.querySelector('i').classList.add('text-blue-700');
            option.querySelector('i').classList.remove('text-gray-600');
        } else {
            option.classList.remove('active');
            option.querySelector('i').classList.remove('text-blue-700');
            option.querySelector('i').classList.add('text-gray-600');
        }
    });
    
    // Style all QR type contents initially
    qrTypeContents.forEach((content, index) => {
        if (index === 0) {
            content.classList.remove('hidden');
            content.style.opacity = '1';
            content.style.transition = 'opacity 0.3s ease';
        } else {
            content.classList.add('hidden');
            content.style.opacity = '0';
            content.style.transition = 'opacity 0.3s ease';
        }
    });
    
    // Make QR type buttons accessible with keyboard
    qrTypeBtns.forEach(btn => {
        btn.addEventListener('keydown', function(e) {
            // Handle Enter or Space key press
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
        
        btn.addEventListener('click', function() {
            // Don't proceed if already selected
            if (this.classList.contains('active')) {
                return;
            }
            
            // Update selected state with animation
            qrTypeBtns.forEach(b => {
                b.classList.remove('active');
                b.style.transition = 'all 0.3s ease';
                b.setAttribute('aria-checked', 'false');
                b.querySelector('i').classList.remove('text-blue-700');
                b.querySelector('i').classList.add('text-gray-600');
            });
            
            this.classList.add('active');
            this.setAttribute('aria-checked', 'true');
            this.querySelector('i').classList.remove('text-gray-600');
            this.querySelector('i').classList.add('text-blue-700');
            
            // Update radio button
            const radio = this.querySelector('input[type="radio"]');
            radio.checked = true;
            
            // Fade out current content
            const qrType = this.dataset.type;
            const currentContent = document.querySelector('.qr-type-content:not(.hidden)');
            
            if (currentContent) {
                currentContent.style.opacity = '0';
                
                setTimeout(() => {
                    // Hide all content sections
                    qrTypeContents.forEach(content => {
                        content.classList.add('hidden');
                        content.style.opacity = '0';
                    });
                    
                    // Show and fade in new content
                    const contentToShow = document.getElementById(`${qrType}-content`);
                    if (contentToShow) {
                        contentToShow.classList.remove('hidden');
                        
                        // Allow the DOM to update before animation
                        setTimeout(() => {
                            contentToShow.style.opacity = '1';
                        }, 50);
                    }
                    
                    // Update current QR type
                    currentQRType = qrType;
                    
                    // Focus on the first input in the new content section
                    const firstInput = contentToShow.querySelector('input, textarea, select');
                    if (firstInput) {
                        firstInput.focus();
                    }
                }, 300);
            } else {
                // First load, no animation needed
                qrTypeContents.forEach(content => {
                    content.classList.add('hidden');
                });
                
                const contentToShow = document.getElementById(`${qrType}-content`);
                if (contentToShow) {
                    contentToShow.classList.remove('hidden');
                    contentToShow.style.opacity = '1';
                }
                
                currentQRType = qrType;
            }
            
            // Update QR preview with type change
            updateQRPreview(`Changed QR type to ${qrType.charAt(0).toUpperCase() + qrType.slice(1)}`);
        });
    });
}

// Setup template selection
function setupTemplateSelection() {
    const templateCards = document.querySelectorAll('.template-card');
    
    // Make template cards accessible with keyboard
    templateCards.forEach(card => {
        card.addEventListener('keydown', function(e) {
            // Handle Enter or Space key press
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
        
        card.addEventListener('click', function() {
            // Add visual selection animation
            templateCards.forEach(c => {
                c.classList.remove('selected');
                c.classList.remove('border-secondary-500');
                c.classList.add('border-gray-200');
                c.setAttribute('aria-pressed', 'false');
            });
            
            this.classList.add('selected');
            this.classList.remove('border-gray-200');
            this.classList.add('border-secondary-500');
            this.setAttribute('aria-pressed', 'true');
            
            // Update radio button
            const radio = this.querySelector('input[type="radio"]');
            radio.checked = true;
            
            // Get template name for notification
            const templateName = this.querySelector('h3').textContent;
            
            // If custom template is selected, switch to custom tab
            if (this.dataset.template === 'custom') {
                document.getElementById('custom-tab').click();
                
                // Show toast notification
                toastr.info('Switched to custom design mode', 'Custom Template');
            } else {
                // Show toast notification for template selection
                toastr.success(`'${templateName}' template applied`, 'Template Changed');
                
                // Apply template styles based on selected template
                applyTemplateStyles(this.dataset.template);
            }
            
            // Update preview with template change
            updateQRPreview(`Applied '${templateName}' template`);
        });
    });
}

// Setup tab switching
function setupTabSwitching() {
    const tabButtons = document.querySelectorAll('[data-bs-toggle="pill"]');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Get target tab
            const target = document.querySelector(this.dataset.bsTarget);
            
            // Remove active class from all buttons and tabs
            tabButtons.forEach(btn => {
                btn.classList.remove('border-secondary-500', 'text-secondary-600', 'active');
                btn.classList.add('border-transparent', 'text-gray-500');
                btn.setAttribute('aria-selected', 'false');
            });
            
            tabPanes.forEach(pane => {
                pane.classList.remove('show', 'active');
                pane.classList.add('hidden');
            });
            
            // Add active class to clicked button and its target
            this.classList.remove('border-transparent', 'text-gray-500');
            this.classList.add('border-secondary-500', 'text-secondary-600', 'active');
            this.setAttribute('aria-selected', 'true');
            
            target.classList.remove('hidden');
            target.classList.add('show', 'active');
        });
    });
}

// Setup form validation
function setupFormValidation() {
    const form = document.getElementById('create-qr-form');
    
    // Add the validation classes
    form.classList.add('needs-validation');
    
    // Prevent form submission if validation fails
    form.addEventListener('submit', function(event) {
        // Validate color inputs before submission
        const colorInputs = form.querySelectorAll('input[id$="color"]');
        let hasColorError = false;
        
        colorInputs.forEach(input => {
            if (input && input.value) {
                let colorValue = input.value.trim();
                if (!colorValue.startsWith('#')) {
                    colorValue = '#' + colorValue;
                }
                
                // Validate hex format
                if (!/^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/.test(colorValue)) {
                    event.preventDefault();
                    event.stopPropagation();
                    hasColorError = true;
                    
                    const label = input.labels ? input.labels[0] : null;
                    const fieldName = label ? label.textContent.trim() : (input.name || input.id);
                    
                    toastr.error(
                        `Invalid color format for ${fieldName}. Please use a valid hex color (e.g., #000000).`,
                        'Validation Error'
                    );
                    
                    input.focus();
                }
                
                // Update input value with properly formatted color
                input.value = colorValue;
            }
        });

        if (hasColorError) {
            return false;
        }
        
        // First, check for any hidden required fields and temporarily make them not required
        const hiddenFields = form.querySelectorAll('.hidden [required]');
        hiddenFields.forEach(field => {
            field.setAttribute('data-was-required', 'true');
            field.removeAttribute('required');
        });
        
        if (!form.checkValidity()) {
            event.preventDefault();
            event.stopPropagation();
            
            // Find all invalid fields
            const invalidFields = form.querySelectorAll(':invalid');
            
            // Create a list of missing fields
            const missingFieldsList = Array.from(invalidFields).map(field => {
                const label = field.labels ? field.labels[0] : null;
                const fieldName = label ? label.textContent.trim() : (field.name || field.id);
                return fieldName.replace(' *', '');
            });
            
            // Show error toast with specific field names
            if (missingFieldsList.length > 0) {
                const errorMsg = `Please fill in the following required fields: ${missingFieldsList.join(', ')}`;
                toastr.error(errorMsg, 'Validation Error');
                
                // Focus the first invalid field
                invalidFields[0].focus();
                
                // Scroll to first invalid input
                invalidFields[0].scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'center' 
                });
            } else {
                // Generic error if no specific fields were identified
                toastr.error('Please fill in all required fields correctly', 'Validation Error');
            }
        } else {
            // Process form submission
            // Add gradient flag if needed
            const exportType = document.getElementById('export_type');
            if (exportType && exportType.value === 'gradient') {
                let gradientField = document.getElementById('using_gradient');
                if (!gradientField) {
                    gradientField = document.createElement('input');
                    gradientField.type = 'hidden';
                    gradientField.id = 'using_gradient';
                    gradientField.name = 'using_gradient';
                    form.appendChild(gradientField);
                }
                gradientField.value = 'true';
            } else {
                // Explicitly set to non-gradient
                let gradientField = document.getElementById('using_gradient');
                if (!gradientField) {
                    gradientField = document.createElement('input');
                    gradientField.type = 'hidden';
                    gradientField.id = 'using_gradient';
                    gradientField.name = 'using_gradient';
                    form.appendChild(gradientField);
                }
                gradientField.value = 'false';
            }
            
            // Add custom eyes flag if needed
            const customEyes = document.getElementById('custom_eyes');
            if (customEyes && customEyes.checked) {
                let customEyesField = document.getElementById('using_custom_eyes');
                if (!customEyesField) {
                    customEyesField = document.createElement('input');
                    customEyesField.type = 'hidden';
                    customEyesField.id = 'using_custom_eyes';
                    customEyesField.name = 'using_custom_eyes';
                    form.appendChild(customEyesField);
                }
                customEyesField.value = 'true';
            }
            
            // Form is valid, add animation to submit button
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = `
                    <div class="animate-spin -ml-1 mr-3 h-5 w-5 text-white">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                    </div>
                    Creating QR Code...`;
                submitBtn.disabled = true;
            }
            
            // Reset unsaved changes flag
            formChanged = false;
        }
        
        // Restore required attribute to fields
        hiddenFields.forEach(field => {
            if (field.getAttribute('data-was-required') === 'true') {
                field.setAttribute('required', '');
                field.removeAttribute('data-was-required');
            }
        });
        
        form.classList.add('was-validated');
    });
}

// Setup logo handling
function setupLogoHandling() {
    const logoInput = document.getElementById('logo');
    const removeLogoBtn = document.getElementById('removeLogo');
    
    if (logoInput) {
        logoInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const fileName = this.files[0].name;
                
                // Validate file type
                const validTypes = ['image/jpeg', 'image/png', 'image/gif'];
                if (!validTypes.includes(this.files[0].type)) {
                    toastr.error('Please upload a JPEG, PNG, or GIF image.', 'Invalid File Type');
                    this.value = '';
                    return;
                }
                
                // Update preview with logo
                updateQRPreview(`Added logo: ${fileName}`);
                
                // Show success notification
                toastr.success(`Logo uploaded successfully: ${fileName}`, 'Logo Added');
            }
        });
    }
    
    if (removeLogoBtn) {
        removeLogoBtn.addEventListener('click', function() {
            if (logoInput) {
                logoInput.value = '';
                updateQRPreview('Removed logo');
                
                // Show notification
                toastr.info('Logo has been removed', 'Logo Removed');
            }
        });
    }
}

// Setup accordions using Alpine.js, with fallback for when Alpine.js is not loaded
function setupAccordions() {
    // Check if Alpine.js is available
    if (typeof Alpine === 'undefined') {
        // Find all accordion headers
        const accordionHeaders = document.querySelectorAll('.accordion-header');
        
        accordionHeaders.forEach(header => {
            const content = header.nextElementSibling;
            
            // Set initial state
            content.style.display = 'none';
            
            // Add click handler
            header.addEventListener('click', () => {
                const isOpen = content.style.display !== 'none';
                
                // Toggle content
                content.style.display = isOpen ? 'none' : 'block';
                
                // Toggle icon
                const icon = header.querySelector('.fa-chevron-down');
                if (icon) {
                    icon.style.transform = isOpen ? '' : 'rotate(180deg)';
                }
            });
        });
    }
}

// Toggle password visibility for WiFi password
function setupPasswordToggle() {
    const togglePasswordBtn = document.getElementById('toggleWifiPassword');
    const passwordInput = document.getElementById('wifi-password');
    
    if (togglePasswordBtn && passwordInput) {
        togglePasswordBtn.addEventListener('click', function() {
            // Toggle password visibility
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            
            // Toggle icon
            const icon = this.querySelector('i');
            if (type === 'password') {
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            } else {
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            }
        });
    }
}

// Setup template guidance modal
function setupTemplateGuidanceModal() {
    const templateHelpBtn = document.getElementById('templateHelpBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const closeModalBtnBottom = document.getElementById('closeModalBtnBottom');
    const modal = document.getElementById('templateGuidanceModal');
    
    if (templateHelpBtn && modal) {
        templateHelpBtn.addEventListener('click', function() {
            modal.classList.remove('hidden');
        });
    }
    
    if (closeModalBtn && modal) {
        closeModalBtn.addEventListener('click', function() {
            modal.classList.add('hidden');
        });
    }
    
    if (closeModalBtnBottom && modal) {
        closeModalBtnBottom.addEventListener('click', function() {
            modal.classList.add('hidden');
        });
    }
    
    // Close modal when clicking outside
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
    }
}

// Apply template styles
function applyTemplateStyles(template) {
    if (!template) return;
    
    // Define templates with their respective styles
    const templates = {
        modern: {
            shape: "rounded",
            color: "#2c5282", // Blue
            background_color: "#FFFFFF",
            export_type: "png", // Non-gradient
            custom_eyes: true,
            inner_eye_style: "circle",
            outer_eye_style: "rounded",
            inner_eye_color: "#2c5282",
            outer_eye_color: "#2c5282"
        },
        corporate: {
            shape: "square",
            color: "#1a365d", // Darker blue
            background_color: "#FFFFFF",
            export_type: "png",
            frame_type: "square",
            custom_eyes: false
        },
        playful: {
            shape: "circle",
            export_type: "gradient",
            gradient_start_color: "#3182ce",
            gradient_end_color: "#90cdf4",
            background_color: "#FFFFFF",
            custom_eyes: true,
            inner_eye_style: "circle",
            outer_eye_style: "circle",
            inner_eye_color: "#3182ce",
            outer_eye_color: "#3182ce"
        },
        minimal: {
            shape: "square",
            color: "#2d3748", // Gray
            background_color: "#FFFFFF",
            export_type: "png",
            custom_eyes: false
        },
        high_contrast: {
            shape: "square",
            color: "#000000",
            background_color: "#FFFFFF",
            export_type: "png",
            module_size: 12,
            quiet_zone: 4,
            custom_eyes: false
        }
    };
    
    // Get the template styles
    const styles = templates[template];
    if (!styles) return;
    
    // Apply template styles
    Object.keys(styles).forEach(key => {
        const value = styles[key];
        const element = document.getElementById(key);
        
        if (element) {
            // Handle color inputs specially
            if (key.includes('color')) {
                const formattedColor = formatColorValue(value);
                element.value = formattedColor;
                
                // Update preview for color inputs
                const preview = document.getElementById(`${key}-preview`);
                if (preview) {
                    preview.style.backgroundColor = formattedColor;
                }
            } 
            // Handle checkboxes
            else if (element.type === 'checkbox') {
                element.checked = value;
                
                // Toggle related panels for custom eyes
                if (key === 'custom_eyes') {
                    const eyeOptions = document.getElementById('eye-customization-options');
                    if (eyeOptions) {
                        eyeOptions.classList.toggle('hidden', !value);
                    }
                }
            }
            // Handle select elements
            else if (element.tagName === 'SELECT') {
                element.value = value;
                
                // Special handling for export type
                if (key === 'export_type') {
                    const gradientOptions = document.getElementById('gradient-options');
                    if (gradientOptions) {
                        gradientOptions.classList.toggle('hidden', value !== 'gradient');
                    }
                }
            }
            // Handle text inputs and range inputs
            else if (element.type === 'text' || element.type === 'number' || element.type === 'range') {
                element.value = value;
                
                // Update display value for range inputs
                if (element.type === 'range') {
                    const valueDisplay = document.getElementById(`${key}-value`);
                    if (valueDisplay) {
                        valueDisplay.textContent = value;
                    }
                }
            }
        }
        
        // Handle radio button groups
        if (key === 'shape') {
            const radio = document.getElementById(`shape-${value}`);
            if (radio) {
                radio.checked = true;
            }
        }
        else if (key === 'frame_type') {
            const radio = document.getElementById(`frame-${value}`);
            if (radio) {
                radio.checked = true;
                
                // Show/hide frame text input based on frame type
                const frameTextContainer = document.getElementById('frame-text-container');
                if (frameTextContainer) {
                    frameTextContainer.classList.toggle('hidden', !['scan_me', 'branded'].includes(value));
                }
            }
        }
    });
    
    // Update gradient preview if needed
    if (styles.export_type === 'gradient') {
        updateGradientPreview();
    }
}

// Helper function to create a lighter variant of a color
function lightenColor(hex, percent) {
    // Convert hex to RGB
    hex = hex.replace(/^\s*#|\s*$/g, '');
    
    // Convert 3 char hex to 6 char
    if(hex.length == 3){
        hex = hex.replace(/(.)/g, '$1$1');
    }
    
    var r = parseInt(hex.substr(0, 2), 16),
        g = parseInt(hex.substr(2, 2), 16),
        b = parseInt(hex.substr(4, 2), 16);
    
    // Increase each component by the percentage
    r = Math.min(255, Math.round(r + (255 - r) * (percent / 100)));
    g = Math.min(255, Math.round(g + (255 - g) * (percent / 100)));
    b = Math.min(255, Math.round(b + (255 - b) * (percent / 100)));
    
    // Convert back to hex
    return '#' + 
        (r.toString(16).padStart(2, '0')) +
        (g.toString(16).padStart(2, '0')) +
        (b.toString(16).padStart(2, '0'));
}