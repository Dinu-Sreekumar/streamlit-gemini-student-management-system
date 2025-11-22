import streamlit as st
import sqlite3
import pandas as pd
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini AI
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.warning("⚠️ GEMINI_API_KEY not found in .env file. AI features will not work.")

# Database Helper Functions
def init_db():
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            student_id TEXT UNIQUE NOT NULL,
            course TEXT,
            gpa REAL,
            email TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_student(name, student_id, course, gpa, email):
    try:
        conn = sqlite3.connect('students.db')
        c = conn.cursor()
        c.execute('INSERT INTO students (name, student_id, course, gpa, email) VALUES (?, ?, ?, ?, ?)',
                  (name, student_id, course, gpa, email))
        conn.commit()
        conn.close()
        return True, "Student added successfully!"
    except sqlite3.IntegrityError:
        return False, "Error: Student ID already exists."
    except Exception as e:
        return False, f"Error: {e}"

def get_all_students():
    conn = sqlite3.connect('students.db')
    df = pd.read_sql_query("SELECT * FROM students", conn)
    conn.close()
    return df

def update_student(original_student_id, name, student_id, course, gpa, email):
    try:
        conn = sqlite3.connect('students.db')
        c = conn.cursor()
        c.execute('''
            UPDATE students 
            SET name=?, student_id=?, course=?, gpa=?, email=?
            WHERE student_id=?
        ''', (name, student_id, course, gpa, email, original_student_id))
        conn.commit()
        conn.close()
        return True, "Student updated successfully!"
    except Exception as e:
        return False, f"Error: {e}"

def delete_student(student_id):
    try:
        conn = sqlite3.connect('students.db')
        c = conn.cursor()
        c.execute('DELETE FROM students WHERE student_id=?', (student_id,))
        conn.commit()
        conn.close()
        return True, "Student deleted successfully!"
    except Exception as e:
        return False, f"Error: {e}"

# AI Helper Functions
def get_gemini_response(prompt):
    if not api_key:
        return "⚠️ API Key missing. Please configure .env file."
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error communicating with Gemini: {e}"

def get_student_context():
    df = get_all_students()
    if df.empty:
        return "No student data available."
    return df.to_string(index=False)

# Page Configuration
st.set_page_config(page_title="Student Management System", page_icon="🎓", layout="wide")

# Initialize Database
init_db()

# Sidebar
st.sidebar.title("🎓 Student System")
st.sidebar.markdown("Manage students and get AI insights.")

# Main Layout
tab1, tab2 = st.tabs(["📋 Manage Students", "🤖 AI Advisor"])

# Tab 1: Student Management
with tab1:
    st.header("Student Management")
    
    # Add Student Section
    with st.expander("➕ Add New Student", expanded=False):
        with st.form("add_student_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Full Name")
                new_id = st.text_input("Student ID")
                new_email = st.text_input("Email")
            with col2:
                new_course = st.selectbox("Course", ["Computer Science", "Engineering", "Business", "Arts", "Science", "Other"])
                new_gpa = st.number_input("GPA", min_value=0.0, max_value=4.0, step=0.1)
            
            submitted = st.form_submit_button("Add Student")
            if submitted:
                if new_name and new_id:
                    success, msg = add_student(new_name, new_id, new_course, new_gpa, new_email)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Name and Student ID are required.")

    # JSON Import Section
    with st.expander("📂 Import Students from JSON", expanded=False):
        uploaded_file = st.file_uploader("Upload JSON file", type=['json'])
        if uploaded_file is not None:
            try:
                import json
                data = json.load(uploaded_file)
                if isinstance(data, list):
                    success_count = 0
                    error_count = 0
                    errors = []
                    
                    if st.button("Import Data"):
                        for student in data:
                            # Basic validation
                            if all(k in student for k in ("name", "student_id")):
                                s_name = student.get("name")
                                s_id = student.get("student_id")
                                s_course = student.get("course", "Other")
                                s_gpa = student.get("gpa", 0.0)
                                s_email = student.get("email", "")
                                
                                success, msg = add_student(s_name, s_id, s_course, s_gpa, s_email)
                                if success:
                                    success_count += 1
                                else:
                                    error_count += 1
                                    errors.append(f"{s_name} ({s_id}): {msg}")
                            else:
                                error_count += 1
                                errors.append(f"Skipped invalid record: {student}")
                        
                        if success_count > 0:
                            st.success(f"Successfully imported {success_count} students.")
                        if error_count > 0:
                            st.warning(f"Failed to import {error_count} students.")
                            with st.expander("View Errors"):
                                for err in errors:
                                    st.write(err)
                        if success_count > 0:
                            st.rerun()
                else:
                    st.error("Invalid JSON format. Expected a list of student objects.")
            except Exception as e:
                st.error(f"Error parsing JSON: {e}")

    # Export Section
    st.markdown("### 📤 Export Data")
    col_exp1, col_exp2 = st.columns(2)
    df = get_all_students()
    if not df.empty:
        with col_exp1:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name='students.csv',
                mime='text/csv',
            )
        with col_exp2:
            json_str = df.to_json(orient='records', indent=4)
            st.download_button(
                label="Download as JSON",
                data=json_str,
                file_name='students.json',
                mime='application/json',
            )

    # View/Edit/Delete Section
    st.subheader("Student Records")
    
    # Search/Filter
    search_term = st.text_input("🔍 Search by Name or ID", "")
    
    df = get_all_students()
    
    if not df.empty:
        if search_term:
            df = df[df['name'].str.contains(search_term, case=False) | df['student_id'].str.contains(search_term, case=False)]
        
        # Display Data
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Edit/Delete Actions
        st.markdown("### Actions")
        col_action1, col_action2 = st.columns(2)
        
        with col_action1:
            st.markdown("#### ✏️ Update Student")
            student_to_edit = st.selectbox("Select Student to Edit", df['student_id'].tolist(), key="edit_select")
            if student_to_edit:
                student_data = df[df['student_id'] == student_to_edit].iloc[0]
                with st.form("edit_student_form"):
                    edit_name = st.text_input("Name", value=student_data['name'])
                    edit_id = st.text_input("Student ID", value=student_data['student_id'])
                    edit_course = st.selectbox("Course", ["Computer Science", "Engineering", "Business", "Arts", "Science", "Other"], index=["Computer Science", "Engineering", "Business", "Arts", "Science", "Other"].index(student_data['course']) if student_data['course'] in ["Computer Science", "Engineering", "Business", "Arts", "Science", "Other"] else 0)
                    edit_gpa = st.number_input("GPA", min_value=0.0, max_value=4.0, step=0.1, value=float(student_data['gpa']))
                    edit_email = st.text_input("Email", value=student_data['email'])
                    
                    if st.form_submit_button("Update Student"):
                        success, msg = update_student(student_to_edit, edit_name, edit_id, edit_course, edit_gpa, edit_email)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

        with col_action2:
            st.markdown("#### 🗑️ Delete Student")
            student_to_delete = st.selectbox("Select Student to Delete", df['student_id'].tolist(), key="delete_select")
            if st.button("Delete Student", type="primary"):
                success, msg = delete_student(student_to_delete)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        
        # Clear All Data
        st.divider()
        with st.expander("⚠️ Danger Zone"):
            st.markdown("### Clear All Data")
            st.warning("This action cannot be undone.")
            if st.button("Clear All Student Data", type="primary"):
                st.session_state.confirm_clear = True
            
            if st.session_state.get("confirm_clear"):
                st.error("Are you sure you want to delete ALL students?")
                col_confirm1, col_confirm2 = st.columns(2)
                with col_confirm1:
                    if st.button("Yes, Delete Everything"):
                        try:
                            conn = sqlite3.connect('students.db')
                            c = conn.cursor()
                            c.execute('DELETE FROM students')
                            conn.commit()
                            conn.close()
                            st.success("All data deleted successfully.")
                            st.session_state.confirm_clear = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                with col_confirm2:
                    if st.button("Cancel"):
                        st.session_state.confirm_clear = False
                        st.rerun()
    else:
        st.info("No students found. Add some students to get started.")

# Tab 2: AI Advisor
with tab2:
    st.header("🤖 AI Advisor")
    
    # Chat Interface
    st.subheader("💬 Ask about your data")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question (e.g., 'Who has the highest GPA?')"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                context = get_student_context()
                full_prompt = f"""
                You are a helpful assistant for a Student Management System.
                Here is the current student data in CSV format:
                
                {context}
                
                User Question: {prompt}
                
                Answer based on the data provided. If the data is empty, say so.
                Keep the answer concise and professional.
                """
                response = get_gemini_response(full_prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

    st.divider()
    
    # Performance Summary
    st.subheader("📝 Performance Summary Generator")
    
    df = get_all_students()
    if not df.empty:
        selected_student_id = st.selectbox("Select Student for Review", df['student_id'].tolist(), key="summary_select")
        if st.button("Generate Performance Review"):
            student_data = df[df['student_id'] == selected_student_id].iloc[0]
            with st.spinner(f"Generating review for {student_data['name']}..."):
                review_prompt = f"""
                Write a personalized performance review and study plan for the following student:
                Name: {student_data['name']}
                Course: {student_data['course']}
                GPA: {student_data['gpa']}
                
                The review should be encouraging but honest. Suggest study tips based on their GPA.
                """
                review = get_gemini_response(review_prompt)
                st.markdown("### Performance Review")
                st.markdown(review)
    else:
        st.info("Add students to generate performance reviews.")
