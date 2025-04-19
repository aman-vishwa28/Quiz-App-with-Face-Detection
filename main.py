import customtkinter as ctk
from tkinter import messagebox
import mysql.connector
from mysql.connector import Error
import cv2
from PIL import Image
from threading import Thread
import time

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def create_mcq_app(root):
    # Database connection
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Aman@2001",
            database="online_exam"
        )
        cursor = conn.cursor(dictionary=True)
    except Error as e:
        messagebox.showerror("Database Error", f"Could not connect to database:\n{e}")
        root.destroy()
        return None
    
    student_name = ""

    # Load questions from database
    cursor.execute("SELECT * FROM questions")
    questions = cursor.fetchall()

    if not questions:
        messagebox.showinfo("No Questions", "No questions found in the database.")
        root.destroy()
        return None

    # State variables
    q_index = 0
    selected_option_index = ctk.IntVar(value=-1)
    user_answers = [None] * len(questions)
    time_left = 300  # 5 minutes
    timer_running = True
    penalty_count = 0
    max_penalties = 3

    # Video capture
    video_capture = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # UI Elements
    start_frame = None
    header = None
    timer_label = None
    question_label = None
    options_frame = None
    option_buttons = []
    nav_frame = None
    prev_button = None
    next_button = None
    submit_button = None
    camera_label = None

    def load_questions():
        nonlocal questions
        cursor.execute("SELECT * FROM questions")
        questions = cursor.fetchall()

    def build_start_screen():
        nonlocal start_frame
        start_frame = ctk.CTkFrame(root)
        start_frame.pack(expand=True, fill="both")


        name_label = ctk.CTkLabel(start_frame, text="Enter Your Name:", font=ctk.CTkFont(size=14))
        name_label.pack(pady=(20, 5))
        
        global name_entry  # Make it accessible to other functions
        name_entry = ctk.CTkEntry(start_frame, width=300, font=ctk.CTkFont(size=14))
        name_entry.pack(pady=5)

        ctk.CTkLabel(start_frame, text="Welcome to the MCQ Quiz", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)

        instructions = (
            "Instructions:\n"
            "- Total 10 Question\n"
            "- You have 5 minutes to complete the quiz.\n"
            "- Each question has 4 options; only one is correct.\n"
            "- Click 'Next' or 'Previous' to navigate between questions.\n"
            "- A live camera feed monitors face presence.\n"
            "- Penalties will be given for no face or multiple faces.\n"
            "- 4 penalties will auto-submit your test.\n"
        )
        ctk.CTkLabel(start_frame, text=instructions, font=ctk.CTkFont(size=14), justify="left").pack(pady=10)

        ctk.CTkButton(start_frame, text="Start Test", font=ctk.CTkFont(size=16), command=start_test).pack(pady=20)

    def start_test():
        nonlocal start_frame, student_name
        student_name = name_entry.get().strip()

        if not student_name:
            messagebox.showwarning("Name Required", "Please enter your name to start the test.")
            return
        
        start_frame.destroy()
        build_quiz_ui()
        show_question()
        update_timer()
        start_camera()

    def build_quiz_ui():
        nonlocal header, timer_label, question_label, options_frame
        nonlocal option_buttons, nav_frame, prev_button, next_button
        nonlocal submit_button, camera_label, student_name

        name_display = ctk.CTkLabel(root, text=f"Student: {student_name}", font=ctk.CTkFont(size=14))
        name_display.pack(pady=(10, 0))

        header = ctk.CTkLabel(root, text="Multiple Choice Quiz", font=ctk.CTkFont(size=22, weight="bold"))
        header.pack(pady=10)

        timer_label = ctk.CTkLabel(root, text="Time Left: 05:00", font=ctk.CTkFont(size=16), text_color="red")
        timer_label.pack()

        question_label = ctk.CTkLabel(root, text="", wraplength=750, font=ctk.CTkFont(size=16))
        question_label.pack(pady=20)

        options_frame = ctk.CTkFrame(root,fg_color="transparent")
        options_frame.pack(pady=10)

        option_buttons = []
        for i in range(4):
            rb = ctk.CTkRadioButton(
                options_frame,
                text="",
                variable=selected_option_index,
                value=i,
                font=ctk.CTkFont(size=14)
            )
            rb.pack(anchor="w", pady=5)
            option_buttons.append(rb)

        nav_frame = ctk.CTkFrame(root, fg_color="transparent")
        nav_frame.pack(pady=20)

        prev_button = ctk.CTkButton(nav_frame, text="Previous", command=prev_question, width=120)
        prev_button.grid(row=0, column=0, padx=15)

        next_button = ctk.CTkButton(nav_frame, text="Next", command=next_question, width=120)
        next_button.grid(row=0, column=1, padx=15)

        submit_button = ctk.CTkButton(root, text="Submit Test", command=ask_to_submit, fg_color="#e74c3c", hover_color="#c0392b")
        submit_button.pack(pady=10)

        camera_label = ctk.CTkLabel(root, text="")
        camera_label.place(relx=1.0, x=-20, y=20, anchor="ne")

    def start_camera():
        def camera_loop():
            nonlocal penalty_count
            violation_start_time = None

            while timer_running:
                ret, frame = video_capture.read()
                if not ret:
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

                current_time = time.time()
                if len(faces) != 1:
                    if violation_start_time is None:
                        violation_start_time = current_time
                    elif current_time - violation_start_time >= 5:
                        penalty_count += 1
                        root.after(0, lambda: messagebox.showwarning(
                            "Penalty!", f"Face detection warning!\nDetected {len(faces)} faces.\nPenalty: {penalty_count}"
                        ))
                        violation_start_time = None

                        if penalty_count > max_penalties:
                            root.after(0, lambda: messagebox.showinfo("Auto Submit", "More than 3 penalties.\nTest will now auto-submit."))
                            root.after(0, submit_test)
                            break
                else:
                    violation_start_time = None

                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(img_rgb).resize((160, 120))
                ctk_img = ctk.CTkImage(light_image=img_pil, size=(160, 120))

                root.after(0, lambda img=ctk_img: camera_label.configure(image=img))
                camera_label.image = ctk_img

        Thread(target=camera_loop, daemon=True).start()

    def show_question():
        nonlocal q_index
        question = questions[q_index]
        question_label.configure(text=f"Q{q_index + 1}: {question['question']}")

        options = [question['option1'], question['option2'], 
                  question['option3'], question['option4']]
        for i in range(4):
            option_buttons[i].configure(text=f"{chr(65+i)}. {options[i]}")

        if user_answers[q_index] is None:
            selected_option_index.set(-1)
        else:
            selected = options.index(user_answers[q_index])
            selected_option_index.set(selected)

    def next_question():
        nonlocal q_index
        save_answer()
        if q_index < len(questions) - 1:
            q_index += 1
            show_question()
        else:
            ask_to_submit()

    def prev_question():
        nonlocal q_index
        save_answer()
        if q_index > 0:
            q_index -= 1
            show_question()

    def save_answer():
        nonlocal q_index
        idx = selected_option_index.get()
        if idx >= 0:
            options = [questions[q_index]['option1'], questions[q_index]['option2'],
                      questions[q_index]['option3'], questions[q_index]['option4']]
            user_answers[q_index] = options[idx]

    def ask_to_submit():
        save_answer()
        result = messagebox.askyesno("Submit Test", "Are you sure you want to submit the test?")
        if result:
            nonlocal timer_running
            timer_running = False
            submit_test()

    def submit_test():
        nonlocal timer_running, student_name
        timer_running = False
        correct = 0
        total = len(questions)

        for i in range(total):
            if user_answers[i] == questions[i]['correct_option']:
                correct += 1

        incorrect = total - correct
        percent = round((correct / total) * 100, 2)

        clear_quiz_ui()

        result_frame = ctk.CTkFrame(root)
        result_frame.pack(pady=10, fill="both", expand=True)

        ctk.CTkLabel(result_frame, text=f"Student: {student_name}", font=ctk.CTkFont(size=14)).pack(pady=(10, 0))

        ctk.CTkLabel(result_frame, text="✅ Test Submitted!", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        ctk.CTkLabel(result_frame, text=f"Total Questions: {total}", font=ctk.CTkFont(size=14)).pack()
        ctk.CTkLabel(result_frame, text=f"Correct: {correct}", text_color="green", font=ctk.CTkFont(size=14)).pack()
        ctk.CTkLabel(result_frame, text=f"Incorrect: {incorrect}", text_color="red", font=ctk.CTkFont(size=14)).pack()
        ctk.CTkLabel(result_frame, text=f"Score: {percent}%", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        try:
            cursor.execute(
                "INSERT INTO results (student_name, total_questions, correct_answers, incorrect_answers, score_percent) VALUES (%s, %s, %s, %s, %s)",
                (student_name,total, correct, incorrect, percent)
            )
            conn.commit()
        except Error as e:
            messagebox.showwarning("Database Warning", f"Could not save result to database:\n{e}")

        review_frame = ctk.CTkScrollableFrame(root, height=300)
        review_frame.pack(padx=20, pady=10, fill="both", expand=True)

        for i, q in enumerate(questions):
            your_answer = user_answers[i] or "No Answer"
            correct_answer = q['correct_option']
            is_correct = (your_answer == correct_answer)

            ctk.CTkLabel(review_frame, text=f"Q{i+1}: {q['question']}", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(5, 0))
            ctk.CTkLabel(review_frame, text=f"Your Answer: {your_answer}", text_color="green" if is_correct else "red").pack(anchor="w")
            ctk.CTkLabel(review_frame, text=f"Correct Answer: {correct_answer}").pack(anchor="w", pady=(0, 5))

        ctk.CTkButton(root, text="Close", command=root.destroy).pack(pady=15)

    def clear_quiz_ui():
        header.pack_forget()
        timer_label.pack_forget()
        question_label.pack_forget()
        options_frame.pack_forget()
        nav_frame.pack_forget()
        submit_button.pack_forget()
        camera_label.place_forget()

    def update_timer():
        nonlocal time_left, timer_running
        if timer_running:
            if time_left > 0:
                mins, secs = divmod(time_left, 60)
                timer_label.configure(text=f"Time Left: {mins:02d}:{secs:02d}")
                time_left -= 1
                root.after(1000, update_timer)
            else:
                messagebox.showinfo("Time Up", "⏰ Time is up! Submitting the test.")
                submit_test()

    # Initialize the app
    build_start_screen()

    # Return cleanup function
    def cleanup():
        nonlocal timer_running, video_capture, conn
        timer_running = False
        if video_capture.isOpened():
            video_capture.release()
        if conn.is_connected():
            conn.close()

    return cleanup

if __name__ == "__main__":
    root = ctk.CTk()
    root.title("MCQ Test")
    root.geometry("500x600")
    cleanup_func = create_mcq_app(root)
    
    
    def on_close():
        if cleanup_func:
            cleanup_func()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()