# qr_templates.py

# Define default templates for different QR types
DEFAULT_TEMPLATES = {
    'vcard': '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contact Information</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .contact-card {
            background-color: #fff;
            border-radius: 12px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            overflow: hidden;
            margin-bottom: 20px;
        }
        .card-header {
            background: linear-gradient(135deg, #6366f1, #3b82f6);
            color: white;
            padding: 20px;
            position: relative;
        }
        .name {
            font-size: 28px;
            font-weight: 600;
            margin: 0;
        }
        .title {
            font-size: 16px;
            opacity: 0.9;
            margin-top: 5px;
        }
        .card-body {
            padding: 20px;
        }
        .info-section {
            margin-bottom: 15px;
        }
        .info-item {
            display: flex;
            align-items: center;
            margin-bottom: 12px;
        }
        .info-icon {
            width: 24px;
            height: 24px;
            margin-right: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #f3f4f6;
            border-radius: 50%;
            padding: 5px;
        }
        .info-content a {
            color: #4f46e5;
            text-decoration: none;
        }
        .info-content a:hover {
            text-decoration: underline;
        }
        .btn {
            display: inline-block;
            background-color: #4f46e5;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 500;
            margin-right: 10px;
            margin-bottom: 10px;
            transition: background-color 0.2s;
        }
        .btn:hover {
            background-color: #4338ca;
        }
        .btn-outline {
            background-color: transparent;
            color: #4f46e5;
            border: 1px solid #4f46e5;
        }
        .btn-outline:hover {
            background-color: #f3f4ff;
        }
        .avatar {
            width: 60px;
            height: 60px;
            background-color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            font-weight: bold;
            color: #6366f1;
            position: absolute;
            right: 20px;
            top: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        @media (max-width: 480px) {
            body {
                padding: 10px;
            }
            .card-header {
                padding: 15px;
            }
            .name {
                font-size: 24px;
            }
        }
    </style>
</head>
<body>
    <div class="contact-card">
        <div class="card-header">
            <h1 class="name">{{name}}</h1>
            <p class="title">{{title}}</p>
            <div class="avatar">
                {{name|first}}
            </div>
        </div>
        <div class="card-body">
            <div class="info-section">
                {% if company %}
                <div class="info-item">
                    <div class="info-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                            <polyline points="9 22 9 12 15 12 15 22"></polyline>
                        </svg>
                    </div>
                    <div class="info-content">
                        <strong>Company:</strong> {{company}}
                    </div>
                </div>
                {% endif %}
                
                {% if phone %}
                <div class="info-item">
                    <div class="info-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
                        </svg>
                    </div>
                    <div class="info-content">
                        <strong>Phone:</strong> <a href="tel:{{phone}}">{{phone}}</a>
                    </div>
                </div>
                {% endif %}
                
                {% if email %}
                <div class="info-item">
                    <div class="info-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                            <polyline points="22,6 12,13 2,6"></polyline>
                        </svg>
                    </div>
                    <div class="info-content">
                        <strong>Email:</strong> <a href="mailto:{{email}}">{{email}}</a>
                    </div>
                </div>
                {% endif %}
                
                {% if website %}
                <div class="info-item">
                    <div class="info-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="2" y1="12" x2="22" y2="12"></line>
                            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                        </svg>
                    </div>
                    <div class="info-content">
                        <strong>Website:</strong> <a href="{{website}}" target="_blank">{{website}}</a>
                    </div>
                </div>
                {% endif %}
                
                {% if address %}
                <div class="info-item">
                    <div class="info-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                            <circle cx="12" cy="10" r="3"></circle>
                        </svg>
                    </div>
                    <div class="info-content">
                        <strong>Address:</strong> {{address}}
                    </div>
                </div>
                {% endif %}
            </div>
            
            <div class="actions">
                {% if phone %}
                <a href="tel:{{phone}}" class="btn">
                    Call Now
                </a>
                {% endif %}
                
                {% if email %}
                <a href="mailto:{{email}}" class="btn btn-outline">
                    Send Email
                </a>
                {% endif %}
                
                <a href="#" id="add-contact-btn" class="btn">
                    Add to Contacts
                </a>
            </div>
        </div>
    </div>
    
    <script>
        document.getElementById('add-contact-btn').addEventListener('click', function(e) {
            e.preventDefault();
            
            // Create vCard format
            const vcard = [
                'BEGIN:VCARD',
                'VERSION:3.0',
                'FN:{{name}}',
                {% if phone %}'TEL:{{phone}}',{% endif %}
                {% if email %}'EMAIL:{{email}}',{% endif %}
                {% if company %}'ORG:{{company}}',{% endif %}
                {% if title %}'TITLE:{{title}}',{% endif %}
                {% if address %}'ADR:;;{{address}};;;',{% endif %}
                {% if website %}'URL:{{website}}',{% endif %}
                'END:VCARD'
            ].join('\n');
            
            // Create download link
            const blob = new Blob([vcard], { type: 'text/vcard' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = '{{name}}.vcf';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    </script>
</body>
</html>''',
    'event': '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Event Details</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9fafb;
        }
        .event-card {
            background-color: #fff;
            border-radius: 12px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            overflow: hidden;
            margin-bottom: 20px;
        }
        .card-header {
            background: linear-gradient(135deg, #ef4444, #f97316);
            color: white;
            padding: 30px 20px;
            position: relative;
        }
        .event-title {
            font-size: 28px;
            font-weight: 600;
            margin: 0;
        }
        .event-organizer {
            font-size: 16px;
            opacity: 0.9;
            margin-top: 5px;
        }
        .card-body {
            padding: 20px;
        }
        .info-section {
            margin-bottom: 15px;
        }
        .info-item {
            display: flex;
            align-items: center;
            margin-bottom: 12px;
        }
        .info-icon {
            width: 24px;
            height: 24px;
            margin-right: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #fee2e2;
            border-radius: 50%;
            padding: 5px;
            color: #ef4444;
        }
        .info-content {
            flex: 1;
        }
        .btn {
            display: inline-block;
            background-color: #ef4444;
            color: white;
            padding: 12px 24px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 500;
            margin-right: 10px;
            margin-bottom: 10px;
            transition: background-color 0.2s;
            border: none;
            cursor: pointer;
            font-size: 1rem;
        }
        .btn:hover {
            background-color: #dc2626;
        }
        .btn-outline {
            background-color: transparent;
            color: #ef4444;
            border: 1px solid #ef4444;
        }
        .btn-outline:hover {
            background-color: #fef2f2;
        }
        .datetime-badge {
            display: flex;
            position: absolute;
            top: 20px;
            right: 20px;
            background-color: white;
            border-radius: 8px;
            padding: 12px;
            color: #ef4444;
            font-weight: 600;
            text-align: center;
            line-height: 1.2;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            flex-direction: column;
            min-width: 60px;
        }
        .date-month {
            font-size: 14px;
            text-transform: uppercase;
        }
        .date-day {
            font-size: 24px;
        }
        .description {
            background-color: #f9fafb;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 15px;
        }
        .countdown {
            background-color: #fef2f2;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
            text-align: center;
            font-weight: 600;
            color: #ef4444;
        }
        .countdown-value {
            font-size: 24px;
            margin-bottom: 5px;
        }
        @media (max-width: 480px) {
            body {
                padding: 10px;
            }
            .card-header {
                padding: 20px 15px;
            }
            .event-title {
                font-size: 24px;
                margin-right: 50px;
            }
            .datetime-badge {
                padding: 8px;
                min-width: 50px;
            }
        }
    </style>
</head>
<body>
    <div class="event-card">
        <div class="card-header">
            <h1 class="event-title">{{title}}</h1>
            {% if organizer %}
            <p class="event-organizer">Organized by {{organizer}}</p>
            {% endif %}
            
            <div class="datetime-badge">
                <span class="date-month" id="event-month"></span>
                <span class="date-day" id="event-day"></span>
            </div>
        </div>
        
        <div class="card-body">
            <div class="info-section">
                {% if start_date %}
                <div class="info-item">
                    <div class="info-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="10"></circle>
                            <polyline points="12 6 12 12 16 14"></polyline>
                        </svg>
                    </div>
                    <div class="info-content">
                        <strong>Starts:</strong> <span id="formatted-start-date">{{start_date}}</span>
                    </div>
                </div>
                {% endif %}
                
                {% if end_time %}
                <div class="info-item">
                    <div class="info-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="10"></circle>
                            <polyline points="12 6 12 12 16 10"></polyline>
                        </svg>
                    </div>
                    <div class="info-content">
                        <strong>Ends:</strong> <span id="formatted-end-time">{{end_time}}</span>
                    </div>
                </div>
                {% endif %}
                
                {% if location %}
                <div class="info-item">
                    <div class="info-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                            <circle cx="12" cy="10" r="3"></circle>
                        </svg>
                    </div>
                    <div class="info-content">
                        <strong>Location:</strong> {{location}}
                    </div>
                </div>
                {% endif %}
            </div>
            
            <div id="countdown-section" class="countdown">
                <div class="countdown-value" id="countdown-value">--</div>
                <div>until the event</div>
            </div>
            
            {% if description %}
            <div class="description">
                {{description}}
            </div>
            {% endif %}
            
            <div class="actions" style="margin-top: 20px;">
                <button id="add-calendar-btn" class="btn">
                    Add to Calendar
                </button>
                
                {% if location %}
                <a href="https://maps.google.com/?q={{location}}" target="_blank" class="btn btn-outline">
                    View on Map
                </a>
                {% endif %}
            </div>
        </div>
    </div>
    
    <script>
        // Format dates
        function formatDate(dateString) {
            try {
                const date = new Date(dateString);
                if (isNaN(date)) return dateString;
                
                const options = { 
                    weekday: 'long', 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                };
                return date.toLocaleDateString(undefined, options);
            } catch (e) {
                return dateString;
            }
        }
        
        // Set event date in badge
        function setEventDateBadge(dateString) {
            try {
                const date = new Date(dateString);
                if (isNaN(date)) return;
                
                const monthEl = document.getElementById('event-month');
                const dayEl = document.getElementById('event-day');
                
                monthEl.textContent = date.toLocaleDateString(undefined, { month: 'short' });
                dayEl.textContent = date.getDate();
            } catch (e) {
                console.error('Error setting date badge:', e);
            }
        }
        
        // Update countdown
        function updateCountdown(dateString) {
            try {
                const targetDate = new Date(dateString);
                if (isNaN(targetDate)) return;
                
                const countdownSection = document.getElementById('countdown-section');
                const countdownValue = document.getElementById('countdown-value');
                
                const now = new Date();
                const difference = targetDate - now;
                
                // If event has passed
                if (difference < 0) {
                    countdownSection.innerHTML = '<div>This event has ended</div>';
                    return;
                }
                
                // Calculate days, hours, minutes
                const days = Math.floor(difference / (1000 * 60 * 60 * 24));
                const hours = Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
                
                if (days > 0) {
                    countdownValue.textContent = `${days} day${days !== 1 ? 's' : ''}`;
                } else if (hours > 0) {
                    countdownValue.textContent = `${hours} hour${hours !== 1 ? 's' : ''}`;
                } else {
                    countdownValue.textContent = `${minutes} minute${minutes !== 1 ? 's' : ''}`;
                }
            } catch (e) {
                console.error('Error updating countdown:', e);
            }
        }
        
        // Format displayed dates
        const startDateEl = document.getElementById('formatted-start-date');
        const endTimeEl = document.getElementById('formatted-end-time');
        
        if (startDateEl) {
            startDateEl.textContent = formatDate(startDateEl.textContent);
            setEventDateBadge(startDateEl.getAttribute('data-original') || startDateEl.textContent);
            updateCountdown(startDateEl.getAttribute('data-original') || startDateEl.textContent);
        }
        
        if (endTimeEl) {
            endTimeEl.textContent = formatDate(endTimeEl.textContent);
        }
        
        // Add to calendar functionality
        document.getElementById('add-calendar-btn').addEventListener('click', function() {
            const title = '{{title}}';
            const description = `{{description}}`;
            const location = '{{location}}';
            const startDate = '{{start_date}}';
            const endTime = '{{end_time}}' || startDate;
            
            // Create iCalendar format
            const icalContent = [
                'BEGIN:VCALENDAR',
                'VERSION:2.0',
                'BEGIN:VEVENT',
                'SUMMARY:' + title,
                'DESCRIPTION:' + description,
                'LOCATION:' + location,
                'DTSTART:' + formatICSDate(startDate),
                'DTEND:' + formatICSDate(endTime),
                'END:VEVENT',
                'END:VCALENDAR'
            ].join('\n');
            
            // Create download link
            const blob = new Blob([icalContent], { type: 'text/calendar' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = title.replace(/[^a-z0-9]/gi, '_').toLowerCase() + '.ics';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
        
        // Helper function to format date for iCalendar
        function formatICSDate(dateString) {
            try {
                const date = new Date(dateString);
                if (isNaN(date)) return dateString;
                
                // Format: YYYYMMDDTHHMMSSZ
                return date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
            } catch (e) {
                return dateString;
            }
        }
    </script>
</body>
</html>''',
    'wifi': '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WiFi Connection Details</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f0f9ff;
        }
        .wifi-card {
            background-color: #fff;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(56, 189, 248, 0.2);
            overflow: hidden;
            margin-bottom: 20px;
            position: relative;
        }
        .card-header {
            background: linear-gradient(135deg, #0ea5e9, #38bdf8);
            color: white;
            padding: 30px 20px;
            position: relative;
            overflow: hidden;
        }
        .wifi-name {
            font-size: 28px;
            font-weight: 600;
            margin: 0;
            position: relative;
            z-index: 1;
        }
        .wifi-encryption {
            font-size: 16px;
            margin-top: 5px;
            opacity: 0.9;
            position: relative;
            z-index: 1;
        }
        .card-body {
            padding: 20px;
            position: relative;
        }
        .wifi-icon {
            position: absolute;
            top: 15px;
            right: 20px;
            font-size: 24px;
            color: white;
            z-index: 1;
        }
        .password-container {
            background-color: #f0f9ff;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
            position: relative;
        }
        .password-label {
            display: block;
            font-size: 14px;
            color: #0369a1;
            margin-bottom: 8px;
        }
        .password-value {
            font-family: monospace;
            font-size: 18px;
            background-color: white;
            padding: 12px 15px;
            border-radius: 6px;
            border: 1px solid #e0e7ff;
            letter-spacing: 1px;
            position: relative;
            margin-right: 40px;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .copy-btn {
            position: absolute;
            right: 15px;
            top: 43px;
            background-color: #0ea5e9;
            color: white;
            border: none;
            width: 36px;
            height: 36px;
            border-radius: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .copy-btn:hover {
            background-color: #0284c7;
        }
        .toggle-password {
            position: absolute;
            right: 60px;
            top: 43px;
            background-color: transparent;
            color: #0ea5e9;
            border: 1px solid #0ea5e9;
            width: 36px;
            height: 36px;
            border-radius: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s;
        }
        .toggle-password:hover {
            background-color: #e0f2fe;
        }
        .connect-btn {
            display: block;
            width: 100%;
            background-color: #0ea5e9;
            color: white;
            border: none;
            padding: 12px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 500;
            margin-top: 20px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .connect-btn:hover {
            background-color: #0284c7;
        }
        .connect-info {
            margin-top: 20px;
            background-color: #e0f2fe;
            border-radius: 8px;
            padding: 15px;
        }
        .connect-info h3 {
            margin-top: 0;
            color: #0369a1;
            font-size: 16px;
        }
        .connect-info ul {
            margin: 0;
            padding-left: 20px;
        }
        .connect-info li {
            margin-bottom: 8px;
            font-size: 14px;
        }
        .wave {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 15px;
            background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 120' preserveAspectRatio='none'%3E%3Cpath d='M0,0V46.29c47.79,22.2,103.59,32.17,158,28,70.36-5.37,136.33-33.31,206.8-37.5C438.64,32.43,512.34,53.67,583,72.05c69.27,18,138.3,24.88,209.4,13.08,36.15-6,69.85-17.84,104.45-29.34C989.49,25,1113-14.29,1200,52.47V0Z' opacity='.25' fill='%23ffffff'%3E%3C/path%3E%3Cpath d='M0,0V15.81C13,36.92,27.64,56.86,47.69,72.05,99.41,111.27,165,111,224.58,91.58c31.15-10.15,60.09-26.07,89.67-39.8,40.92-19,84.73-46,130.83-49.67,36.26-2.85,70.9,9.42,98.6,31.56,31.77,25.39,62.32,62,103.63,73,40.44,10.79,81.35-6.69,119.13-24.28s75.16-39,116.92-43.05c59.73-5.85,113.28,22.88,168.9,38.84,30.2,8.66,59,6.17,87.09-7.5,22.43-10.89,48-26.93,60.65-49.24V0Z' opacity='.5' fill='%23ffffff'%3E%3C/path%3E%3Cpath d='M0,0V5.63C149.93,59,314.09,71.32,475.83,42.57c43-7.64,84.23-20.12,127.61-26.46,59-8.63,112.48,12.24,165.56,35.4C827.93,77.22,886,95.24,951.2,90c86.53-7,172.46-45.71,248.8-84.81V0Z' fill='%23ffffff'%3E%3C/path%3E%3C/svg%3E") no-repeat;
            background-size: cover;
            z-index: 0;
        }
        .wifi-signal {
            position: absolute;
            top: 20px;
            right: 20px;
            width: 40px;
            height: 40px;
            z-index: 1;
        }
        .wifi-signal span {
            display: block;
            position: absolute;
            bottom: 0;
            left: 50%;
            width: 6px;
            background-color: rgba(255, 255, 255, 0.6);
            border-radius: 3px 3px 0 0;
            transform: translateX(-50%);
        }
        .wifi-signal span:nth-child(1) {
            height: 6px;
            animation: signal 1.5s infinite 0.2s;
        }
        .wifi-signal span:nth-child(2) {
            height: 12px;
            left: calc(50% - 8px);
            animation: signal 1.5s infinite 0.4s;
        }
        .wifi-signal span:nth-child(3) {
            height: 18px;
            left: calc(50% - 16px);
            animation: signal 1.5s infinite 0.6s;
        }
        .wifi-signal span:nth-child(4) {
            height: 24px;
            left: calc(50% - 24px);
            animation: signal 1.5s infinite 0.8s;
        }
        .wifi-signal span:nth-child(5) {
            height: 30px;
            left: calc(50% - 32px);
            animation: signal 1.5s infinite 1s;
        }
        
        @keyframes signal {
            0% { background-color: rgba(255, 255, 255, 0.3); }
            50% { background-color: rgba(255, 255, 255, 1); }
            100% { background-color: rgba(255, 255, 255, 0.3); }
        }
        
        .copied-toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: #0c4a6e;
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 14px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            z-index: 100;
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        @media (max-width: 480px) {
            body {
                padding: 10px;
            }
            .card-header {
                padding: 20px 15px;
            }
            .wifi-name {
                font-size: 24px;
                margin-right: 40px;
            }
        }
    </style>
</head>
<body>
    <div id="copied-toast" class="copied-toast">Password copied!</div>
    
    <div class="wifi-card">
        <div class="card-header">
            <div class="wifi-signal">
                <span></span>
                <span></span>
                <span></span>
                <span></span>
                <span></span>
            </div>
            <h1 class="wifi-name">{{ssid}}</h1>
            <p class="wifi-encryption">{{encryption}} Network</p>
            <div class="wave"></div>
        </div>
        
        <div class="card-body">
            <div class="password-container">
                <label class="password-label">Network Password</label>
                <div class="password-value" id="password-display">••••••••••••</div>
                <button class="toggle-password" id="toggle-password" title="Show/Hide Password">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M10.5 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z"/>
                        <path d="M0 8s3-5.5 8-5.5S16 8 16 8s-3 5.5-8 5.5S0 8 0 8zm8 3.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z"/>
                    </svg>
                </button>
                <button class="copy-btn" id="copy-password" title="Copy Password">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/>
                        <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/>
                    </svg>
                </button>
                <input type="hidden" id="actual-password" value="{{password}}">
            </div>
            
            <button class="connect-btn" id="connect-btn">Connect Automatically</button>
            
            <div class="connect-info">
                <h3>How to Connect</h3>
                <ul>
                    <li><strong>iOS:</strong> Open your camera and point it at the QR code to connect automatically.</li>
                    <li><strong>Android:</strong> Use your camera app or go to WiFi settings and scan the QR code.</li>
                    <li><strong>Manual:</strong> Go to your WiFi settings, find "{{ssid}}" and enter the password shown above.</li>
                </ul>
            </div>
        </div>
    </div>
    
    <script>
        const passwordDisplay = document.getElementById('password-display');
        const actualPassword = document.getElementById('actual-password').value;
        const togglePasswordBtn = document.getElementById('toggle-password');
        const copyPasswordBtn = document.getElementById('copy-password');
        const connectBtn = document.getElementById('connect-btn');
        const toast = document.getElementById('copied-toast');
        
        let passwordVisible = false;
        
        // Toggle password visibility
        togglePasswordBtn.addEventListener('click', function() {
            passwordVisible = !passwordVisible;
            
            if (passwordVisible) {
                passwordDisplay.textContent = actualPassword;
                togglePasswordBtn.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                        <path d="m10.79 12.912-1.614-1.615a3.5 3.5 0 0 1-4.474-4.474l-2.06-2.06C.938 6.278 0 8 0 8s3 5.5 8 5.5a7.029 7.029 0 0 0 2.79-.588zM5.21 3.088A7.028 7.028 0 0 1 8 2.5c5 0 8 5.5 8 5.5s-.939 1.721-2.641 3.238l-2.062-2.062a3.5 3.5 0 0 0-4.474-4.474L5.21 3.089z"/>
                        <path d="M5.525 7.646a2.5 2.5 0 0 0 2.829 2.829l-2.83-2.829zm4.95.708-2.829-2.83a2.5 2.5 0 0 1 2.829 2.829zm-5.598-5.598a8.523 8.523 0 0 1 4.704-1.382A8.445 8.445 0 0 1 16 8a8.46 8.46 0 0 1-3.447 5.65c-1.3.853-2.887 1.35-4.553 1.35C3 15 0 8 0 8a8.49 8.49 0 0 1 2.088-3.396L4.877 2.75zM11.123 13.25A8.458 8.458 0 0 0 16 8a8.482 8.482 0 0 0-3.72-5.656A8.482 8.482 0 0 0 8 1c-1.74 0-3.376.514-4.713 1.344L11.123 13.25z"/>
                    </svg>
                `;
            } else {
                passwordDisplay.textContent = '••••••••••••';
                togglePasswordBtn.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M10.5 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z"/>
                        <path d="M0 8s3-5.5 8-5.5S16 8 16 8s-3 5.5-8 5.5S0 8 0 8zm8 3.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z"/>
                    </svg>
                `;
            }
        });
        
        // Copy password
        copyPasswordBtn.addEventListener('click', function() {
            copyToClipboard(actualPassword);
            
            // Show toast
            toast.style.opacity = '1';
            setTimeout(() => {
                toast.style.opacity = '0';
            }, 2000);
        });
        
        // Connect button - for demonstration, just copy the WiFi connection details
        connectBtn.addEventListener('click', function() {
            // Create WiFi connection string
            const wifiString = `WIFI:S:{{ssid}};T:{{encryption}};P:{{password}};;`;
            copyToClipboard(wifiString);
            
            alert('WiFi connection details copied! You can now paste this into another device or app that supports WiFi connection strings.');
        });
        
        // Helper function to copy text to clipboard
        function copyToClipboard(text) {
            // Create temporary element
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'absolute';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            
            // Select and copy
            textarea.select();
            document.execCommand('copy');
            
            // Clean up
            document.body.removeChild(textarea);
        }
    </script>
</body>
</html>''',
    'text': '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Text Content</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }
        .text-card {
            background-color: #fff;
            border-radius: 12px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            overflow: hidden;
            margin-bottom: 20px;
        }
        .card-header {
            background: linear-gradient(135deg, #10b981, #34d399);
            color: white;
            padding: 20px;
            position: relative;
        }
        .card-title {
            font-size: 24px;
            font-weight: 600;
            margin: 0;
        }
        .card-body {
            padding: 20px;
        }
        .text-content {
            font-size: 16px;
            line-height: 1.7;
            white-space: pre-wrap;
            overflow-wrap: break-word;
            word-wrap: break-word;
        }
        .copy-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: 20px;
            background-color: #f1f5f9;
            color: #475569;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .copy-btn:hover {
            background-color: #e2e8f0;
        }
        .copy-btn svg {
            margin-right: 8px;
        }
        .timestamp {
            font-size: 12px;
            color: #94a3b8;
            margin-top: 20px;
            text-align: right;
        }
        .copied-toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: #334155;
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 14px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            z-index: 100;
            opacity: 0;
            transition: opacity 0.3s;
        }
        .reading-time {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.8);
            margin-top: 8px;
            display: flex;
            align-items: center;
        }
        .reading-time svg {
            margin-right: 5px;
        }
        @media (max-width: 480px) {
            body {
                padding: 12px;
            }
            .card-header {
                padding: 16px;
            }
            .card-title {
                font-size: 20px;
            }
            .card-body {
                padding: 16px;
            }
        }
    </style>
</head>
<body>
    <div id="copied-toast" class="copied-toast">Text copied to clipboard!</div>
    
    <div class="text-card">
        <div class="card-header">
            <h1 class="card-title">Shared Text Content</h1>
            <div class="reading-time">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                <span id="reading-time">2 min read</span>
            </div>
        </div>
        
        <div class="card-body">
            <div class="text-content" id="text-content">{{text}}</div>
            
            <button class="copy-btn" id="copy-btn">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                Copy Text
            </button>
            
            <div class="timestamp">
                Generated on <span id="current-date"></span>
            </div>
        </div>
    </div>
    
    <script>
        // Set current date
        document.getElementById('current-date').textContent = new Date().toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        
        // Calculate reading time
        function calculateReadingTime() {
            const text = document.getElementById('text-content').textContent;
            const wordCount = text.split(/\s+/).length;
            const readingTimeMin = Math.max(1, Math.ceil(wordCount / 200)); // Assuming 200 words per minute
            
            document.getElementById('reading-time').textContent = 
                readingTimeMin === 1 ? "1 min read" : `${readingTimeMin} min read`;
        }
        calculateReadingTime();
        
        // Copy to clipboard functionality
        document.getElementById('copy-btn').addEventListener('click', function() {
            const textToCopy = document.getElementById('text-content').textContent;
            copyToClipboard(textToCopy);
            
            // Show toast
            const toast = document.getElementById('copied-toast');
            toast.style.opacity = '1';
            setTimeout(() => {
                toast.style.opacity = '0';
            }, 2000);
            
            // Update button text temporarily
            const originalText = this.innerHTML;
            this.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                Copied!
            `;
            setTimeout(() => {
                this.innerHTML = originalText;
            }, 2000);
        });
        
        // Helper function to copy text to clipboard
        function copyToClipboard(text) {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'absolute';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
        }
    </script>
</body>
</html>
''',
'hotel_menu': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{hotel_name}} - {{menu_title}}</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            color: #333;
        }
        .menu-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #fff;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .menu-header {
            text-align: center;
            padding: 20px 0;
            border-bottom: 2px solid #f0f0f0;
        }
        .menu-header h1 {
            margin: 0;
            color: #333;
            font-size: 32px;
        }
        .menu-header h2 {
            margin: 10px 0 0;
            color: #777;
            font-size: 18px;
            font-weight: normal;
        }
        .menu-description {
            padding: 15px 0;
            font-size: 16px;
            line-height: 1.5;
            color: #555;
            text-align: center;
            font-style: italic;
        }
        .menu-category {
            margin: 30px 0;
        }
        .category-header {
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        .category-name {
            margin: 0;
            font-size: 24px;
            color: #222;
        }
        .category-description {
            margin: 5px 0 0;
            font-size: 14px;
            color: #666;
        }
        .menu-item {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px dashed #eee;
        }
        .item-details {
            flex: 1;
        }
        .item-image {
            width: 80px;
            height: 80px;
            margin-left: 15px;
            object-fit: cover;
            border-radius: 4px;
        }
        .item-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
        }
        .item-name {
            margin: 0;
            font-size: 18px;
            color: #111;
        }
        .item-price {
            font-weight: bold;
            color: #111;
        }
        .item-description {
            margin: 5px 0 0;
            font-size: 14px;
            color: #777;
            line-height: 1.4;
        }
        .item-badges {
            margin-top: 5px;
        }
        .badge {
            display: inline-block;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 3px;
            margin-right: 5px;
        }
        .badge-vegetarian {
            background-color: #8bc34a;
            color: white;
        }
        .badge-spicy {
            background-color: #ff5722;
            color: white;
        }
        .badge-special {
            background-color: #ffc107;
            color: #333;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="menu-container">
        <div class="menu-header">
            <h1>{{hotel_name}}</h1>
            <h2>{{menu_title}}</h2>
        </div>
        
        <div class="menu-description">
            {{description}}
        </div>
        
        <!-- Menu content will be dynamically generated -->
        
        <div class="footer">
            Powered by QR Craft
        </div>
    </div>
</body>
</html>
"""
}


def get_template_vars(qr_type):
    """Get available template variables for a QR type"""
    if qr_type == 'vcard':
        return ['name', 'phone', 'email', 'company', 'title', 'address', 'website']
    elif qr_type == 'event':
        return ['title', 'location', 'start_date', 'end_time', 'description', 'organizer']
    elif qr_type == 'wifi':
        return ['ssid', 'password', 'encryption']
    elif qr_type == 'text':
        return ['text']
    elif qr_type == 'hotel_menu':
        return ['hotel_name', 'menu_title', 'description']
    else:
        return ['content']

def get_var_descriptions():
    """Get descriptions for template variables"""
    return {
        'name': 'Full name of the contact',
        'phone': 'Phone number',
        'email': 'Email address',
        'company': 'Company or organization name',
        'title': 'Job title or position',
        'address': 'Physical address',
        'website': 'Website URL',
        'title': 'Event title',
        'location': 'Event location',
        'start_date': 'Event start date and time',
        'end_time': 'Event end date and time',
        'description': 'Event description',
        'organizer': 'Event organizer',
        'ssid': 'WiFi network name',
        'password': 'WiFi password',
        'encryption': 'WiFi encryption type (WPA, WEP, etc.)',
        'text': 'Text content of the QR code',
        'content': 'Generic content of the QR code',
        # New hotel menu variables
        'hotel_name': 'Name of the hotel or restaurant',
        'menu_title': 'Title of the menu',
        'menu_description': 'Description of the menu'
    }