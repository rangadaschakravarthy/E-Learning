from datetime import datetime
import os
import random
import signal
import subprocess
import tempfile
from flask import Flask, abort, jsonify, render_template, request, redirect, send_from_directory, url_for, session, flash, make_response,send_file
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
import re
from PIL import Image, ImageDraw,ImageFont

app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Anurag@123'
app.config['MYSQL_DB'] = 'wt'
app.secret_key = 'xyz'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '22eg112c10@anurag.edu.in'
app.config['MAIL_PASSWORD'] = 'Abcdefgh123'

mail = Mail(app)
mysql = MySQL(app)

otp_storage = {} 

TIMER_DURATION = 3600  
COOLDOWN_DURATION = 10

def send_otp_email(email, otp):
    subject = "Your OTP for Registration"
    body = f"""
    Hi,

    Your OTP for registration is: {otp}

    Please enter this OTP to complete your registration.

    Best regards,
    The Team
    """
    msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[email])
    msg.body = body
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")
def check_login():
    user_id = request.cookies.get('user_id')
    if user_id:
        cur = mysql.connection.cursor()
        cur.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        if user:
            session['logged_in'] = True
            session['username'] = user[0]
def get_db_connection():
    cur=mysql.connection.cursor()
    return cur

def extract_class_name(code):
    """
    Extracts the class name from Java code.
    This will match the class name regardless of whether it's public or has other modifiers.
    """
    match = re.search(r'class\s+(\w+)', code)
    if match:
        return match.group(1)
    else:
        return "No class found in the code"
    
def generate_certificate(name, course_name):
    if course_name == "Python":
        template_path = "static/certificate_template.png"
    elif course_name == "JavaScript":
        template_path = "static/jscertificate_template.png"
    elif course_name == "Java":
        template_path = "static/javacertificate_template.png"
    elif course_name == "C":
        template_path = "static/ccertificate_template.png"
    else:
        template_path = "static/cpluscertificate_template.png"
    certificate = Image.open(template_path)
    font_path = "arial.ttf" 
    font_size = 70
    font = ImageFont.truetype(font_path, font_size)
    draw = ImageDraw.Draw(certificate)
    name_position = (1150, 720)  
    draw.text(name_position, name, font=font, fill="black")
    output_dir = "static/certificates"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_path = os.path.join(output_dir, f"{name}_{course_name}.png")
    certificate.save(output_path)
    print(f"Certificate saved as {output_path}")

@app.route('/')
def home():
    check_login()
    logged_in = session.get('logged_in', False)
    cur = mysql.connection.cursor()
    cur.execute("SELECT course_name, description, image_url FROM courses LIMIT 3")
    courses = cur.fetchall()
    cur.close()

    courses_dict = [
        {'course_name': course[0], 'description': course[1], 'image_url': course[2]}
        for course in courses
    ]
    return render_template('home.html', logged_in=logged_in, courses=courses_dict)

@app.route('/sign', methods=['GET', 'POST'])
def sign():
    if request.method == 'POST':
        if 'login' in request.form:
            username = request.form['username']
            password = request.form['password']
            cur = mysql.connection.cursor()
            cur.execute("SELECT id FROM users WHERE username = %s AND password = %s", (username, password))
            user = cur.fetchone()
            cur.close()

            if user:
                session['logged_in'] = True
                session['username'] = username

                response = make_response(redirect(url_for('home')))
                response.set_cookie('user_id', str(user[0]), max_age=30 * 24 * 60 * 60)  
                return response
            else:
                flash('Invalid username or password', 'danger')
                return render_template('sign.html')

        elif 'signup' in request.form:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            if not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                flash('Invalid email address', 'danger')
                return render_template('sign.html')

            if password != confirm_password:
                flash('Passwords do not match', 'danger')
                return render_template('sign.html')
            otp = str(random.randint(100000, 999999))
            otp_storage[email] = otp
            send_otp_email(email, otp)
            session['email'] = email
            session['username'] = username
            session['password'] = password
            flash('An OTP has been sent to your email. Please enter it below to complete registration.', 'info')
            return render_template('otp_verification.html')
    return render_template('sign.html')

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form['otp']
        email = session.get('email')
        if email and entered_otp == otp_storage.get(email):
            username = session.get('username')
            password = session.get('password')
            cur = mysql.connection.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL,
                    email VARCHAR(100) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            mysql.connection.commit()

            cur.execute("INSERT INTO users (username, password, email) VALUES (%s, %s, %s)", (username, password, email))
            mysql.connection.commit()
            cur.close()

            otp_storage.pop(email, None)
            session.pop('email', None)
            session.pop('username', None)
            session.pop('password', None)
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('sign'))

        flash('Invalid or expired OTP. Please try again.', 'danger')
        return render_template('otp_verification.html')

    return redirect(url_for('sign'))

@app.route('/otp_verification', methods=['GET'])
def otp_verification():
    return render_template('otp_verification.html')


@app.route('/compiler')
def course_detail():
    # Your logic to fetch and render course details
    return render_template('compiler.html')

@app.route('/enroll/<course_name>', methods=['POST'])
def enroll(course_name):
    check_login()
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    username = session.get('username')

    cur = mysql.connection.cursor()
    # Check if user is already enrolled in the course
    cur.execute("SELECT * FROM enrollments WHERE username = %s AND course_name = %s", (username, course_name))
    enrollment = cur.fetchone()

    if enrollment:
        flash(f'You are already enrolled in {course_name}!', 'warning')
        return redirect(url_for('course_det', course_name=course_name))

    cur.execute("INSERT INTO enrollments (username, course_name) VALUES (%s, %s)", (username, course_name))
    mysql.connection.commit()
    cur.close()

    flash(f'You have been enrolled in {course_name}!', 'success')
    return redirect(url_for('profile'))

@app.route('/courses', methods=['GET', 'POST'])
def courses():
    check_login()
    if not session.get('logged_in'):
        return redirect(url_for('sign'))

    cur = mysql.connection.cursor()
    username = session.get('username')
    cur.execute("SELECT username, email, created_at FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.execute("""
        SELECT course_name, description, image_url, roadmap_url, video_url, notes_url 
        FROM courses
    """)
    courses = cur.fetchall()
    cur.close()

    user_dict = {'username': user[0], 'email': user[1], 'created_at': user[2]}
    
    courses_dict = [
        {
            'course_name': course[0],
            'description': course[1],
            'image_url': course[2],
            'roadmap_url': course[3],
            'video_url': course[4],
            'notes_url': course[5]
        }
        for course in courses
    ]
    return render_template('courses.html', user=user_dict,courses=courses_dict)

course_intro = {
    "python": {
        "name": "Python",
        "description": "Python is a versatile, high-level programming language known for its simplicity and readability.",
        "demand": [
            "Python is one of the most popular programming languages globally.",
            "Its adaptability to various fields contributes to its growing demand."
        ],
        "skills": [
            "Build web applications using Django or Flask.",
            "Create automation scripts for repetitive tasks.",
            "Develop machine learning models using TensorFlow or PyTorch."
        ],
        "companies": [
            "Google",
            "Netflix",
            "Spotify",
            "NASA"
        ],
        "nextCourses": [
            "Advanced Python programming",
            "Data Science and Analysis",
            "Machine Learning and AI Development"
        ]
    },
    "java": {
        "name": "Java",
        "description": "Java is a robust, object-oriented programming language known for its platform independence and reliability.",
        "demand": [
            "Java remains a core technology for backend systems.",
            "It powers Android development."
        ],
        "skills": [
            "Develop Android mobile applications.",
            "Build enterprise-grade applications using Spring Boot."
        ],
        "companies": [
            "Amazon",
            "LinkedIn",
            "IBM",
            "Twitter"
        ],
        "nextCourses": [
            "Spring Boot for enterprise development",
            "Kotlin for modern Android development"
        ]
    },
    "javascript": {
        "name": "JavaScript",
        "description": "JavaScript is a dynamic, high-level programming language that is a core part of web development for both front-end and back-end programming.",
        "demand": [
            "JavaScript is essential for web development and is used by almost every modern website.",
            "Its role in building interactive websites and web applications has made it indispensable."
        ],
        "skills": [
            "Build dynamic web pages with HTML, CSS, and JavaScript.",
            "Develop full-stack applications using Node.js.",
            "Create single-page applications (SPAs) with frameworks like React or Angular."
        ],
        "companies": [
            "Facebook (React, Node.js)",
            "Google (Angular, Chrome)",
            "Microsoft (TypeScript, Node.js)"
        ],
        "nextCourses": [
            "Advanced JavaScript (ES6+)",
            "React and Vue.js for front-end development",
            "Node.js for back-end development"
        ]
    },
    "c": {
        "name": "C",
        "description": "C is a powerful, general-purpose programming language that serves as the foundation for many other languages.",
        "demand": [
            "C is in demand for developing operating systems, compilers, and real-time applications.",
            "It is highly valued for its ability to provide low-level memory access and performance optimization."
        ],
        "skills": [
            "Build operating systems and system software.",
            "Develop embedded systems for IoT and hardware devices.",
            "Write efficient programs for high-performance applications."
        ],
        "companies": [
            "Microsoft (Windows kernel development)",
            "Apple (macOS and iOS development)",
            "Intel (embedded systems and firmware)"
        ],
        "nextCourses": [
            "C++ for object-oriented programming",
            "Embedded systems programming",
            "Data structures and algorithms for competitive programming"
        ]
    },
    "c++": {
        "name": "C++",
        "description": "C++ is an extension of C that introduces object-oriented programming (OOP) concepts. It is widely used for game development, system software, and performance-critical applications.",
        "demand": [
            "C++ is in high demand for its role in developing high-performance software, real-time systems, and video games.",
            "It is essential for industries requiring low-latency and memory-efficient applications."
        ],
        "skills": [
            "Develop video games using engines like Unreal Engine.",
            "Work on system software and compilers.",
            "Create performance-critical financial or scientific applications."
        ],
        "companies": [
            "Adobe (Photoshop and other creative tools)",
            "Electronic Arts (game development)",
            "Bloomberg (financial systems)"
        ],
        "nextCourses": [
            "Advanced C++ concepts like STL, multithreading, and memory management",
            "Game development with Unreal Engine or Unity",
            "Data structures and algorithms for software engineering roles"
        ]
    }
}




@app.route('/intro/<course_name>', methods=['GET', 'POST'])
def courses_intro(course_name):
    return render_template('courses_intro.html', course_name=course_name, course_intro=course_intro)

@app.route('/execute', methods=['POST'])
def execute_code():
    data = request.json
    if not data or 'code' not in data or 'language' not in data:
        return jsonify({'error': 'Invalid code or language'}), 400

    code = data['code']
    language = data['language']
    
    try:
        if language == 'C':
            file_extension = '.c'
        elif language == 'C++':
            file_extension = '.cpp'
        elif language == 'Java':
            file_extension = '.java'
        elif language == 'Python':
            file_extension = '.py'
        elif language == 'JavaScript':
            file_extension = '.js'
        else:
            return jsonify({'error': 'Unsupported language'}), 400
        
        temp_file = tempfile.NamedTemporaryFile(suffix=file_extension, delete=False)
        temp_file.write(code.encode())
        temp_file.close()

        if language == 'Python':
            command = ['python', temp_file.name]
        elif language == 'JavaScript':
            command = ['node', temp_file.name]
        elif language == 'C++':
            compile_command = ['g++', temp_file.name, '-o', temp_file.name + '.out']
            compile_process = subprocess.run(compile_command, capture_output=True, text=True)
            if compile_process.returncode != 0:
                os.remove(temp_file.name)
                return jsonify({'error': compile_process.stderr}), 400
            command = [temp_file.name + '.out']
        elif language == 'Java':
            # Java compilation
            compile_command = ['javac', temp_file.name]
            compile_process = subprocess.run(compile_command, capture_output=True, text=True)
            if compile_process.returncode != 0:
                os.remove(temp_file.name)
                return jsonify({'error': compile_process.stderr}), 400
            
            # Extract the class name from the Java code
            class_name = extract_class_name(code)
            if not class_name:
                os.remove(temp_file.name)
                return jsonify({'error': 'No class found in the code'}), 400

            # Execute the Java program
            command = ['java', '-cp', os.path.dirname(temp_file.name), class_name]

        elif language == 'C':
            compile_command = ['gcc', temp_file.name, '-o', temp_file.name + '.out']
            compile_process = subprocess.run(compile_command, capture_output=True, text=True)
            if compile_process.returncode != 0:
                os.remove(temp_file.name)
                return jsonify({'error': compile_process.stderr}), 400
            command = [temp_file.name + '.out']

        process = subprocess.run(command, capture_output=True, text=True)
        output = process.stdout or process.stderr

        os.remove(temp_file.name)
        return jsonify({'output': output})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    check_login()
    if not session.get('logged_in'):
        return redirect(url_for('sign'))

    username = session.get('username')
    cur = mysql.connection.cursor()

    # User details
    cur.execute("SELECT id,username, email, created_at FROM users WHERE username = %s", (username,))
    user = cur.fetchone()

    # Enrolled courses
    cur.execute("""
        SELECT c.course_name, c.description, c.image_url, e.progress 
        FROM enrollments e 
        JOIN courses c ON e.course_name = c.course_name 
        WHERE e.username = %s
    """,(username,))
    enrolled_courses = cur.fetchall()
    cur.close()

    enrolled_courses_list = [
        {'course_name': course[0], 'description': course[1], 'image_url': course[2], 'progress': course[3]}
        for course in enrolled_courses
    ]

    user_dict = {'user_id':user[0],'username': user[1], 'email': user[2], 'created_at': user[3]}

    return render_template('profile.html', user=user_dict, enrolled_courses=enrolled_courses_list)

@app.route('/certificate/<username>/<course_name>')
def show_certificate(username, course_name):
    certificate_dir = os.path.join(app.static_folder, 'certificates')
    filename = f"{username}_{course_name}.png"
    if os.path.exists(os.path.join(certificate_dir, filename)):
        return send_from_directory(certificate_dir, filename)
    else:
        abort(404, description="Certificate not found")

@app.route('/get_quiz_script', methods=['GET'])
def get_quiz_script():
    course_name = request.args.get('course_name')
    quiz_scripts = {
        'Python': 'python_quiz.js',
        'JavaScript': 'javascript_quiz.js',
        'C++': 'cpp_quiz.js',
        'Java': 'java_quiz.js',
        'C': 'c_quiz.js'
    }
    
    quiz_script = quiz_scripts.get(course_name, None)
    if quiz_script:
        return jsonify({'quiz_script': quiz_script})
    return jsonify({'quiz_script': None})

concepts = {
    "python": {
        "beginner": ["Variables and Data Types", "Conditional Statements", "Loops", "Functions", "Basic Input/Output"],
        "intermediate": ["File Handling", "Modules and Packages", "Error Handling", "Object-Oriented Programming", "Decorators"],
        "advanced": ["Generators", "Multithreading and Multiprocessing", "Data Analysis with Pandas", "Machine Learning Basics", "Web Development with Flask"]
    },
    "c": {
        "beginner": ["Basic Syntax", "Data Types", "Loops", "Functions", "Pointers"],
        "intermediate": ["File Handling", "Dynamic Memory Allocation", "Structures and Unions", "Preprocessors", "Recursion"],
        "advanced": ["Multithreading", "Socket Programming", "Data Structures", "Compiler Design Basics", "Memory Management"]
    },
    "c++": {
        "beginner": ["Basic Syntax", "Input/Output", "Control Structures", "Functions", "Arrays"],
        "intermediate": ["Classes and Objects", "Inheritance", "Polymorphism", "File Handling", "Templates"],
        "advanced": ["STL (Standard Template Library)", "Multithreading", "Smart Pointers", "Memory Management", "Game Development Basics"]
    },
    "java": {
        "beginner": ["Basic Syntax", "Data Types", "Control Flow Statements", "Loops", "Functions"],
        "intermediate": ["Object-Oriented Programming", "Exception Handling", "Collections Framework", "File Handling", "Multithreading"],
        "advanced": ["JavaFX", "JDBC (Database Connectivity)", "Spring Framework Basics", "Microservices", "RESTful APIs"]
    },
    "javascript": {
        "beginner": ["Variables and Data Types", "Functions", "DOM Manipulation", "Events", "Loops"],
        "intermediate": ["Promises and Async/Await", "ES6 Features", "APIs and Fetch", "Error Handling", "Modules"],
        "advanced": ["React Basics", "Node.js Basics", "WebSockets", "Authentication and Authorization", "Performance Optimization"]
    }
}

@app.route("/concepts/<course_name>")
def display_concepts(course_name):
    course_concepts = concepts.get(course_name.lower(), {})
    return render_template("concepts.html", course_name=course_name, course_concepts=course_concepts)

# Change password route
@app.route('/change_password', methods=['POST'])
def change_password():
    check_login()
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    username = session.get('username')
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_new_password = request.form['confirm_new_password']

    cur = mysql.connection.cursor()
    cur.execute("SELECT password FROM users WHERE username = %s", (username,))
    user_password = cur.fetchone()[0]

    if current_password != user_password:
        error = "Incorrect current password"
        return redirect(url_for('profile', error=error))

    if new_password != confirm_new_password:
        error = "Passwords do not match"
        return redirect(url_for('profile', error=error))

    cur.execute("UPDATE users SET password = %s WHERE username = %s", (new_password, username))
    mysql.connection.commit()
    cur.close()

    flash("Password changed successfully!", "success")
    return redirect(url_for('profile'))
@app.route('/about',methods=['GET','POST'])
def about():
    return render_template('about.html')
# Logout route
@app.route('/logout')
def logout():
    session.clear()  # Clear all session data
    response = make_response(redirect(url_for('home')))
    response.set_cookie('user_id', '', expires=0)
    return response

@app.route('/course_detail/<course_name>', methods=['GET'])
def course_det(course_name):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT course_name, description, image_url, roadmap_url, video_url, notes_url 
        FROM courses
        WHERE course_name = %s
    """, (course_name,))
    course = cur.fetchone()  # Fetch a single row
    cur.close()

    if course:
        course_dict = {
            'course_name': course[0],
            'description': course[1],
            'image_url': course[2],
            'roadmap_url': course[3],
            'video_url': course[4],
            'notes_url': course[5]
        }
        return render_template('course_detail.html', course=course_dict, course_name=course_name)
    else:
        return "Course not found", 404

@app.route('/quiz/<course_name>', methods=['GET', 'POST'])
def quiz(course_name):
    # Define quiz script mapping for different courses
    quiz_scripts = {
        'Python': 'pythonquiz.js',
        'JavaScript': 'javascript.js',
        'C++': 'cpp.js',
        'Java': 'javaquiz.js',
        'C': 'cquiz.js'
    }

    # Fetch the correct script for the given course name
    quiz_script = quiz_scripts.get(course_name, None)
    if quiz_script:
        return render_template('quiz.html', quiz_script=quiz_script, course_name=course_name)
    return "Quiz not found", 404

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    data = request.get_json()
    score = data.get('score')
    course_name = data.get('course_name')
    # totalQuestions = 2
    percentage = data.get('percentage') #int((score / totalQuestions) * 100)
    username = session['username']
    if percentage > 60:
        generate_certificate(username.capitalize(),course_name)
        
        try:
            cur = mysql.connection.cursor()
            query = "UPDATE enrollments SET progress = %s WHERE course_name = %s AND username = %s"
            cur.execute(query, (percentage, course_name, username))
            mysql.connection.commit()
            print("Database updated successfully!")
        except Exception as e:
            print("Error while updating the database:", str(e)) 
        finally:
            cur.close()
    
    return jsonify({"message": "Progress saved successfully", "progress": percentage})

PROBLEMS = {
    1: {
        'id': 1,
        'title': "Two Sum",
        'description': "Given an array of integers, return indices of the two numbers such that they add up to a specific target.",
        'test_cases': [
            {
                'input': "nums = [2, 7, 11, 15], target = 9",
                'output': "Indices: [0, 1]",
            }
        ],
    },
    2: {
        'id': 2,
        'title': "Two Sum II - Input Sorted Array",
        'description': "Given a sorted array of integers and a target sum, return the indices of two numbers such that they add up to the target.",
        'test_cases': [
            {
                'input': "nums = [1, 2, 3, 4, 5], target = 6",
                'output': "Indices: [1, 4]",
            }
        ],
    },
    3: {
        'id': 3,
        'title': "Palindrome Number",
        'description': "Determine whether an integer is a palindrome. An integer is a palindrome if it reads the same forward and backward.",
        'test_cases': [
            {
                'input': "x = 121",
                'output': "True",
            }
        ],
    },
    4: {
        'id': 4,
        'title': "Reverse Integer",
        'description': "Given a 32-bit signed integer, reverse the digits of the integer.",
        'test_cases': [
            {
                'input': "x = 123",
                'output': "321",
            }
        ],
    },
    5: {
        'id': 5,
        'title': "Roman to Integer",
        'description': "Convert a Roman numeral to an integer.",
        'test_cases': [
            {
                'input': "s = 'III'",
                'output': "3",
            }
        ],
    },
    6: {
        'id': 6,
        'title': "Longest Substring Without Repeating Characters",
        'description': "Given a string, find the length of the longest substring without repeating characters.",
        'test_cases': [
            {
                'input': "s = 'abcabcbb'",
                'output': "3",
            }
        ],
    },
    7: {
        'id': 7,
        'title': "Valid Parentheses",
        'description': "Given a string containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.",
        'test_cases': [
            {
                'input': "s = '()[]{}'",
                'output': "True",
            }
        ],
    },
    8: {
        'id': 8,
        'title': "Merge Two Sorted Lists",
        'description': "Merge two sorted linked lists into one sorted list.",
        'test_cases': [
            {
                'input': "l1 = [1, 2, 4], l2 = [1, 3, 4]",
                'output': "[1, 1, 2, 3, 4, 4]",
            }
        ],
    },
    9: {
        'id': 9,
        'title': "Search Insert Position",
        'description': "Given a sorted array and a target value, return the index where the target should be inserted so that the array remains sorted.",
        'test_cases': [
            {
                'input': "nums = [1, 3, 5, 6], target = 5",
                'output': "2",
            }
        ],
    },
    10: {
        'id': 10,
        'title': "Remove Duplicates from Sorted Array",
        'description': "Given a sorted array, remove the duplicates in-place such that each element appears only once and return the new length of the array.",
        'test_cases': [
            {
                'input': "nums = [1, 1, 2]",
                'output': "2",
            }
        ],
    },
    11: {
        'id': 11,
        'title': "Maximum Subarray",
        'description': "Given an integer array 'nums', find the contiguous subarray (containing at least one number) which has the largest sum and return its sum.",
        'test_cases': [
            {
                'input': "nums = [-2, 1, -3, 4, -1, 2, 1, -5, 4]",
                'output': "6",
            }
        ],
    },
        12: {
        'id': 12,
        'title': "Climbing Stairs",
        'description': "You are climbing a staircase. It takes n steps to reach the top. Each time you can either climb 1 or 2 steps. In how many distinct ways can you climb to the top?",
        'test_cases': [
            {
                'input': "n = 2",
                'output': "2",
            }
        ],
    },
    13: {
        'id': 13,
        'title': "Merge Intervals",
        'description': "Given an array of intervals where intervals[i] = [starti, endi], merge all overlapping intervals.",
        'test_cases': [
            {
                'input': "intervals = [[1, 3], [2, 6], [8, 10], [15, 18]]",
                'output': "[[1, 6], [8, 10], [15, 18]]",
            }
        ],
    },
    14: {
        'id': 14,
        'title': "Find Peak Element",
        'description': "A peak element is an element that is strictly greater than its neighbors. Find a peak element and return its index.",
        'test_cases': [
            {
                'input': "nums = [1, 2, 3, 1]",
                'output': "2",
            }
        ],
    },
    15: {
        'id': 15,
        'title': "Single Number",
        'description': "Given a non-empty array of integers nums, every element appears twice except for one. Find that single one.",
        'test_cases': [
            {
                'input': "nums = [2, 2, 1]",
                'output': "1",
            }
        ],
    },
    16: {
        'id': 16,
        'title': "Valid Anagram",
        'description': "Given two strings s and t, return true if t is an anagram of s, and false otherwise.",
        'test_cases': [
            {
                'input': "s = 'anagram', t = 'nagaram'",
                'output': "True",
            }
        ],
    },
    17: {
        'id': 17,
        'title': "Majority Element",
        'description': "Given an array nums of size n, return the majority element. The majority element is the element that appears more than n / 2 times.",
        'test_cases': [
            {
                'input': "nums = [3, 2, 3]",
                'output': "3",
            }
        ],
    },
    18: {
        'id': 18,
        'title': "Contains Duplicate",
        'description': "Given an integer array nums, return true if any value appears at least twice in the array, and false if every element is distinct.",
        'test_cases': [
            {
                'input': "nums = [1, 2, 3, 1]",
                'output': "True",
            }
        ],
    },
    19: {
        'id': 19,
        'title': "Move Zeroes",
        'description': "Given an integer array nums, move all 0's to the end of it while maintaining the relative order of the non-zero elements.",
        'test_cases': [
            {
                'input': "nums = [0, 1, 0, 3, 12]",
                'output': "[1, 3, 12, 0, 0]",
            }
        ],
    },
    20: {
        'id': 20,
        'title': "Binary Search",
        'description': "Given a sorted array of integers, return the index of the target value using binary search. If not found, return -1.",
        'test_cases': [
            {
                'input': "nums = [-1, 0, 3, 5, 9, 12], target = 9",
                'output': "4",
            }
        ],
    },
    21: {
        'id': 21,
        'title': "Rotate Array",
        'description': "Given an array, rotate the array to the right by k steps, where k is non-negative.",
        'test_cases': [
            {
                'input': "nums = [1, 2, 3, 4, 5, 6, 7], k = 3",
                'output': "[5, 6, 7, 1, 2, 3, 4]",
            }
        ],
    }
}

LANGUAGES = {
    'python': '.py',
    'c': '.c',
    'java': '.java',
    'javascript': '.js',
    'cpp': '.cpp'
}

@app.route('/compete')
def compete():
    # Display the list of problems
    check_login()
    if not session.get('logged_in'):
        return redirect(url_for('sign'))
    cur = mysql.connection.cursor()
    username = session.get('username')
    cur.execute("SELECT username, email, created_at FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    
    user_dict = {'username': user[0], 'email': user[1], 'created_at': user[2]}
    
    return render_template('index.html', user=user_dict,problems=PROBLEMS)

@app.route('/problem/<int:problem_id>')
def problem(problem_id):
    problem = PROBLEMS.get(problem_id)
    if not problem:
        return redirect(url_for('index'))
    return render_template('problem.html', problem=problem)

@app.route('/submit', methods=['POST'])
def submit_code():
    code = request.form['code']
    problem_id = int(request.form['problem_id'])
    language = request.form['language']
    
    problem = PROBLEMS.get(problem_id)
    
    if not problem:
        return redirect(url_for('index'))
    
    # Generate a temporary file for the submitted code
    code_file = save_code_to_file(code, language)
    
    # Run the code based on the selected language
    result = execute_code(code_file, language)
    
    # Initialize a list to hold results for each test case
    test_case_results = []
    
    for i, test_case in enumerate(problem['test_cases']):
        output = result['output'].strip()
        expected_output = test_case['output'].strip()
        
        # Compare output with expected output for each test case
        if output == expected_output:
            status = 'Success'
            message = f'Test Case {i + 1}: Your code has passed this test case!'
        else:
            status = 'Failed'
            message = f'Test Case {i + 1}: Expected: {expected_output}\nYour Output: {output}'
        
        test_case_results.append({
            'test_case': i + 1,
            'status': status,
            'message': message
        })
    
    # Cleanup the temporary code file
    if os.path.exists(code_file):
        os.remove(code_file)
        print(f"Deleted file: {code_file}")  # Debugging line
    
    return render_template('result.html', test_case_results=test_case_results)


def save_code_to_file(code, language):
    """ Save the submitted code to a temporary file based on the selected language. """
    extension = LANGUAGES.get(language)
    if not extension:
        raise ValueError(f"Unsupported language: {language}")

    # Handle Java separately to rename the file dynamically
    if language == 'java':
        class_name = extract_class_name_from_code(code)
        code_file = f'{class_name}.java'  # Rename the file to match the class name
    else:
        code_file = f'temp_code{extension}'

    with open(code_file, 'w') as f:
        f.write(code)
    
    return code_file

def extract_class_name_from_code(code):
    """ Extract the main class name from the provided Java code (without file) """
    match = re.search(r'public\s+class\s+([a-zA-Z_][a-zA-Z0-9_]*)', code)
    if match:
        return match.group(1)
    else:
        raise ValueError("No public class found in the Java code")

def execute_code(code_file, language):
    """ Execute the submitted code based on the selected language. """
    if language == 'python':
        return run_python(code_file)
    elif language == 'c':
        return run_c(code_file)
    elif language == 'java':
        return run_java(code_file)
    elif language == 'javascript':
        return run_javascript(code_file)
    elif language == 'cpp':
        return run_cpp(code_file)

def run_python(code_file):
    try:
        result = subprocess.run(
            ['python', code_file],
            text=True,
            capture_output=True,
            timeout=5  # Set a timeout to avoid infinite loops
        )
        return {'output': result.stdout, 'error': result.stderr}
    except subprocess.TimeoutExpired:
        return {'output': '', 'error': 'Execution timed out'}

def run_c(code_file):
    try:
        # Compile the C code
        subprocess.run(['gcc', code_file, '-o', 'temp_program'], check=True)
        # Execute the compiled program
        result = subprocess.run(
            ['./temp_program'],
            text=True,
            capture_output=True,
            timeout=5
        )
        return {'output': result.stdout, 'error': result.stderr}
    except subprocess.TimeoutExpired:
        return {'output': '', 'error': 'Execution timed out'}
    except subprocess.CalledProcessError as e:
        return {'output': '', 'error': str(e)}

def run_java(code_file):
    try:
        # Step 1: Extract the main class name from the Java code
        class_name = extract_class_name_from_code(open(code_file, 'r').read())
        
        # Step 2: Compile the Java code
        compile_result = subprocess.run(
            ['javac', code_file],
            text=True,
            capture_output=True,
            timeout=5
        )
        
        # Check if there were any compilation errors
        if compile_result.returncode != 0:
            return {'output': '', 'error': f"Compilation failed: {compile_result.stderr}"}
        
        # Step 3: Execute the compiled Java class
        result = subprocess.run(
            ['java', class_name],
            text=True,
            capture_output=True,
            timeout=5
        )
        
        return {'output': result.stdout, 'error': result.stderr}
    
    except subprocess.TimeoutExpired:
        return {'output': '', 'error': 'Execution timed out'}
    
    except subprocess.CalledProcessError as e:
        return {'output': '', 'error': str(e)}
    
    except ValueError as e:
        # Handle the case where the class name could not be extracted
        return {'output': '', 'error': str(e)}

    finally:
        if 'class_name' in locals():
            class_file = f"{class_name}.class"
            if os.path.exists(class_file):
                os.remove(class_file)
        if os.path.exists(code_file):
            os.remove(code_file)

def run_javascript(code_file):
    try:
        result = subprocess.run(
            ['node', code_file],
            text=True,
            capture_output=True,
            timeout=5
        )
        return {'output': result.stdout, 'error': result.stderr}
    except subprocess.TimeoutExpired:
        return {'output': '', 'error': 'Execution timed out'}

def run_cpp(code_file):
    try:
        subprocess.run(['g++', code_file, '-o', 'temp_program'], check=True)
        result = subprocess.run(
            ['./temp_program'],
            text=True,
            capture_output=True,
            timeout=5
        )
        return {'output': result.stdout, 'error': result.stderr}
    except subprocess.TimeoutExpired:
        return {'output': '', 'error': 'Execution timed out'}
    except subprocess.CalledProcessError as e:
        return {'output': '', 'error': str(e)}

projects = {
    "python": {
        "beginner": [
            {"name": "Simple Calculator", "description": "Build a basic calculator."},
            {"name": "To-do List App", "description": "Create a simple to-do list app."},
            {"name": "Guess the Number", "description": "Create a game where the user guesses a random number."},
            {"name": "Basic Alarm Clock", "description": "Create a simple alarm clock using Python."},
            {"name": "Number Converter", "description": "Build a program to convert units (e.g., inches to centimeters)."}
        ],
        "intermediate": [
            {"name": "Weather App", "description": "Create an app that shows weather information using an API."},
            {"name": "Expense Tracker", "description": "Track daily expenses using Python."},
            {"name": "Web Scraper", "description": "Build a program to scrape data from a website."},
            {"name": "Currency Converter", "description": "Build an app to convert currencies."},
            {"name": "Flashcard App", "description": "Create an app that helps you learn new languages with flashcards."}
        ],
        "advanced": [
            {"name": "Machine Learning Model", "description": "Build a machine learning model for predictions."},
            {"name": "Flask Web App", "description": "Create a complete web app using Flask."},
            {"name": "Chatbot", "description": "Develop a chatbot using natural language processing (NLP)."},
            {"name": "Django E-commerce Site", "description": "Build an e-commerce website with Django."},
            {"name": "Blockchain", "description": "Create a simple blockchain implementation in Python."}
        ]
    },
    "c": {
        "beginner": [
            {"name": "Hello World", "description": "Print 'Hello, World' to the console."},
            {"name": "Sum of Two Numbers", "description": "Write a program to sum two integers."},
            {"name": "Prime Number Checker", "description": "Write a program to check if a number is prime."},
            {"name": "Temperature Converter", "description": "Create a program to convert between Celsius and Fahrenheit."},
            {"name": "Even or Odd Checker", "description": "Write a program to check if a number is even or odd."}
        ],
        "intermediate": [
            {"name": "File Handling", "description": "Create a program to read and write files."},
            {"name": "Simple Banking System", "description": "Create a basic banking system."},
            {"name": "Palindrome Checker", "description": "Write a program to check if a word is a palindrome."},
            {"name": "Number Sorting", "description": "Create a program to sort a list of numbers."},
            {"name": "Tic-Tac-Toe Game", "description": "Build a simple console-based Tic-Tac-Toe game."}
        ],
        "advanced": [
            {"name": "Data Structures", "description": "Implement various data structures like linked list, stack, etc."},
            {"name": "Multi-threading Program", "description": "Write a multi-threaded program in C."},
            {"name": "Database Management System", "description": "Implement a simple database system."},
            {"name": "Socket Programming", "description": "Create a client-server application using sockets."},
            {"name": "Compiler", "description": "Create a simple compiler in C for arithmetic expressions."}
        ]
    },
    "c++": {
        "beginner": [
            {"name": "Array Operations", "description": "Perform basic operations on arrays."},
            {"name": "Number Guessing Game", "description": "Create a simple number guessing game."},
            {"name": "Factorial Calculator", "description": "Write a program to calculate the factorial of a number."},
            {"name": "Simple Calculator", "description": "Create a basic calculator with C++."},
            {"name": "Grade Calculator", "description": "Write a program to calculate and print student grades."}
        ],
        "intermediate": [
            {"name": "Class and Object", "description": "Implement a class and object in C++."},
            {"name": "File I/O", "description": "Handle files using file I/O in C++."},
            {"name": "String Manipulation", "description": "Create a program to manipulate strings (concatenate, compare, etc.)."},
            {"name": "Student Information System", "description": "Create a system to manage student data."},
            {"name": "Calendar App", "description": "Build a simple console calendar app."}
        ],
        "advanced": [
            {"name": "STL Containers", "description": "Work with Standard Template Library (STL) in C++."},
            {"name": "Memory Management", "description": "Handle memory allocation and deallocation."},
            {"name": "File Compression Tool", "description": "Create a tool to compress and decompress files."},
            {"name": "Game Development", "description": "Create a simple game using C++ and a graphics library."},
            {"name": "Data Encryption", "description": "Build a program for encrypting and decrypting text."}
        ]
    },
    "java": {
        "beginner": [
            {"name": "Hello Java", "description": "Write a basic 'Hello, World' program."},
            {"name": "Basic Calculator", "description": "Create a simple calculator."},
            {"name": "Odd or Even", "description": "Write a program to check if a number is odd or even."},
            {"name": "Factorial Calculator", "description": "Build a program to calculate the factorial of a number."},
            {"name": "Basic ATM System", "description": "Create a simple ATM system in Java."}
        ],
        "intermediate": [
            {"name": "Student Management System", "description": "Create a student management system using OOP."},
            {"name": "Bank Account System", "description": "Create a bank account system in Java."},
            {"name": "To-do List", "description": "Build a simple to-do list app."},
            {"name": "Library System", "description": "Create a library management system in Java."},
            {"name": "Address Book", "description": "Build a system to store and search contacts."}
        ],
        "advanced": [
            {"name": "Java GUI App", "description": "Create a desktop app using Java Swing."},
            {"name": "Multithreading", "description": "Implement multithreading in Java."},
            {"name": "Online Shopping System", "description": "Build a basic e-commerce system."},
            {"name": "Chat Application", "description": "Create a real-time chat application."},
            {"name": "Database CRUD Operations", "description": "Create a CRUD application using Java and a database."}
        ]
    },
    "javascript": {
        "beginner": [
            {"name": "Interactive Website", "description": "Create a simple interactive webpage."},
            {"name": "To-do List", "description": "Build a to-do list app with JavaScript."},
            {"name": "Image Slider", "description": "Create a simple image slider using JavaScript."},
            {"name": "Simple Form Validation", "description": "Build a form with client-side validation."},
            {"name": "Countdown Timer", "description": "Create a countdown timer that counts down to a specific date."}
        ],
        "intermediate": [
            {"name": "Weather App", "description": "Create a weather app with JavaScript and APIs."},
            {"name": "Chat App", "description": "Build a simple real-time chat app using JavaScript."},
            {"name": "To-do List with Local Storage", "description": "Create a to-do list app that saves data in local storage."},
            {"name": "Quiz App", "description": "Build a quiz application with multiple choice questions."},
            {"name": "Recipe App", "description": "Create an app that shows recipes based on ingredients."}
        ],
        "advanced": [
            {"name": "React App", "description": "Build a single-page application with React."},
            {"name": "Node.js API", "description": "Create a RESTful API using Node.js."},
            {"name": "Real-time Chat with WebSockets", "description": "Build a real-time chat application using WebSockets."},
            {"name": "E-commerce Website", "description": "Create a complete e-commerce site using React and Redux."},
            {"name": "Authentication System", "description": "Build a user authentication system with JWT."}
        ]
    }
}

@app.route('/project/<course_name>')
def project(course_name):
    # Your function logic here
    return render_template('project.html', course_name=course_name)


@app.route('/project/<language>/<level>', methods=['GET'])
def project_page(language, level):
    # Check if the requested language exists in the projects dictionary
    print(language)
    print(level)
    if language not in projects:
        return jsonify({"error": "Language not found"}), 404

    # Check if the requested level exists for the given language
    if level not in projects[language]:
        return jsonify({"error": "Level not found for the given language"}), 404

    # Get the list of projects for the given language and level
    project_list = projects[language][level]

    # Render the projects for the given language and level
    return render_template('language_projects.html', language=language, level=level, projects=project_list)

@app.route('/games')
def games_page():
    check_login()
    cur = mysql.connection.cursor()
    username = session.get('username')
    cur.execute("SELECT username, email, created_at FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    now = datetime.now()
    user_dict = {'username': user[0], 'email': user[1], 'created_at': user[2]}
    # Check if a timer start time exists in the session
    if 'timer_start' not in session:
        session['timer_start'] = now.isoformat()

    # Convert the session timer start time to datetime
    timer_start = datetime.fromisoformat(session['timer_start'])
    elapsed = (now - timer_start).total_seconds()

    if elapsed > TIMER_DURATION:
        # Timer expired; start cooldown
        if 'cooldown_start' not in session:
            session['cooldown_start'] = now.isoformat()

        cooldown_start = datetime.fromisoformat(session['cooldown_start'])
        cooldown_elapsed = (now - cooldown_start).total_seconds()

        if cooldown_elapsed >= COOLDOWN_DURATION:
            # Cooldown expired; reset the session and allow gameplay
            session.pop('cooldown_start', None)
            session.pop('timer_start', None)
            return render_template('games.html',user=user_dict)  # Allow access to games.html
        else:
            remaining_cooldown = COOLDOWN_DURATION - cooldown_elapsed
            minutes, seconds = divmod(remaining_cooldown, 60)
            remaining_time = f"{int(minutes):02}:{int(seconds):02}"
            return render_template(
                'cooldown.html',
                remaining_time=remaining_time
            )
    else:
        remaining_timer = TIMER_DURATION - elapsed
        minutes, seconds = divmod(remaining_timer, 60)
        flash(f"You have {int(minutes)} minutes and {int(seconds)} seconds left before cooldown starts.")
        return render_template('games.html', user=user_dict)  # Allow access to games during active timer


@app.route('/timer_status')
def timer_status():
    now = datetime.now()

    if 'timer_start' in session:
        timer_start = datetime.fromisoformat(session['timer_start'])
        elapsed = (now - timer_start).total_seconds()
        remaining = max(0, TIMER_DURATION - elapsed)
        return jsonify({'remaining': remaining})

    return jsonify({'remaining': 0})

@app.route('/games/Tic-Tac-Toe')
def tic_tac_toe():
    return render_template('tic_tac_toe.html')

@app.route('/games/Rock-Paper-Scissors')
def rock_paper_scissors():
    return render_template('rock_paper_scissors.html')

@app.route('/games/connect-four')
def connect_four():
    return render_template('connect_four.html')

@app.route('/games/snake-game')
def snake_game():
    return render_template('snake_game.html')

@app.route('/games/brick-game')
def brick_game():
    return render_template('brick.html')

@app.route('/games/memory-game')
def memory_game():
    return render_template('memory_game.html')


if __name__ == '__main__':
    try:
        app.run(debug=True)
    except KeyboardInterrupt:
        print("Shutting down server...")
        os.kill(os.getpid(), signal.SIGINT)
