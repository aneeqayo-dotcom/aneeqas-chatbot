from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import os
from dotenv import load_dotenv
from datetime import datetime
import random
import re
import json
import time
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

app = Flask(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# ============================================
# MODEL FALLBACK - Try multiple models
# ============================================
MODELS_TO_TRY = [
    'models/gemini-3.6-flash',
    'models/gemini-3.5-flash',
    'models/gemini-2.5-flash',
    'models/gemini-1.5-flash',
    'models/gemini-pro'
]

def get_available_model():
    """Try to find a working model"""
    for model_name in MODELS_TO_TRY:
        try:
            model = genai.GenerativeModel(model_name)
            # Test with a simple request
            test_response = model.generate_content("Hello")
            if test_response:
                print(f"✅ Using model: {model_name}")
                return model
        except Exception as e:
            print(f"❌ Model {model_name} failed: {e}")
            continue
    # Fallback to first model even if it might fail
    return genai.GenerativeModel(MODELS_TO_TRY[0])

# Initialize model
text_model = get_available_model()

# ============================================
# COLOR PALETTES
# ============================================
COLOR_PALETTES = [
    {'primary': '#6C3CE1', 'secondary': '#1a1424', 'accent': '#E94560', 'bg': '#0d0a14', 'card': '#1f1530', 'text': '#FFFFFF'},
    {'primary': '#C0392B', 'secondary': '#1a0a0a', 'accent': '#E74C3C', 'bg': '#0d0505', 'card': '#1a0a0a', 'text': '#FFFFFF'},
    {'primary': '#2980B9', 'secondary': '#0a1a2a', 'accent': '#3498DB', 'bg': '#050d1a', 'card': '#0a1a2a', 'text': '#FFFFFF'},
    {'primary': '#27AE60', 'secondary': '#0a1a0a', 'accent': '#2ECC71', 'bg': '#050d05', 'card': '#0a1a0a', 'text': '#FFFFFF'},
    {'primary': '#8E44AD', 'secondary': '#1a0a2a', 'accent': '#AF7AC5', 'bg': '#0d051a', 'card': '#1a0a2a', 'text': '#FFFFFF'},
    {'primary': '#D4A017', 'secondary': '#1a140a', 'accent': '#F1C40F', 'bg': '#0d0a05', 'card': '#1a140a', 'text': '#FFFFFF'},
    {'primary': '#1ABC9C', 'secondary': '#0a1a14', 'accent': '#16A085', 'bg': '#050d0a', 'card': '#0a1a14', 'text': '#FFFFFF'},
]

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def extract_schedule_details(prompt):
    """Extract days and time slots from prompt"""
    days = 7
    hours = ['8:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00']
    
    # Extract number of days
    day_match = re.search(r'(\d+)\s*(?:day|days?)', prompt.lower())
    if day_match:
        days = int(day_match.group(1))
        days = max(1, min(days, 14))
    
    # Extract hours per day
    hour_match = re.search(r'(\d+)\s*hours?\s*per\s*day', prompt.lower())
    if hour_match:
        hours_per_day = int(hour_match.group(1))
        hours = []
        for h in range(8, min(8 + hours_per_day, 22), 2):
            ampm = "AM" if h < 12 else "PM"
            display_hour = h if h <= 12 else h - 12
            hours.append(f"{display_hour}:00 {ampm}")
    
    # Extract time range (e.g., "from 9am to 5pm")
    time_match = re.search(r'from\s*(\d+)\s*(?:am|pm|AM|PM)\s*to\s*(\d+)\s*(?:am|pm|AM|PM)', prompt.lower())
    if time_match:
        start = int(time_match.group(1))
        end = int(time_match.group(2))
        if start < end and end - start <= 12:
            hours = []
            for h in range(start, end + 1, 2):
                ampm = "AM" if h < 12 else "PM"
                display_hour = h if h <= 12 else h - 12
                hours.append(f"{display_hour}:00 {ampm}")
    
    return days, hours

def generate_schedule_with_gemini(prompt, days, time_slots):
    """Use Gemini to generate the actual schedule with rate limit handling"""
    schedule_prompt = f"""
    Based on this request: "{prompt}"
    Create a schedule with {days} days and these time slots: {', '.join(time_slots)}
    
    Return ONLY a JSON object with this exact format:
    {{
        "title": "Schedule Title",
        "days": ["Day1", "Day2", ...],
        "activities": {{
            "Day1": ["Activity for time 1", "Activity for time 2", ...],
            "Day2": ["Activity for time 1", "Activity for time 2", ...]
        }}
    }}
    Each activity should be specific to the request.
    Make activities concise (4-6 words max).
    """
    
    global text_model
    
    # Try each model if one fails
    for model_name in MODELS_TO_TRY:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(schedule_prompt)
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                schedule_data = json.loads(json_match.group())
                return schedule_data
        except Exception as e:
            error_msg = str(e)
            if '429' in error_msg or 'quota' in error_msg.lower():
                print(f"Rate limit on {model_name}, trying next...")
                continue
            elif '404' in error_msg or 'not found' in error_msg.lower():
                print(f"Model {model_name} not available, trying next...")
                continue
            else:
                print(f"Error with {model_name}: {e}")
                continue
    
    # ============================================
    # SMART FALLBACK SCHEDULE (No API needed)
    # ============================================
    fallback_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][:days]
    
    # Detect topic from prompt
    prompt_lower = prompt.lower()
    if 'math' in prompt_lower or 'mathematics' in prompt_lower:
        topics = ['Algebra', 'Geometry', 'Calculus', 'Statistics', 'Trigonometry', 'Probability', 'Review']
        title = "📐 MATH STUDY PLAN"
    elif 'science' in prompt_lower or 'physics' in prompt_lower or 'chemistry' in prompt_lower:
        topics = ['Physics', 'Chemistry', 'Biology', 'Lab Work', 'Theory', 'Practice', 'Review']
        title = "🔬 SCIENCE SCHEDULE"
    elif 'yoga' in prompt_lower:
        topics = ['Sun Salutation', 'Warrior Pose', 'Tree Pose', 'Meditation', 'Breathing', 'Stretching', 'Relaxation']
        title = "🧘 YOGA ROUTINE"
    elif 'work' in prompt_lower or 'job' in prompt_lower or 'office' in prompt_lower:
        topics = ['Meetings', 'Deep Work', 'Planning', 'Research', 'Design', 'Testing', 'Review']
        title = "💼 WORK SCHEDULE"
    elif 'exam' in prompt_lower or 'test' in prompt_lower:
        topics = ['Revision', 'Practice Test', 'Review', 'Flashcards', 'Mock Exam', 'Analysis', 'Rest']
        title = "📚 EXAM PREP"
    elif 'gym' in prompt_lower or 'workout' in prompt_lower or 'fitness' in prompt_lower:
        topics = ['Cardio', 'Strength', 'Core', 'Stretching', 'HIIT', 'Yoga', 'Recovery']
        title = "💪 FITNESS PLAN"
    elif 'coding' in prompt_lower or 'programming' in prompt_lower or 'developer' in prompt_lower:
        topics = ['Coding', 'Debugging', 'Review', 'Learning', 'Projects', 'Documentation', 'Testing']
        title = "💻 CODE SCHEDULE"
    else:
        topics = ['Study', 'Review', 'Practice', 'Read', 'Notes', 'Focus', 'Learn']
        title = "📅 MY SCHEDULE"
    
    # Distribute topics across days and time slots
    fallback_activities = {}
    for i, day in enumerate(fallback_days):
        day_activities = []
        for j in range(len(time_slots)):
            topic_idx = (i + j) % len(topics)
            if i % 2 == 0:
                day_activities.append(f"{topics[topic_idx]} (Deep Focus)")
            else:
                day_activities.append(f"{topics[topic_idx]} (Review)")
        fallback_activities[day] = day_activities
    
    return {
        "title": title,
        "days": fallback_days,
        "activities": fallback_activities
    }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        file_data = data.get('file', None)
        
        # Handle file upload
        if file_data:
            try:
                import base64
                import io
                image_data = base64.b64decode(file_data.split(',')[1] if ',' in file_data else file_data)
                image = Image.open(io.BytesIO(image_data))
                
                # Try each model
                for model_name in MODELS_TO_TRY:
                    try:
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content([
                            f"The user uploaded this image and said: '{user_message}'. Please analyze the image and help them with their request.",
                            image
                        ])
                        return jsonify({'response': response.text})
                    except Exception as e:
                        if '429' in str(e) or 'quota' in str(e).lower():
                            continue
                        if '404' in str(e) or 'not found' in str(e).lower():
                            continue
                        raise e
                
                return jsonify({'response': "⚠️ I'm currently rate-limited. Please wait a moment and try again. (Free tier: 20 requests/day)"})
            except Exception as e:
                return jsonify({'response': f"⚠️ I couldn't process the image: {str(e)}"})
        
        # Regular chat - try each model
        for model_name in MODELS_TO_TRY:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(user_message)
                return jsonify({'response': response.text})
            except Exception as e:
                error_msg = str(e)
                if '429' in error_msg or 'quota' in error_msg.lower():
                    continue
                if '404' in error_msg or 'not found' in error_msg.lower():
                    continue
                raise e
        
        return jsonify({'response': "⚠️ I've reached my daily limit. Please wait a moment or try again tomorrow. (Free tier: 20 requests/day)"})
        
    except Exception as e:
        error_msg = str(e)
        if '429' in error_msg or 'quota' in error_msg.lower():
            return jsonify({'response': "⚠️ I've reached my daily limit. Please wait a moment or try again tomorrow. (Free tier: 20 requests/day)"})
        return jsonify({'response': f"Error: {error_msg}"})

@app.route('/generate-image', methods=['POST'])
def generate_image():
    try:
        data = request.json
        prompt = data.get('prompt', 'Create a weekly schedule')
        
        # Extract schedule details
        num_days, time_slots = extract_schedule_details(prompt)
        
        # Generate schedule using Gemini (with fallback)
        schedule_data = generate_schedule_with_gemini(prompt, num_days, time_slots)
        
        days = schedule_data.get('days', ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][:num_days])
        activities_by_day = schedule_data.get('activities', {})
        
        # Ensure activities match days
        if not activities_by_day or len(activities_by_day) != len(days):
            activities_by_day = {}
            for day in days:
                activities_by_day[day] = [f"Activity {i+1}" for i in range(len(time_slots))]
        
        # Pick random color palette
        palette = random.choice(COLOR_PALETTES)
        
        # Dynamic image dimensions
        margin = 30
        header_height = 75
        row_height = 55
        time_col_width = 70
        
        cell_width = 140 if num_days <= 5 else 110 if num_days <= 7 else 90
        
        width = margin * 2 + time_col_width + (cell_width * num_days) + 20
        height = header_height + 40 + (row_height * len(time_slots)) + 50
        
        width = max(width, 700)
        height = max(height, 500)
        
        # Create image
        img = Image.new('RGB', (width, height), color=palette['bg'])
        draw = ImageDraw.Draw(img)
        
        # Load fonts
        try:
            font_title = ImageFont.truetype("arial.ttf", 26)
            font_subtitle = ImageFont.truetype("arial.ttf", 14)
            font_header = ImageFont.truetype("arial.ttf", 15)
            font_text = ImageFont.truetype("arial.ttf", 12)
            font_time = ImageFont.truetype("arial.ttf", 14)
            font_footer = ImageFont.truetype("arial.ttf", 12)
        except:
            font_title = font_subtitle = font_header = font_text = font_time = font_footer = ImageFont.load_default()
        
        # Header with gradient
        for i in range(header_height):
            ratio = i / header_height
            r1, g1, b1 = hex_to_rgb(palette['primary'])
            r2, g2, b2 = hex_to_rgb(palette['accent'])
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            draw.rectangle([0, i, width, i+1], fill=(r, g, b))
        
        # Title
        title = schedule_data.get('title', '📅 SCHEDULE PLANNER')
        if num_days == 1:
            title += " (1 Day)"
        elif num_days <= 5:
            title += f" ({num_days} Days)"
        
        draw.text((margin + 10, 10), title, fill='#FFFFFF', font=font_title)
        
        subtitle = prompt[:55] + '...' if len(prompt) > 55 else prompt
        draw.text((margin + 10, 45), f"📌 {subtitle}", fill='#FFFFFF', font=font_subtitle)
        
        # Table header
        y_start = header_height + 20
        
        for i, day in enumerate(days):
            x = margin + time_col_width + i * cell_width
            draw.rectangle([x, y_start, x + cell_width, y_start + 35], fill=palette['primary'])
            display_day = day[:4] if num_days > 5 else day[:6]
            text_width = draw.textlength(display_day, font=font_header)
            text_x = x + (cell_width - text_width) // 2
            draw.text((text_x, y_start + 8), display_day, fill='#FFFFFF', font=font_header)
        
        # Table rows
        y = y_start + 35
        emojis = ['📚', '✏️', '📖', '💡', '🎯', '⭐', '🔥', '💪', '🧘', '🎨', '🧠', '💻', '📝']
        
        for time_idx, time in enumerate(time_slots):
            if time_idx % 2 == 0:
                draw.rectangle([margin, y, width - margin, y + row_height], fill=palette['card'])
            else:
                draw.rectangle([margin, y, width - margin, y + row_height], fill=palette['bg'])
            
            # Time label
            draw.rectangle([margin, y, margin + time_col_width, y + row_height], fill=palette['secondary'])
            text_width = draw.textlength(time, font=font_time)
            text_x = margin + (time_col_width - text_width) // 2
            draw.text((text_x, y + 18), time, fill=palette['text'], font=font_time)
            
            # Activities
            for day_idx in range(num_days):
                x = margin + time_col_width + day_idx * cell_width
                day_name = days[day_idx]
                
                day_activities = activities_by_day.get(day_name, [])
                activity = day_activities[time_idx] if time_idx < len(day_activities) else "Break"
                
                if activity and activity != "Break":
                    emoji = random.choice(emojis)
                    dot_color = random.choice([palette['primary'], palette['accent']])
                    dot_x = x + 6
                    dot_y = y + 20
                    draw.ellipse([dot_x, dot_y, dot_x + 8, dot_y + 8], fill=dot_color)
                    
                    display_text = f"{emoji} {activity[:12]}"
                    if len(activity) > 12:
                        display_text = f"{emoji} {activity[:10]}.."
                    
                    max_text_width = cell_width - 20
                    temp_font = font_text
                    for size in range(13, 9, -1):
                        try:
                            test_font = ImageFont.truetype("arial.ttf", size)
                            test_width = draw.textlength(display_text, font=test_font)
                            if test_width <= max_text_width:
                                temp_font = test_font
                                break
                        except:
                            pass
                    
                    text_x = x + 18
                    text_y = y + 17
                    draw.text((text_x, text_y), display_text, fill=palette['text'], font=temp_font)
                else:
                    dot_x = x + 10
                    dot_y = y + 24
                    draw.ellipse([dot_x, dot_y, dot_x + 5, dot_y + 5], fill='#3a3a5a')
            
            y += row_height
        
        # Grid lines
        for i in range(num_days + 1):
            x = margin + time_col_width + i * cell_width
            draw.line([x, y_start + 35, x, y], fill='#3a3a5a', width=1)
        
        y_line = y_start + 35
        for i in range(len(time_slots) + 1):
            draw.line([margin, y_line, width - margin, y_line], fill='#3a3a5a', width=1)
            y_line += row_height
        
        # Footer
        footer_y = height - 30
        quotes = [
            "✨ Stay consistent, stay focused",
            "📚 Small steps lead to big results",
            "💪 You've got this!",
            "🎯 Every day is progress",
            "⭐ Keep pushing forward"
        ]
        draw.text((margin + 10, footer_y), random.choice(quotes), fill=palette['text'], font=font_footer)
        
        brand_text = f"📅 Wi Ha Joon ({num_days} days)"
        brand_width = draw.textlength(brand_text, font=font_footer)
        draw.text((width - margin - brand_width - 10, footer_y), brand_text, fill=palette['text'], font=font_footer)
        
        # Save
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        filename = f'planner_{timestamp}.png'
        image_path = os.path.join('static', filename)
        img.save(image_path, quality=95)
        
        return jsonify({
            'image_url': f'/{image_path}',
            'success': True,
            'days': num_days,
            'time_slots': len(time_slots),
            'schedule': schedule_data
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)