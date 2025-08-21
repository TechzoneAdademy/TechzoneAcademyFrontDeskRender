from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash, Response, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
import os
from datetime import datetime, timedelta
import hashlib
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .firebase_config import firebase_config
import random
import re

techzone_app = Flask(__name__)
techzone_app.secret_key = "techzone_secret"

# Custom template filter for date formatting
@techzone_app.template_filter('format_date')
def format_date(date_str):
    """Format date from YYYY-MM-DD to DD-MMM-YYYY"""
    if not date_str:
        return "Unknown"
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d-%b-%Y').upper()
    except:
        return date_str

# ---------- File Paths ----------
TRAINER_UPLOADS = "static/uploads"
os.makedirs(TRAINER_UPLOADS, exist_ok=True)

# ---------- Firebase Collections ----------
if firebase_config.firebase_available:
    students_collection = firebase_config.get_collection('students')
    batches_collection = firebase_config.get_collection('batches')
    trainer_files_collection = firebase_config.get_collection('trainer_files')
    course_tracking_collection = firebase_config.get_collection('course_tracking')
    role_credentials_collection = firebase_config.get_collection('role_credentials')
    student_feedback_collection = firebase_config.get_collection('student_feedback')
    messages_collection = firebase_config.get_collection('messages')  # For trainer-student messages
    storage_bucket = firebase_config.storage_bucket
    print("Firebase collections initialized!")
else:
    print("Firebase not available!")
    students_collection = None
    batches_collection = None
    trainer_files_collection = None
    course_tracking_collection = None
    role_credentials_collection = None
    student_feedback_collection = None
    messages_collection = None
    storage_bucket = None

FIREBASE_AVAILABLE = firebase_config.firebase_available

# ---------- Utility Functions ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---------- File Download Route ----------
@techzone_app.route("/download/<filename>")
def download_file(filename):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    
    print(f"[DEBUG] Download request for file: {filename} by user: {session.get('username')} with role: {session.get('role')}")

    # For student users, check if they can access this file
    if session.get("role") == "Student":
        student_batch_id = session.get("student_batch")  # This should be the batch _id
        print(f"[DEBUG] Student batch ID from session: {student_batch_id}")
        
        if student_batch_id and FIREBASE_AVAILABLE and trainer_files_collection is not None:
            try:
                # Check if file belongs to student's batch
                file_record = None
                docs = trainer_files_collection.where('filename', '==', filename).stream()
                for doc in docs:
                    file_record = doc.to_dict()
                    break
                
                if file_record:
                    file_batch_id = file_record.get('batch_id')
                    print(f"[DEBUG] File batch_id: {file_batch_id}, Student batch_id: {student_batch_id}")
                    
                    # Convert both to strings for comparison
                    if str(file_batch_id) != str(student_batch_id):
                        print(f"[DEBUG] Access denied: File batch {file_batch_id} != Student batch {student_batch_id}")
                        flash("You can only download files from your enrolled batch!", "danger")
                        return redirect(url_for("dashboard"))
                    else:
                        print(f"[DEBUG] Access granted: File belongs to student's batch")
                else:
                    print(f"[DEBUG] File record not found for filename: {filename}")
                    flash("File not found in database!", "danger")
                    return redirect(url_for("dashboard"))
            except Exception as e:
                print(f"Error checking file access: {e}")
                flash("Error checking file access!", "danger")
                return redirect(url_for("dashboard"))

    # Try to get file from Firebase Storage or Firestore
    if FIREBASE_AVAILABLE and trainer_files_collection is not None:
        try:
            file_record = None
            docs = trainer_files_collection.where('filename', '==', filename).stream()
            for doc in docs:
                file_record = doc.to_dict()
                break
            
            if file_record:
                # First try to download from Firebase Storage if available
                if file_record.get('uploaded_to_storage') and storage_bucket:
                    try:
                        storage_path = file_record.get('storage_path', f"trainer_uploads/{filename}")
                        blob = storage_bucket.blob(storage_path)
                        if blob.exists():
                            file_data = blob.download_as_bytes()
                            content_type = file_record.get('content_type', 'application/octet-stream')
                            original_filename = file_record.get('original_filename', filename)
                            response = Response(file_data, content_type=content_type)
                            response.headers['Content-Disposition'] = f'attachment; filename="{original_filename}"'
                            return response
                    except Exception as storage_e:
                        print(f"Error downloading from Firebase Storage: {storage_e}")
                
                # Fallback to base64 data if available
                if file_record.get("file_data_base64"):
                    file_data = base64.b64decode(file_record["file_data_base64"])
                    file_ext = filename.split('.')[-1].lower()
                    content_type = file_record.get('content_type', 'application/octet-stream')
                    if not content_type or content_type == 'application/octet-stream':
                        if file_ext == 'pdf':
                            content_type = 'application/pdf'
                        elif file_ext in ['jpg', 'jpeg']:
                            content_type = 'image/jpeg'
                        elif file_ext == 'png':
                            content_type = 'image/png'
                        elif file_ext in ['doc', 'docx']:
                            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                        elif file_ext in ['xls', 'xlsx']:
                            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        elif file_ext == 'mp4':
                            content_type = 'video/mp4'
                    
                    original_filename = file_record.get('original_filename', filename)
                    response = Response(file_data, content_type=content_type)
                    response.headers['Content-Disposition'] = f'attachment; filename="{original_filename}"'
                    return response
        except Exception as e:
            print(f"Error downloading from Firebase: {e}")

    # Fallback to file system
    file_path = os.path.join(TRAINER_UPLOADS, filename)
    if os.path.exists(file_path):
        try:
            return send_file(file_path, as_attachment=True)
        except Exception as e:
            print(f"Error sending file from filesystem: {e}")
            try:
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                response = Response(file_data, content_type='application/octet-stream')
                response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            except Exception as e2:
                print(f"Error reading file manually: {e2}")
    flash("File not found!", "danger")
    return redirect(url_for("dashboard"))

# ---------- File Delete Route ----------
@techzone_app.route("/delete-file/<filename>", methods=["POST"])
def delete_file(filename):
    if not session.get("logged_in") or session.get("role") != "Trainer":
        return redirect(url_for("login"))
    username = session.get("username")
    # Check if the file belongs to the current trainer
    if FIREBASE_AVAILABLE and trainer_files_collection is not None:
        try:
            file_record = None
            docs = trainer_files_collection.where('filename', '==', filename).stream()
            for doc in docs:
                file_record = doc.to_dict()
                break
            if file_record and file_record.get("uploaded_by") != username:
                flash("You can only delete files you uploaded!", "danger")
                return redirect(url_for("dashboard"))
        except Exception as e:
            print(f"Error checking file ownership: {e}")
    if not filename.startswith(username):
        flash("You can only delete files you uploaded!", "danger")
        return redirect(url_for("dashboard"))
    if delete_trainer_file(filename, username):
        flash("File deleted successfully!", "warning")
    else:
        flash("Error deleting file.", "danger")
    return redirect(url_for("dashboard"))

# ---------- Trainer File Management Functions ----------
def get_trainer_files_by_user(username):
    """Get all files uploaded by a specific trainer"""
    if not FIREBASE_AVAILABLE or trainer_files_collection is None:
        return []
    try:
        docs = trainer_files_collection.where(filter=('uploaded_by', '==', username)).stream()
        files = []
        for doc in docs:
            file_data = doc.to_dict()
            file_data['_id'] = doc.id
            files.append(file_data)
        return files
    except Exception as e:
        print(f"Error getting trainer files: {e}")
        return []

def get_trainer_files_by_batch(batch_id):
    """Get all trainer files for a specific batch - with cleanup of orphaned records"""
    if not FIREBASE_AVAILABLE or trainer_files_collection is None:
        return []
    try:
        # Convert batch_id to string to match Firestore storage format
        batch_id_str = str(batch_id)
        print(f"[DEBUG] Looking for files with batch_id: '{batch_id_str}'")
        
        docs = trainer_files_collection.where('batch_id', '==', batch_id_str).stream()
        files = []
        orphaned_docs = []
        
        for doc in docs:
            file_data = doc.to_dict()
            file_data['_id'] = doc.id
            filename = file_data.get('filename')
            
            # Check if file actually exists in Firebase Storage
            file_exists_in_storage = False
            if file_data.get('uploaded_to_storage') and storage_bucket:
                try:
                    storage_path = file_data.get('storage_path', f"trainer_uploads/{filename}")
                    blob = storage_bucket.blob(storage_path)
                    if blob.exists():
                        file_exists_in_storage = True
                    else:
                        print(f"[DEBUG] File {filename} missing from Storage, checking for base64 backup")
                        # If no base64 backup either, mark as orphaned
                        if not file_data.get('file_data_base64'):
                            print(f"[DEBUG] File {filename} has no base64 backup - marking as orphaned")
                            orphaned_docs.append(doc)
                            continue
                except Exception as e:
                    print(f"[DEBUG] Error checking storage for {filename}: {e}")
                    # If storage check fails but has base64, keep it
                    if not file_data.get('file_data_base64'):
                        orphaned_docs.append(doc)
                        continue
            
            # Keep files that either exist in storage OR have base64 backup
            if file_exists_in_storage or file_data.get('file_data_base64'):
                files.append(file_data)
                print(f"[DEBUG] Found valid file: {filename} for batch {file_data.get('batch_id')}")
            else:
                print(f"[DEBUG] File {filename} has no valid source - marking as orphaned")
                orphaned_docs.append(doc)
        
        # Clean up orphaned records
        if orphaned_docs:
            print(f"[DEBUG] Cleaning up {len(orphaned_docs)} orphaned file records")
            for doc in orphaned_docs:
                try:
                    print(f"[DEBUG] Deleting orphaned record: {doc.to_dict().get('filename')}")
                    doc.reference.delete()
                except Exception as e:
                    print(f"[DEBUG] Error deleting orphaned record: {e}")
        
        print(f"[DEBUG] Total valid files found for batch {batch_id_str}: {len(files)}")
        return files
    except Exception as e:
        print(f"Error getting trainer files by batch: {e}")
        return []

def delete_trainer_file(filename, uploaded_by):
    """Delete trainer file from both Firestore and Firebase Storage"""
    if not FIREBASE_AVAILABLE or trainer_files_collection is None:
        return False
    try:
        # Delete from Firestore
        docs = trainer_files_collection.where('filename', '==', filename).where('uploaded_by', '==', uploaded_by).stream()
        for doc in docs:
            doc.reference.delete()
        
        # Delete from Firebase Storage
        if storage_bucket:
            blob = storage_bucket.blob(f"trainer_uploads/{filename}")
            if blob.exists():
                blob.delete()
        
        return True
    except Exception as e:
        print(f"Error deleting trainer file: {e}")
        return False

# ---------- File Cleanup Utilities ----------
@techzone_app.route("/admin/cleanup-files", methods=["GET", "POST"])
def cleanup_files():
    """Admin utility to clean up orphaned file records"""
    if not session.get("logged_in") or session.get("role") not in ["Admin", "Super Admin"]:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        cleaned_count = cleanup_orphaned_file_records()
        if cleaned_count >= 0:
            flash(f"Cleanup completed! Removed {cleaned_count} orphaned file records.", "success")
        else:
            flash("Error during cleanup process!", "danger")
        return redirect(url_for("cleanup_files"))
    
    # GET request - show cleanup information
    orphaned_files = get_orphaned_file_count()
    return render_template("cleanup_files.html", orphaned_count=orphaned_files)

def cleanup_orphaned_file_records():
    """Clean up all orphaned file records across all collections"""
    if not FIREBASE_AVAILABLE or trainer_files_collection is None:
        return -1
    
    try:
        print("[CLEANUP] Starting cleanup of orphaned file records...")
        
        docs = trainer_files_collection.stream()
        orphaned_docs = []
        total_checked = 0
        
        for doc in docs:
            total_checked += 1
            file_data = doc.to_dict()
            filename = file_data.get('filename')
            
            # Check if file actually exists in Firebase Storage or has base64 backup
            file_exists_in_storage = False
            has_base64_backup = bool(file_data.get('file_data_base64'))
            
            if file_data.get('uploaded_to_storage') and storage_bucket:
                try:
                    storage_path = file_data.get('storage_path', f"trainer_uploads/{filename}")
                    blob = storage_bucket.blob(storage_path)
                    if blob.exists():
                        file_exists_in_storage = True
                    else:
                        print(f"[CLEANUP] File {filename} missing from Storage")
                except Exception as e:
                    print(f"[CLEANUP] Error checking storage for {filename}: {e}")
            
            # Mark as orphaned if no valid source exists
            if not file_exists_in_storage and not has_base64_backup:
                print(f"[CLEANUP] File {filename} has no valid source - marking as orphaned")
                orphaned_docs.append(doc)
        
        # Clean up orphaned records
        cleaned_count = 0
        if orphaned_docs:
            print(f"[CLEANUP] Cleaning up {len(orphaned_docs)} orphaned file records")
            for doc in orphaned_docs:
                try:
                    orphaned_filename = doc.to_dict().get('filename')
                    print(f"[CLEANUP] Deleting orphaned record: {orphaned_filename}")
                    doc.reference.delete()
                    cleaned_count += 1
                except Exception as e:
                    print(f"[CLEANUP] Error deleting orphaned record: {e}")
        
        print(f"[CLEANUP] Cleanup completed. Checked {total_checked} files, removed {cleaned_count} orphaned records")
        return cleaned_count
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return -1

def get_orphaned_file_count():
    """Get count of orphaned file records"""
    if not FIREBASE_AVAILABLE or trainer_files_collection is None:
        return 0
    
    try:
        docs = trainer_files_collection.stream()
        orphaned_count = 0
        
        for doc in docs:
            file_data = doc.to_dict()
            filename = file_data.get('filename')
            
            # Check if file actually exists in Firebase Storage or has base64 backup
            file_exists_in_storage = False
            has_base64_backup = bool(file_data.get('file_data_base64'))
            
            if file_data.get('uploaded_to_storage') and storage_bucket:
                try:
                    storage_path = file_data.get('storage_path', f"trainer_uploads/{filename}")
                    blob = storage_bucket.blob(storage_path)
                    if blob.exists():
                        file_exists_in_storage = True
                except Exception as e:
                    pass  # Ignore errors during count
            
            # Count as orphaned if no valid source exists
            if not file_exists_in_storage and not has_base64_backup:
                orphaned_count += 1
        
        return orphaned_count
    except Exception as e:
        print(f"Error counting orphaned files: {e}")
        return 0

# ---------- Student Management Functions ----------
def generate_student_id_simple(course_initials, phone_number):
    """Generate automatic student ID with format: INITIALS PHONE_NUMBER (e.g., MDA 7456890321)"""
    if not FIREBASE_AVAILABLE or students_collection is None:
        return f"{course_initials} {phone_number}"
    
    try:
        # Check if this exact student ID already exists
        existing_student_id = f"{course_initials} {phone_number}"
        docs = students_collection.where(filter=('student_id', '==', existing_student_id)).stream()
        
        # If the exact ID exists, return None to indicate it should not be used
        for doc in docs:
            return None
        
        return existing_student_id
        
    except Exception as e:
        print(f"Error generating simple student ID: {e}")
        return f"{course_initials} {phone_number}"

def generate_student_id(course_initials, batch_start_time, batch_end_time, batch_start_date):
    """Generate automatic student ID with format: INITIALS001 (START_TIME)-(END_TIME) (BATCH_START_DATE)"""
    # Handle unknown values by providing sensible defaults
    if batch_start_time == 'Unknown':
        batch_start_time = 'TBD'
    if batch_end_time == 'Unknown':
        batch_end_time = 'TBD'
    if batch_start_date == 'Unknown':
        batch_start_date = 'TBD'
        
    if not FIREBASE_AVAILABLE or students_collection is None:
        return f"{course_initials}001 ({batch_start_time})-({batch_end_time}) ({batch_start_date})"
    
    try:
        @techzone_app.route("/debug/students")
        def debug_students():
            if not FIREBASE_AVAILABLE or students_collection is None:
                return "Students collection not available."
            students = students_collection.stream()
            html = "<h2>All Students and batch_time</h2><table border='1'><tr><th>Username</th><th>Password</th><th>Batch Time</th></tr>"
            for student in students:
                data = student.to_dict()
                html += f"<tr><td>{data.get('username')}</td><td>{data.get('password')}</td><td>{data.get('batch_time')}</td></tr>"
            html += "</table>"
            return html

        # Get all existing students with the same course initials
        docs = students_collection.where('course_initials', '==', course_initials).stream()
        existing_numbers = []
        
        for doc in docs:
            student_data = doc.to_dict()
            student_id = student_data.get('student_id', '')
            # Extract number from student ID (e.g., EPE003 -> 3)
            if student_id.startswith(course_initials):
                try:
                    # Find the number part between initials and first space/parenthesis
                    id_part = student_id[len(course_initials):].split(' ')[0].split('(')[0]
                    if id_part.isdigit():
                        existing_numbers.append(int(id_part))
                except (ValueError, IndexError):
                    continue
        
        # Get the next sequential number
        next_number = max(existing_numbers, default=0) + 1
        
        # Format the student ID with proper format: EPE001 (4:00)-(5:00) (01-AUG-2025)
        formatted_number = f"{next_number:03d}"  # 001, 002, etc.
        student_id = f"{course_initials}{formatted_number} ({batch_start_time})-({batch_end_time}) ({batch_start_date})"
        
        return student_id
        
    except Exception as e:
        print(f"Error generating student ID: {e}")
        # Fallback ID generation
        return f"{course_initials}001 ({batch_start_time})-({batch_end_time}) ({batch_start_date})"

def get_all_students():
    """Get all students from Firestore"""
    if not FIREBASE_AVAILABLE or students_collection is None:
        return []
    try:
        docs = students_collection.stream()
        students = []
        for doc in docs:
            student_data = doc.to_dict()
            student_data['_id'] = doc.id
            students.append(student_data)
        return students
    except Exception as e:
        print(f"Error getting students: {e}")
        return []

def add_student(student_data):
    # Use batch_id from form if present, else resolve from batch_time
    if 'batch_id' in student_data and student_data['batch_id']:
        print('[DEBUG] Using batch_id from form:', student_data['batch_id'])
    else:
        # Try to find batch_id by matching batch_time or batch_name
        batch_name = student_data.get('batch_time') or student_data.get('batch_name')
        batch_id = None
        if batch_name and batches_collection is not None:
            all_batches = batches_collection.stream()
            for batch_doc in all_batches:
                batch = batch_doc.to_dict()
                display_name = f"{batch.get('original_batch_name') or batch.get('batch_name', '')} ({batch.get('start_time', '')})-({batch.get('end_time', '')}) ({batch.get('batch_start_date', '')})"
                if display_name == batch_name:
                    batch_id = batch_doc.id
                    break
        if batch_id:
            student_data['batch_id'] = batch_id
            print('[DEBUG] Resolved batch_id from batch_time:', batch_id)
        else:
            print('[WARN] Could not resolve batch_id for student:', student_data)
    # Check OTP verification
    if not session.get('student_email_otp_verified') or session.get('student_email_otp_email') != student_data.get('email'):
        return {"success": False, "error": "Email OTP not verified. Please verify the email before adding the student."}
    # Clear OTP verification after use
    session.pop('student_email_otp_verified', None)
    session.pop('student_email_otp', None)
    session.pop('student_email_otp_email', None)
    if not FIREBASE_AVAILABLE or students_collection is None:
        print("Firebase not available or students collection is None.")
        return {"success": False, "error": "Firebase not available"}
    try:
        print(f"Adding student with data: {student_data}")
        enrollment_datetime = datetime.now()
        enrollment_date = enrollment_datetime.strftime('%d-%m-%Y')
        enrollment_time = enrollment_datetime.strftime('%I:%M %p')
        assert 'student_name' in student_data, "Student name missing"
        assert isinstance(student_data['total_fees'], float), "Total fees must be a number"
        existing_students = get_all_students()
        if student_data.get('student_id'):
            for student in existing_students:
                if student.get('student_id') == student_data['student_id']:
                    print(f"Student ID {student_data['student_id']} already exists")
                    return {"success": False, "error": "student id already exists"}
        if student_data.get('email'):
            for student in existing_students:
                if student.get('email') == student_data['email']:
                    print(f"Email {student_data['email']} already exists for another student")
                    return {"success": False, "error": "student email already exists"}
        if student_data.get('username'):
            for student in existing_students:
                if student.get('username') == student_data['username']:
                    print(f"Username {student_data['username']} already exists for another student")
                    return {"success": False, "error": "username already exists"}
        if student_data.get('password'):
            for student in existing_students:
                if student.get('password') == student_data['password']:
                    print(f"Password already exists for another student")
                    return {"success": False, "error": "password already exists"}
        print("Validation passed. Processing student addition...")
        batch_time = student_data.get('batch_time', '')
        batch_start_time, batch_end_time = 'Unknown', 'Unknown'
        batch_start_date = 'Unknown'
        print(f"Debug: Processing batch_time: {batch_time}")
        if batch_time:
            # Handle new batch format: "Batch Name (Start Date) (Start Time-End Time)"
            # Example: "Prompt Engineering (01-AUG-2025) (4:00-5:00)"
            if '(' in batch_time and ')' in batch_time:
                try:
                    last_open = batch_time.rfind('(')
                    last_close = batch_time.rfind(')')
                    if last_open != -1 and last_close != -1 and last_close > last_open:
                        time_section = batch_time[last_open + 1:last_close]
                        print(f"Debug: Time section extracted: {time_section}")
                        if '-' in time_section:
                            times = time_section.split('-')
                            if len(times) == 2:
                                batch_start_time = times[0].strip()
                                batch_end_time = times[1].strip()
                                print(f"Debug: Extracted times - Start: {batch_start_time}, End: {batch_end_time}")
                except Exception as e:
                    print(f"Error parsing times from new format: {e}")
            if batch_time.count('(') >= 2:
                try:
                    first_open = batch_time.find('(')
                    first_close = batch_time.find(')', first_open)
                    if first_close != -1:
                        second_open = batch_time.find('(', first_close + 1)
                        if second_open != -1:
                            second_close = batch_time.find(')', second_open)
                            if second_close != -1:
                                date_section = batch_time[second_open + 1:second_close]
                                print(f"Debug: Date section extracted: {date_section}")
                                if any(char.isdigit() for char in date_section) and '-' in date_section:
                                    batch_start_date = date_section.upper()
                                    print(f"Debug: Formatted date: {batch_start_date}")
                except Exception as e:
                    print(f"Error parsing date from batch name: {e}")
            if batch_start_date == 'Unknown':
                print("Debug: Trying to get date from batch record")
                selected_batch_name = batch_time.split(' (')[0] if ' (' in batch_time else batch_time
                print(f"Debug: Selected batch name: {selected_batch_name}")
                batches = get_all_batches()
                for batch in batches:
                    if batch.get('batch_name') == selected_batch_name or batch.get('original_batch_name') == selected_batch_name:
                        batch_start_date = batch.get('batch_start_date', 'Unknown')
                        print(f"Debug: Found batch start date: {batch_start_date}")
                        if batch_start_date != 'Unknown' and batch_start_date:
                            try:
                                date_obj = datetime.strptime(batch_start_date, '%Y-%m-%d')
                                batch_start_date = date_obj.strftime('%d-%b-%Y').upper()
                                print(f"Debug: Converted date: {batch_start_date}")
                            except Exception as e:
                                print(f"Error parsing batch start date: {e}")
                        break
        course_initials = student_data.get('course_initials')
        phone_number = student_data.get('student_number')
        if course_initials and phone_number:
            # Use the new simple format: INITIALS PHONE_NUMBER
            generated_id = generate_student_id_simple(course_initials, phone_number)
            if generated_id is None:
                return {"success": False, "error": "Student ID already exists for this course type and phone number"}
            student_data['student_id'] = generated_id
            for student in existing_students:
                if student.get('student_id') == generated_id:
                    print(f"Student ID {generated_id} already exists (this should not happen with proper generation)")
                    return {"success": False, "error": "student id already exists"}
        student_data['created_at'] = enrollment_datetime.strftime('%Y-%m-%d %H:%M:%S')
        student_data['enrollment_date'] = enrollment_date
        student_data['enrollment_time'] = enrollment_time
        doc_ref = students_collection.document(student_data['student_id'])
        doc_ref.set(student_data)
        print("Student added successfully.")
        return {"success": True, "error": None}
    except AssertionError as e:
        print(f"Validation error: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"Error adding student: {e}")
        return {"success": False, "error": str(e)}

def update_student(student_doc_id, student_data):
    """Update a student in Firestore"""
    if not FIREBASE_AVAILABLE or students_collection is None:
        return {"success": False, "error": "Firebase not available"}
    try:
        # Check for uniqueness of email, username, and password (excluding current student)
        existing_students = get_all_students()
        
        # Check student ID uniqueness (excluding current student)
        if student_data.get('student_id'):
            for student in existing_students:
                if student.get('_id') != student_doc_id and student.get('student_id') == student_data['student_id']:
                    print(f"Student ID {student_data['student_id']} already exists for another student")
                    return {"success": False, "error": "student id already exists"}
        
        # Check email uniqueness
        if student_data.get('email'):
            for student in existing_students:
                if student.get('_id') != student_doc_id and student.get('email') == student_data['email']:
                    print(f"Email {student_data['email']} already exists for another student")
                    return {"success": False, "error": "student email already exists"}
        
        # Check username uniqueness
        if student_data.get('username'):
            for student in existing_students:
                if student.get('_id') != student_doc_id and student.get('username') == student_data['username']:
                    print(f"Username {student_data['username']} already exists for another student")
                    return {"success": False, "error": "username already exists"}
        
        # Check password uniqueness
        if student_data.get('password'):
            for student in existing_students:
                if student.get('_id') != student_doc_id and student.get('password') == student_data['password']:
                    print(f"Password already exists for another student")
                    return {"success": False, "error": "password already exists"}
        
        student_data['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        doc_ref = students_collection.document(student_doc_id)
        doc_ref.update(student_data)
        return {"success": True, "error": None}
    except Exception as e:
        print(f"Error updating student: {e}")
        return {"success": False, "error": str(e)}

def delete_student(student_doc_id):
    """Delete a student from Firestore"""
    if not FIREBASE_AVAILABLE or students_collection is None:
        return False
    try:
        doc_ref = students_collection.document(student_doc_id)
        doc_ref.delete()
        return True
    except Exception as e:
        print(f"Error deleting student: {e}")
        return False

def get_student_by_id(student_doc_id):
    """Get a specific student by document ID"""
    if not FIREBASE_AVAILABLE or students_collection is None:
        return None
    try:
        doc_ref = students_collection.document(student_doc_id)
        doc = doc_ref.get()
        if doc.exists:
            student_data = doc.to_dict()
            student_data['_id'] = doc.id
            return student_data
        return None
    except Exception as e:
        print(f"Error getting student: {e}")
        return None

# ---------- Batch Management Functions ----------
def get_all_batches():
    """Get all batches from Firestore"""
    if not FIREBASE_AVAILABLE or batches_collection is None:
        return []
    try:
        docs = batches_collection.stream()
        batches = []
        for doc in docs:
            batch_data = doc.to_dict()
            batch_data['_id'] = doc.id
            batches.append(batch_data)
        return batches
    except Exception as e:
        print(f"Error getting batches: {e}")
        return []

def add_batch(batch_data):
    """Add a new batch to Firestore"""
    if not FIREBASE_AVAILABLE or batches_collection is None:
        return False
    try:
        # Get current datetime for creation timestamp
        current_datetime = datetime.now()
        batch_data['created_at'] = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
        
        # Store the original batch name
        original_batch_name = batch_data.get('batch_name', '')
        batch_data['original_batch_name'] = original_batch_name
        
        # Keep the batch name as is (without creation date)
        # The batch name will be displayed as: Batch Name (Start Time)-(End Time)
        # The creation date is stored separately in batch_start_date
        
        doc_ref = batches_collection.document()
        doc_ref.set(batch_data)
        return True
    except Exception as e:
        print(f"Error adding batch: {e}")
        return False

def update_batch(batch_doc_id, batch_data):
    """Update a batch in Firestore"""
    if not FIREBASE_AVAILABLE or batches_collection is None:
        return False
    try:
        batch_data['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Store the original batch name
        original_batch_name = batch_data.get('batch_name', '')
        batch_data['original_batch_name'] = original_batch_name
        
        # Keep the batch name as is (without creation date)
        # The batch name will be displayed as: Batch Name (Start Time)-(End Time)
        # The creation date is stored separately in batch_start_date
        
        doc_ref = batches_collection.document(batch_doc_id)
        doc_ref.update(batch_data)
        return True
    except Exception as e:
        print(f"Error updating batch: {e}")
        return False

def delete_batch(batch_doc_id):
    """Delete a batch from Firestore"""
    if not FIREBASE_AVAILABLE or batches_collection is None:
        return False
    try:
        doc_ref = batches_collection.document(batch_doc_id)
        doc_ref.delete()
        return True
    except Exception as e:
        print(f"Error deleting batch: {e}")
        return False

# ---------- Course Tracking Functions ----------
def load_data():
    """Load course tracking data from Firestore"""
    if not FIREBASE_AVAILABLE or course_tracking_collection is None:
        return pd.DataFrame(columns=["Trainer Name", "Batch Name", "Ongoing Module Name", 
                                   "Completed Module", "Upcoming Module", "Class Date",
                                   "Start Time", "End Time", "Time stamp"])
    try:
        docs = course_tracking_collection.stream()
        records = []
        for doc in docs:
            record = doc.to_dict()
            record['_id'] = doc.id
            records.append(record)
        
        if records:
            df = pd.DataFrame(records)
            expected_columns = ["Trainer Name", "Batch Name", "Ongoing Module Name", 
                               "Completed Module", "Upcoming Module", "Class Date",
                               "Start Time", "End Time", "Time stamp"]
            df = df.reindex(columns=expected_columns, fill_value="")
        else:
            df = pd.DataFrame(columns=["Trainer Name", "Batch Name", "Ongoing Module Name", 
                                       "Completed Module", "Upcoming Module", "Class Date",
                                       "Start Time", "End Time", "Time stamp"])
        return df
    except Exception as e:
        print(f"Error loading course tracking data: {e}")
        return pd.DataFrame(columns=["Trainer Name", "Batch Name", "Ongoing Module Name", 
                                   "Completed Module", "Upcoming Module", "Class Date",
                                   "Start Time", "End Time", "Time stamp"])

def load_data_by_trainer(trainer_name):
    """Load all course tracking data from Firestore (showing all records like admin dashboard)"""
    if not FIREBASE_AVAILABLE or course_tracking_collection is None:
        return pd.DataFrame(columns=["Trainer Name", "Batch Name", "Ongoing Module Name", 
                                   "Completed Module", "Upcoming Module", "Class Date",
                                   "Start Time", "End Time", "Time stamp", "_id"])
    try:
        # Get all records from the collection (like admin dashboard)
        all_docs = course_tracking_collection.stream()
        all_records = []
        for doc in all_docs:
            record = doc.to_dict()
            record['_id'] = doc.id
            all_records.append(record)
        
        if all_records:
            df = pd.DataFrame(all_records)
            expected_columns = ["Trainer Name", "Batch Name", "Ongoing Module Name", 
                               "Completed Module", "Upcoming Module", "Class Date",
                               "Start Time", "End Time", "Time stamp", "_id"]
            df = df.reindex(columns=expected_columns, fill_value="")
        else:
            df = pd.DataFrame(columns=["Trainer Name", "Batch Name", "Ongoing Module Name", 
                                       "Completed Module", "Upcoming Module", "Class Date",
                                       "Start Time", "End Time", "Time stamp", "_id"])
        return df
    except Exception as e:
        print(f"Error loading course tracking data by trainer: {e}")
        return pd.DataFrame(columns=["Trainer Name", "Batch Name", "Ongoing Module Name", 
                                   "Completed Module", "Upcoming Module", "Class Date",
                                   "Start Time", "End Time", "Time stamp", "_id"])

def add_record(data):
    """Add a single record to Firestore"""
    if not FIREBASE_AVAILABLE or course_tracking_collection is None:
        return False
    try:
        doc_ref = course_tracking_collection.document()
        doc_ref.set(data)
        return True
    except Exception as e:
        print(f"Error adding course tracking record: {e}")
        return False

def edit_record(index, data):
    """Edit a record by index in Firestore"""
    if not FIREBASE_AVAILABLE or course_tracking_collection is None:
        return False
    try:
        docs = list(course_tracking_collection.stream())
        if 0 <= index < len(docs):
            doc_ref = docs[index].reference
            doc_ref.update(data)
            return True
        return False
    except Exception as e:
        print(f"Error editing course tracking record: {e}")
        return False

def delete_record(index):
    """Delete a record by index from Firestore"""
    if not FIREBASE_AVAILABLE or course_tracking_collection is None:
        return False
    try:
        docs = list(course_tracking_collection.stream())
        if 0 <= index < len(docs):
            doc_ref = docs[index].reference
            doc_ref.delete()
            return True
        return False
    except Exception as e:
        print(f"Error deleting course tracking record: {e}")
        return False

def edit_record_by_id(record_id, data):
    """Edit a record by document ID in Firestore"""
    if not FIREBASE_AVAILABLE or course_tracking_collection is None:
        return False
    try:
        # First, let's check if the document exists and get its current data
        doc_ref = course_tracking_collection.document(record_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            print(f"Document with ID {record_id} does not exist!")
            return False
        
        # Get the current document data
        current_data = doc.to_dict()
        
        # Preserve the original timestamp
        if 'Time stamp' in current_data:
            data['Time stamp'] = current_data['Time stamp']
        else:
            # If no timestamp exists, create a new one
            data['Time stamp'] = f"{datetime.now().strftime('%Y-%m-%d %I:%M %p')}"
        
        # Update the document
        doc_ref.update(data)
        return True
    except Exception as e:
        print(f"Error editing course tracking record by ID: {e}")
        return False

# ---------- Messaging Functions ----------
def send_message(batch_id, trainer_name, message_content):
    """Send a message to a specific batch."""
    if not FIREBASE_AVAILABLE or messages_collection is None:
        return False
    try:
        message_data = {
            'batch_id': batch_id,
            'trainer_name': trainer_name,
            'message_content': message_content,
            'timestamp': datetime.now(),
            'read_by': []  # List of student IDs who have read the message
        }
        messages_collection.add(message_data)
        return True
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def get_messages_for_batch(batch_id):
    """Get all messages for a specific batch."""
    if not FIREBASE_AVAILABLE or messages_collection is None:
        return []
    try:
        print("[DEBUG] Querying messages for batch_id:", batch_id)
        docs = messages_collection.where('batch_id', '==', batch_id).order_by('timestamp', direction='DESCENDING').stream()
        messages = []
        for doc in docs:
            message_data = doc.to_dict()
            message_data['_id'] = doc.id
            messages.append(message_data)
        print(f"[DEBUG] Fetched {len(messages)} messages for batch_id {batch_id}")
        for m in messages:
            print("[DEBUG] Message:", m)
        return messages
    except Exception as e:
        print(f"Error getting messages: {e}")
        return []

def mark_messages_as_read(student_id, batch_id):
    """Mark all messages in a batch as read by a student."""
    if not FIREBASE_AVAILABLE or messages_collection is None:
        return False
    try:
        docs = messages_collection.where(filter=('batch_id', '==', batch_id)).stream()
        for doc in docs:
            doc_ref = doc.reference
            doc_ref.update({
                'read_by': firestore.ArrayUnion([student_id])
            })
        return True
    except Exception as e:
        print(f"Error marking messages as read: {e}")
        return False

# ---------- Student Feedback Functions ----------
def add_student_feedback(feedback_data):
    """Add a new student feedback to Firestore"""
    if not FIREBASE_AVAILABLE or student_feedback_collection is None:
        return False
    try:
        feedback_data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        doc_ref = student_feedback_collection.document()
        doc_ref.set(feedback_data)
        return True
    except Exception as e:
        print(f"Error adding student feedback: {e}")
        return False

def get_all_student_feedback():
    """Get all student feedback from Firestore"""
    if not FIREBASE_AVAILABLE or student_feedback_collection is None:
        return []
    try:
        docs = student_feedback_collection.order_by('created_at', direction='DESCENDING').stream()
        feedbacks = []
        for doc in docs:
            feedback_data = doc.to_dict()
            feedback_data['_id'] = doc.id
            feedbacks.append(feedback_data)
        return feedbacks
    except Exception as e:
        print(f"Error getting student feedback: {e}")
        return []

def delete_student_feedback(feedback_doc_id):
    """Delete a specific feedback by document ID"""
    if not FIREBASE_AVAILABLE or student_feedback_collection is None:
        return False
    try:
        doc_ref = student_feedback_collection.document(feedback_doc_id)
        doc_ref.delete()
        return True
    except Exception as e:
        print(f"Error deleting student feedback: {e}")
        return False

def delete_all_student_feedback():
    """Delete all student feedback"""
    if not FIREBASE_AVAILABLE or student_feedback_collection is None:
        return False
    try:
        docs = student_feedback_collection.stream()
        for doc in docs:
            doc.reference.delete()
        return True
    except Exception as e:
        print(f"Error deleting all student feedback: {e}")
        return False

# ---------- Role Credentials Functions ----------
def check_admin_login(username, password):
    """Check admin login credentials from Firestore"""
    if not FIREBASE_AVAILABLE or role_credentials_collection is None:
        return False
    try:
        docs = role_credentials_collection.where('username', '==', username).where('password', '==', hash_password(password)).where('role', '==', 'Admin').stream()
        return len(list(docs)) > 0
    except Exception as e:
        print(f"Error checking admin login: {e}")
        return False

def check_role_login(username, password, role):
    """Check role-based login credentials from Firestore"""
    if not FIREBASE_AVAILABLE or role_credentials_collection is None:
        print("[DEBUG] Firebase unavailable or role_credentials_collection is None")
        return False
    try:
        hashed_pw = hash_password(password)
        print(f"[DEBUG] Checking login for username: '{username}', hashed_password: '{hashed_pw}', role: '{role}'")
        docs = role_credentials_collection.where('username', '==', username).where('password', '==', hashed_pw).where('role', '==', role).stream()
        found = False
        for doc in docs:
            print(f"[DEBUG] Found matching document: {doc.to_dict()}")
            found = True
        if not found:
            print("[DEBUG] No matching document found for given credentials.")
        return found
    except Exception as e:
        print(f"Error checking role login: {e}")
        return False

def check_student_login(username, password, batch_id):
    """Check student login credentials from Firestore"""
    if not FIREBASE_AVAILABLE or students_collection is None:
        return None
    try:
        docs = students_collection.where('username', '==', username).where('password', '==', password).where('batch_id', '==', batch_id).stream()
        for doc in docs:
            student_data = doc.to_dict()
            student_data['_id'] = doc.id
            return student_data
        return None
    except Exception as e:
        print(f"Error checking student login: {e}")
        return None

# ---------- Email Configuration ----------
try:
    from .email_config import EMAIL_CONFIG
except ImportError:
    print("Warning: email_config.py not found. Using default configuration.")
    EMAIL_CONFIG = {
        'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.environ.get('SMTP_PORT', '587')),
        'email': os.environ.get('EMAIL_ADDRESS', 'your_email@gmail.com'),
        'password': os.environ.get('EMAIL_PASSWORD', 'your_app_password')
    }

def send_student_email(student_email, student_data):
    """Send student details via email"""
    try:
        if (EMAIL_CONFIG['email'] == 'your_email@gmail.com' or 
            EMAIL_CONFIG['password'] == 'your_app_password'):
            print("Email configuration not set up properly. Please update email_config.py")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['email']
        msg['To'] = student_email
        msg['Subject'] = f"Student Receipt - {student_data['student_name']} - TechZone Academy"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; margin: -30px -30px 30px -30px; }}
                .detail-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
                .detail-label {{ font-weight: bold; color: #333; }}
                .detail-value {{ color: #666; }}
                .login-credentials {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .credentials-title {{ font-weight: bold; margin-bottom: 10px; font-size: 16px; }}
                .credential-item {{ margin: 5px 0; }}
                .due-fees {{ color: #dc3545; font-weight: bold; }}
                .paid-fees {{ color: #28a745; font-weight: bold; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎓 TechZone Academy</h1>
                    <h2>Student Receipt & Login Details</h2>
                </div>
                
                <div class="login-credentials">
                    <div class="credentials-title">🔐 Your Login Credentials</div>
                    <div class="credential-item"><strong>Username:</strong> {student_data.get('username', 'Not set')}</div>
                    <div class="credential-item"><strong>Password:</strong> {student_data.get('password', 'Not set')}</div>
                    <div class="credential-item"><strong>Portal URL:</strong> http://localhost:5000</div>
                </div>
                
                <div class="detail-row"><span class="detail-label">Student ID:</span><span class="detail-value">{student_data['student_id']}</span></div>
                <div class="detail-row"><span class="detail-label">Student Name:</span><span class="detail-value">{student_data['student_name']}</span></div>
                <div class="detail-row"><span class="detail-label">Phone Number:</span><span class="detail-value">{student_data.get('student_number', 'Not provided')}</span></div>
                <div class="detail-row"><span class="detail-label">Email:</span><span class="detail-value">{student_data.get('email', 'Not provided')}</span></div>
                <div class="detail-row"><span class="detail-label">Course Name:</span><span class="detail-value">{student_data['course_name']}</span></div>
                <div class="detail-row"><span class="detail-label">Batch Time:</span><span class="detail-value">{student_data.get('batch_time', 'Not assigned')}</span></div>
                <div class="detail-row"><span class="detail-label">Total Fees:</span><span class="detail-value">₹{student_data['total_fees']:.2f}</span></div>
                <div class="detail-row"><span class="detail-label">Fees Paid:</span><span class="detail-value paid-fees">₹{student_data['fees_paid']:.2f}</span></div>
                <div class="detail-row"><span class="detail-label">Due Fees:</span><span class="detail-value {'due-fees' if student_data.get('due_fees', 0) > 0 else 'paid-fees'}">₹{student_data.get('due_fees', 0):.2f}</span></div>
                <div class="detail-row"><span class="detail-label">Number of Installments:</span><span class="detail-value">{student_data.get('installments', 'Not set')}</span></div>
                <div class="detail-row"><span class="detail-label">Fees Due Date:</span><span class="detail-value">{student_data.get('fees_due_date', 'Not set')}</span></div>
                <div class="detail-row"><span class="detail-label">Fees Status:</span><span class="detail-value {'paid-fees' if student_data.get('fees_status') == 'Paid' else 'due-fees'}">{student_data.get('fees_status', 'Unpaid')}</span></div>
                <div class="detail-row"><span class="detail-label">Enrollment Date:</span><span class="detail-value">{student_data.get('created_at', 'Not recorded')}</span></div>
                
                <div class="footer">
                    <p><strong>Important Instructions:</strong></p>
                    <p>1. Use the username and password above to login to the student portal</p>
                    <p>2. Keep your login credentials secure and confidential</p>
                    <p>3. Contact administration if you have any issues accessing your account</p>
                    <hr>
                    <p>This email was sent from TechZone Academy Student Management System.</p>
                    <p>If you have any questions, please contact us.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        text = msg.as_string()
        server.sendmail(EMAIL_CONFIG['email'], student_email, text)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# ---------- Admin Management Functions ----------
def get_all_admins():
    """Get all admins from Firestore"""
    if not FIREBASE_AVAILABLE or role_credentials_collection is None:
        return []
    try:
        docs = role_credentials_collection.where(filter=('role', '==', 'Admin')).stream()
        admins = []
        for doc in docs:
            admin_data = doc.to_dict()
            admin_data['_id'] = doc.id
            admins.append(admin_data)
        return admins
    except Exception as e:
        print(f"Error getting admins: {e}")
        return []

def add_admin(admin_data):
    """Add a new admin to Firestore"""
    if not FIREBASE_AVAILABLE or role_credentials_collection is None:
        print("Firebase not available or role_credentials collection is None.")
        return False
    try:
        # Check if username already exists
        docs = role_credentials_collection.where('username', '==', admin_data['username']).where('role', '==', 'Admin').stream()
        for doc in docs:
            print(f"Admin with username {admin_data['username']} already exists")
            return False
        # Store original password for Super Admin visibility
        original_password = admin_data['password']
        admin_data['password'] = hash_password(admin_data['password'])
        admin_data['original_password'] = original_password
        admin_data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        admin_data['role'] = 'Admin'
        admin_data['status'] = 'active'
        doc_ref = role_credentials_collection.document()
        doc_ref.set(admin_data)
        print("Admin added successfully.")
        return True
    except Exception as e:
        print(f"Error adding admin: {e}")
        return False

def update_admin(admin_id, admin_data):
    """Update an admin in Firestore"""
    if not FIREBASE_AVAILABLE or role_credentials_collection is None:
        print("Firebase not available or role_credentials collection is None.")
        return False
    try:
        # Hash the password if it's being updated
        if 'password' in admin_data and admin_data['password']:
            original_password = admin_data['password']
            admin_data['password'] = hash_password(admin_data['password'])
            admin_data['original_password'] = original_password
        elif 'password' in admin_data and not admin_data['password']:
            del admin_data['password']
        admin_data['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        doc_ref = role_credentials_collection.document(admin_id)
        doc_ref.update(admin_data)
        print(f"Admin {admin_id} updated successfully.")
        return True
    except Exception as e:
        print(f"Error updating admin: {e}")
        return False

def delete_admin(admin_id):
    """Delete an admin from Firestore"""
    if not FIREBASE_AVAILABLE or role_credentials_collection is None:
        return False
    try:
        doc_ref = role_credentials_collection.document(admin_id)
        doc_ref.delete()
        print(f"Admin {admin_id} deleted successfully.")
        return True
    except Exception as e:
        print(f"Error deleting admin: {e}")
        return False

# ---------- Routes ----------
@techzone_app.route("/student_login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        batch_id = request.form.get("batch_id")

        if not username or not password or not batch_id:
            flash("Please fill in all fields and select your batch!", "danger")
            return render_template("login.html", batches=get_all_batches())

        if FIREBASE_AVAILABLE and students_collection is not None:
            try:
                print(f"[DEBUG] Submitted username: {username}")
                print(f"[DEBUG] Submitted password: {password}")
                print(f"[DEBUG] Submitted batch_id: {batch_id}")
                # Print all students with this username
                all_user_docs = students_collection.where('username', '==', username).stream()
                for doc in all_user_docs:
                    stu = doc.to_dict()
                    print(f"[DEBUG] Candidate student: username={stu.get('username')}, password={stu.get('password')}, batch_id={stu.get('batch_id')}, doc_id={doc.id}")
                # Now try to match all three fields
                docs = students_collection.where('username', '==', username)\
                                         .where('password', '==', password)\
                                         .where('batch_id', '==', batch_id)\
                                         .stream()
                student_doc = next(docs, None)
                print("[DEBUG] Student found:", student_doc)
                if student_doc:
                    student_data = student_doc.to_dict()
                    session["logged_in"] = True
                    session["username"] = username
                    session["role"] = "Student"
                    session["student_batch"] = batch_id
                    session["student_id"] = student_doc.id
                    return redirect(url_for("dashboard"))
            except Exception as e:
                print(f"Error checking student login: {e}")

        flash("Invalid student credentials or batch selection!", "danger")
        return render_template("login.html", batches=get_all_batches())

    # GET request: show the login page with all batches
    return render_template("login.html", batches=get_all_batches())

@techzone_app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role")
        username = request.form.get("username")
        password = request.form.get("password")
        batch_name = request.form.get("batch_name") if role == "Student" else None
        
        if not role or not username or not password:
            flash("Please fill in all fields and select a role!", "danger")
            return render_template("login.html", batches=get_all_batches())
        
        if role == "Student" and not batch_name:
            flash("Please select your batch!", "danger")
            return render_template("login.html", batches=get_all_batches())
        
        # Check student login
        if role == "Student":
            student = check_student_login(username, password, batch_name)
            if student:
                session["logged_in"] = True
                session["username"] = username
                session["role"] = role
                # Find the batch _id based on the selected batch_name string
                batches = get_all_batches()
                batch_id = None
                for batch in batches:
                    # Compose display name as shown in dropdown
                    display_name = f"{batch.get('batch_name', '')} ({batch.get('batch_start_date', '')}) ({batch.get('start_time', '')}-{batch.get('end_time', '')})"
                    if display_name == batch_name:
                        batch_id = batch.get('_id')
                        break
                if not batch_id:
                    flash('Batch not found! Please contact admin.', 'danger')
                    return render_template('login.html', batches=get_all_batches())
                session["student_batch"] = batch_id
                session["student_id"] = student["_id"]
                return redirect(url_for("dashboard"))
            flash("Invalid student credentials or batch selection!", "danger")
            return render_template("login.html", batches=get_all_batches())
        
        # Check other roles
        if role in ["Super Admin", "Trainer", "Admin"]:
            if check_role_login(username, password, role):
                session["logged_in"] = True
                session["username"] = username
                session["role"] = role
                return redirect(url_for("dashboard"))
        
        flash("Invalid credentials!", "danger")
    return render_template("login.html", batches=get_all_batches())

@techzone_app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    role = session["role"]
    username = session["username"]
    df = load_data()

    if role == "Trainer":
        trainer_name = session.get("username")
        all_batches = get_all_batches()
        print("Trainer name:", trainer_name)
        print("All batches:", all_batches)
        # Show all batches in dropdown, not just assigned ones
        trainer_batches = all_batches
        print("Trainer batches:", trainer_batches)
        # Gather messages for each batch
        batch_messages = {}
        for batch in trainer_batches:
            batch_id = str(batch.get('_id'))
            batch_messages[batch_id] = get_messages_for_batch(batch_id)

        if request.method == "POST":
            # This POST handling is for the file upload form.
            # The message sending is handled by its own route, send_trainer_message.
            batch_id = request.form.get('batch_id')
            if 'file' in request.files and batch_id:
                file = request.files['file']
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    # Add trainer username prefix to avoid conflicts
                    prefixed_filename = f"{trainer_name}_{filename}"
                    try:
                        if FIREBASE_AVAILABLE and storage_bucket is not None:
                            # Get file data first for size calculation
                            file.seek(0)
                            file_data = file.read()
                            file_size = len(file_data)
                            
                            # Upload to Firebase Storage
                            file.seek(0)  # Reset file pointer for upload
                            blob = storage_bucket.blob(f"trainer_uploads/{prefixed_filename}")
                            blob.upload_from_file(file, content_type=file.content_type)
                            
                            # Store file metadata in Firestore (without base64 data to avoid size limits)
                            file_record = {
                                'filename': prefixed_filename,
                                'original_filename': filename,
                                'uploaded_by': trainer_name,
                                'batch_id': batch_id,
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'file_size': file_size,
                                'content_type': file.content_type,
                                'storage_path': f"trainer_uploads/{prefixed_filename}",
                                'uploaded_to_storage': True
                            }
                            
                            # Only store base64 for very small files (less than 500KB)
                            if file_size < 500000:  # 500KB limit
                                file_data_base64 = base64.b64encode(file_data).decode('utf-8')
                                file_record['file_data_base64'] = file_data_base64
                                file_record['has_base64_backup'] = True
                            else:
                                file_record['has_base64_backup'] = False
                            
                            trainer_files_collection.add(file_record)
                            flash("File uploaded successfully!", "success")
                        else:
                            flash("Firebase Storage not available!", "danger")
                    except Exception as e:
                        print(f"Error uploading file: {e}")
                        flash(f"Error uploading file: {str(e)}", "danger")
                else:
                    flash('No selected file', 'danger')
            else:
                flash('No file part or batch selected', 'danger')
            return redirect(url_for('dashboard'))

        # This part handles the GET request to display the dashboard.
        trainer_batch_files = {}
        for batch in trainer_batches:
            batch_id = str(batch['_id'])  # Ensure string format for consistency
            batch_name = batch.get('batch_name', 'Unknown Batch')
            files_for_batch = get_trainer_files_by_batch(batch_id)
            trainer_batch_files[batch_id] = {
                'batch_name': batch_name,
                'files': files_for_batch
            }

        return render_template(
            "dashboard_trainer.html", 
            username=trainer_name, 
            batches=trainer_batches, 
            trainer_batch_files=trainer_batch_files,
            trainer_name=trainer_name
        )

    elif role == "Admin":
        if request.method == "POST":
            action = request.form["action"]
            if action == "add":
                data = {
                    "Trainer Name": request.form["trainer"],
                    "Batch Name": request.form["batch"],
                    "Ongoing Module Name": request.form["ongoing_module"],
                    "Completed Module": request.form["completed_module"],
                    "Upcoming Module": request.form["upcoming_module"],
                    "Class Date": request.form["class_date"],
                    "Start Time": request.form["start_time"],
                    "End Time": request.form["end_time"],
                    "Time stamp": f"{datetime.now().strftime('%Y-%m-%d %I:%M %p')}"
                }
                add_record(data)
                flash("Record added successfully!", "success")
            elif action == "edit":
                index = int(request.form["edit_index"])
                data = {
                    "Trainer Name": request.form["trainer"],
                    "Batch Name": request.form["batch"],
                    "Ongoing Module Name": request.form["ongoing_module"],
                    "Completed Module": request.form["completed_module"],
                    "Upcoming Module": request.form["upcoming_module"],
                    "Class Date": request.form["class_date"],
                    "Start Time": request.form["start_time"],
                    "End Time": request.form["end_time"]
                }
                edit_record(index, data)
                flash("Record updated successfully!", "success")
            elif action == "delete":
                index = int(request.form["delete_index"])
                delete_record(index)
                flash("Record deleted!", "warning")
            df = load_data()
        
        batches = get_all_batches()
        return render_template("dashboard_admin.html", data=df, batches=batches)

    elif role == "Super Admin":
        batches = get_all_batches()
        return render_template("dashboard_boss.html", data=df, batches=batches)

    elif role == "Student":
        if request.method == "POST":
            action = request.form.get("action")
            if action == "submit_feedback":
                feedback_text = request.form.get("feedback_text")
                if feedback_text and feedback_text.strip():
                    student_id = session.get("student_id")
                    student_info = get_student_by_id(student_id)
                    
                    if student_info:
                        feedback_data = {
                            "student_id": student_id,
                            "student_record_id": student_info.get("student_id", "Unknown"),
                            "student_name": student_info.get("student_name", "Unknown"),
                            "student_number": student_info.get("student_number", "Unknown"),
                            "batch_name": student_info.get("batch_time", "Unknown"),
                            "feedback_text": feedback_text.strip(),
                            "submitted_by": username
                        }
                        
                        if add_student_feedback(feedback_data):
                            flash("Feedback submitted successfully!", "success")
                        else:
                            flash("Error submitting feedback. Please try again.", "danger")
                    else:
                        flash("Student information not found!", "danger")
                else:
                    flash("Please enter your feedback before submitting.", "danger")
                
                return redirect(url_for("dashboard"))
        
        # Fetch messages for the student's batch
        batch_id = session.get("student_batch")
        print("[DEBUG] Student batch_id from session:", batch_id)
        messages = get_messages_for_batch(batch_id)
        print("[DEBUG] Messages fetched for batch:", messages)
        
        # Calculate unread message count
        unread_count = 0
        for msg in messages:
            if username not in msg.get('read_by', []):
                unread_count += 1
        
        # Get files for student's batch - create batch_files structure like trainer dashboard
        batch_files = {}
        if batch_id:
            files_for_batch = get_trainer_files_by_batch(batch_id)
            if files_for_batch:
                # Get batch info for display name
                batches = get_all_batches()
                batch_name = "Unknown Batch"
                for batch in batches:
                    if str(batch['_id']) == str(batch_id):
                        if batch.get('original_batch_name'):
                            batch_name = f"{batch.get('original_batch_name')} ({batch.get('start_time', 'Unknown')})-({batch.get('end_time', 'Unknown')}) ({batch.get('batch_start_date', 'Unknown')})"
                        else:
                            batch_name = f"{batch.get('batch_name', 'Unknown')} ({batch.get('start_time', 'Unknown')})-({batch.get('end_time', 'Unknown')}) ({batch.get('batch_start_date', 'Unknown')})"
                        break
                
                batch_files[batch_id] = {
                    'batch_name': batch_name,
                    'files': files_for_batch
                }
                
        return render_template("dashboard_student.html", username=username, batch_files=batch_files, batch_id=batch_id, messages=messages, unread_count=unread_count)

@techzone_app.route("/trainer-modules", methods=["GET", "POST"])
def trainer_modules():
    if not session.get("logged_in") or session.get("role") != "Trainer":
        return redirect(url_for("login"))
    
    username = session["username"]
    df = load_data_by_trainer(username)
    
    if request.method == "POST":
        action = request.form.get("action")
        if action == "edit":
            record_id = request.form.get("edit_record_id")
            data = {
                "Trainer Name": request.form["trainer"],
                "Batch Name": request.form["batch"],
                "Ongoing Module Name": request.form["ongoing_module"],
                "Completed Module": request.form["completed_module"],
                "Upcoming Module": request.form["upcoming_module"],
                "Class Date": request.form["class_date"],
                "Start Time": request.form["start_time"],
                "End Time": request.form["end_time"]
            }
            
            if edit_record_by_id(record_id, data):
                flash("Record updated successfully!", "success")
            else:
                flash("Error updating record!", "danger")
            
            df = load_data_by_trainer(username)
    
    batches = get_all_batches()
    return render_template("trainer_modules.html", data=df, batches=batches, trainer_name=username)

@techzone_app.route("/batch-summary")
def batch_summary():
    if not session.get("logged_in") or session.get("role") not in ["Super Admin", "Admin"]:
        return redirect(url_for("login"))
    
    batches = get_all_batches()
    students = get_all_students()
    
    # Calculate batch-wise summary
    batch_summary = []
    for batch in batches:
        batch_id = batch['_id']
        # Use detailed batch name formatting consistent with other templates
        # Format the date using the same logic as the template filter
        batch_start_date = batch.get('batch_start_date', 'Unknown')
        if batch_start_date and batch_start_date != 'Unknown':
            try:
                from datetime import datetime
                date_obj = datetime.strptime(batch_start_date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d-%b-%Y').upper()
            except:
                formatted_date = batch_start_date
        else:
            formatted_date = 'Unknown'
            
        if batch.get('original_batch_name'):
            batch_display_name = f"{batch.get('original_batch_name')} ({batch.get('start_time', 'Unknown')})-({batch.get('end_time', 'Unknown')}) ({formatted_date})"
        else:
            batch_display_name = f"{batch.get('batch_name', 'Unknown')} ({batch.get('start_time', 'Unknown')})-({batch.get('end_time', 'Unknown')}) ({formatted_date})"
        
        # Count students in this batch
        batch_students = [s for s in students if s.get('batch_id') == batch_id]
        total_students = len(batch_students)
        
        # Count paid and unpaid students
        paid_students = len([s for s in batch_students if s.get('fees_status') == 'Paid'])
        unpaid_students = total_students - paid_students
        
        batch_summary.append({
            'batch_name': batch_display_name,
            'total_students': total_students,
            'paid_students': paid_students,
            'unpaid_students': unpaid_students
        })
    
    # Sort batch summary by batch name
    batch_summary.sort(key=lambda x: x['batch_name'])
    
    return render_template("batch_summary.html", batches=batches, students=students, batch_summary=batch_summary)

@techzone_app.route("/student-management")
def student_management():
    if not session.get("logged_in") or session.get("role") != "Admin":
        return redirect(url_for("login"))
    
    batches = get_all_batches()
    students = get_all_students()
    
    # Calculate batch-wise summary
    batch_summary = []
    for batch in batches:
        batch_id = batch['_id']
        batch_display_name = f"{batch.get('batch_name', 'Unknown')} ({batch.get('start_time', 'Unknown')}-{batch.get('end_time', 'Unknown')}) ({batch.get('batch_start_date', 'Unknown')})"
        
        # Count students in this batch
        batch_students = [s for s in students if s.get('batch_id') == batch_id]
        total_students = len(batch_students)
        
        # Count paid and unpaid students
        paid_students = len([s for s in batch_students if s.get('fees_status') == 'Paid'])
        unpaid_students = total_students - paid_students
        
        batch_summary.append({
            'batch_name': batch_display_name,
            'total_students': total_students,
            'paid_students': paid_students,
            'unpaid_students': unpaid_students
        })
    
    # Sort batch summary by batch name
    batch_summary.sort(key=lambda x: x['batch_name'])
    
    return render_template("student_management.html", batches=batches, students=students, batch_summary=batch_summary)

@techzone_app.route("/student-details", methods=["GET", "POST"])
def student_details():
    if not session.get("logged_in") or session.get("role") != "Admin":
        return redirect(url_for("login"))
    
    # Handle search via GET request
    search_query = request.args.get('search_query', '').strip()

    # Initialize filter variables
    selected_batch = request.form.get("batch") if request.method == "POST" else None
    selected_status = request.form.get("fee_status") if request.method == "POST" else None
    
    if request.method == "POST":
        action = request.form.get("action")
        
        # Handle filter form submission
        if action == "filter_students":
            selected_batch = request.form.get("batch")
            selected_status = request.form.get("fee_status")
            # Don't process other POST actions, just filter
        elif action == "add_student":
            # Handle fees due date
            fees_due_date = request.form["fees_due_date"]
            if fees_due_date == "custom":
                fees_due_date = request.form["custom_date"]
            
            # Handle custom course initials
            course_initials = request.form["course_initials"]
            if course_initials == "CUSTOM":
                custom_course_initials = request.form.get("custom_course_initials", "").strip().upper()
                if custom_course_initials and len(custom_course_initials) >= 2 and len(custom_course_initials) <= 4:
                    course_initials = custom_course_initials
                else:
                    flash("Custom course initials must be 2-4 characters long!", "danger")
                    # Continue with error but use default
                    course_initials = "CUSTOM"
            
            print("[DEBUG] Received batch_id from form:", request.form.get("batch_id"))
            student_data = {
                "course_initials": course_initials,
                "student_name": request.form["student_name"],
                "student_number": request.form["student_number"],
                "email": request.form["email"],
                "course_name": request.form["course_name"],
                "batch_time": request.form["batch_time"],
                "total_fees": float(request.form["total_fees"]),
                "fees_paid": float(request.form["fees_paid"]),
                "due_fees": float(request.form["due_fees"]),
"installments": request.form["installments"],
                "fees_due_date": fees_due_date,
                "fees_status": request.form["fees_status"],
                "username": request.form["username"],
                "password": request.form["password"],
                "batch_id": request.form.get("batch_id")
            }
            
            # Use the generated student ID if provided
            if request.form.get("generated_student_id"):
                student_data["student_id"] = request.form["generated_student_id"]
            
            result = add_student(student_data)
            if result["success"]:
                flash("Student added successfully!", "success")
            else:
                flash(result["error"], "danger")
                
        elif action == "update_student":
            student_id = request.form["student_id_hidden"]
            
            # Handle fees due date
            fees_due_date = request.form["fees_due_date"]
            if fees_due_date == "custom":
                fees_due_date = request.form["custom_date"]
            
            # Handle custom course initials
            course_initials = request.form["course_initials"]
            if course_initials == "CUSTOM":
                custom_course_initials = request.form.get("custom_course_initials", "").strip().upper()
                if custom_course_initials and len(custom_course_initials) >= 2 and len(custom_course_initials) <= 4:
                    course_initials = custom_course_initials
                else:
                    flash("Custom course initials must be 2-4 characters long!", "danger")
                    # Continue with error but use default
                    course_initials = "CUSTOM"
            
            student_data = {
                "course_initials": course_initials,
                "student_name": request.form["student_name"],
                "student_number": request.form["student_number"],
                "email": request.form["email"],
                "course_name": request.form["course_name"],
                "batch_time": request.form["batch_time"],
                "total_fees": float(request.form["total_fees"]),
                "fees_paid": float(request.form["fees_paid"]),
                "due_fees": float(request.form["due_fees"]),
"installments": request.form["installments"],
                "fees_due_date": fees_due_date,
                "fees_status": request.form["fees_status"],
                "username": request.form["username"],
                "password": request.form["password"]
            }
            # Regenerate student_id if batch_time or batch_start_date changes
            old_student = get_student_by_id(student_id)
            old_batch_time = old_student.get("batch_time") if old_student else None
            old_batch_start_date = None
            if old_student:
                # Find the batch for the old batch_time
                old_batches = get_all_batches()
                old_selected_batch_name = old_batch_time.split(' (')[0] if old_batch_time and ' (' in old_batch_time else old_batch_time
                for batch in old_batches:
                    if batch.get('batch_name') == old_selected_batch_name:
                        old_batch_start_date = batch.get('batch_start_date', None)
                        break
            # Get new batch start date and times using the same logic as add_student
            new_batch_time = student_data["batch_time"]
            new_batch_start_date = 'Unknown'
            batch_start_time, batch_end_time = 'Unknown', 'Unknown'
            
            if new_batch_time:
                # Handle new batch format: "Batch Name (Start Date) (Start Time-End Time)"
                # Example: "Prompt Engineering (01-AUG-2025) (4:00-5:00)"
                
                # Extract times from the new format
                if '(' in new_batch_time and ')' in new_batch_time:
                    try:
                        # Find the time section in the last set of parentheses
                        last_open = new_batch_time.rfind('(')
                        last_close = new_batch_time.rfind(')')
                        if last_open != -1 and last_close != -1 and last_close > last_open:
                            time_section = new_batch_time[last_open + 1:last_close]
                            print(f"Debug: Time section extracted: {time_section}")
                            
                            # Split by "-" to get start and end times
                            if '-' in time_section:
                                times = time_section.split('-')
                                if len(times) == 2:
                                    batch_start_time = times[0].strip()
                                    batch_end_time = times[1].strip()
                                    print(f"Debug: Extracted times - Start: {batch_start_time}, End: {batch_end_time}")
                    except Exception as e:
                        print(f"Error parsing times from new format: {e}")
                        # Fallback: try to get times from batch record
                        try:
                            new_selected_batch_name = new_batch_time.split(' (')[0] if ' (' in new_batch_time else new_batch_time
                            batches = get_all_batches()
                            for batch in batches:
                                if batch.get('batch_name') == new_selected_batch_name or batch.get('original_batch_name') == new_selected_batch_name:
                                    batch_start_time = batch.get('start_time', 'Unknown')
                                    batch_end_time = batch.get('end_time', 'Unknown')
                                    print(f"Debug: Fallback times from batch - Start: {batch_start_time}, End: {batch_end_time}")
                                    break
                        except Exception as fallback_e:
                            print(f"Error in fallback time parsing: {fallback_e}")
                
                # Extract batch start date from the second set of parentheses
                if new_batch_time.count('(') >= 2:  # Should have at least 2 sets of parentheses
                    try:
                        # Find the second set of parentheses (date section)
                        first_open = new_batch_time.find('(')
                        first_close = new_batch_time.find(')', first_open)
                        if first_close != -1:
                            second_open = new_batch_time.find('(', first_close + 1)
                            if second_open != -1:
                                second_close = new_batch_time.find(')', second_open)
                                if second_close != -1:
                                    date_section = new_batch_time[second_open + 1:second_close]
                                    print(f"Debug: Date section extracted: {date_section}")
                                    
                                    # Check if this is a date format (contains numbers and dashes)
                                    if any(char.isdigit() for char in date_section) and '-' in date_section:
                                        new_batch_start_date = date_section.upper()
                                        print(f"Debug: Formatted date: {new_batch_start_date}")
                    except Exception as e:
                        print(f"Error parsing date from batch name: {e}")
                
                # If we still don't have a batch start date, try to get it from the batch record
                if new_batch_start_date == 'Unknown':
                    print("Debug: Trying to get date from batch record")
                    # Extract the base batch name (before the first parenthesis)
                    new_selected_batch_name = new_batch_time.split(' (')[0] if ' (' in new_batch_time else new_batch_time
                    print(f"Debug: Selected batch name: {new_selected_batch_name}")
                    
                    # Find the batch to get its start date
                    batches = get_all_batches()
                    for batch in batches:
                        if batch.get('batch_name') == new_selected_batch_name or batch.get('original_batch_name') == new_selected_batch_name:
                            new_batch_start_date = batch.get('batch_start_date', 'Unknown')
                            print(f"Debug: Found batch start date: {new_batch_start_date}")
                            # Convert date format from YYYY-MM-DD to DD-Mon-YYYY
                            if new_batch_start_date != 'Unknown' and new_batch_start_date:
                                try:
                                    date_obj = datetime.strptime(new_batch_start_date, '%Y-%m-%d')
                                    new_batch_start_date = date_obj.strftime('%d-%b-%Y').upper()
                                    print(f"Debug: Converted date: {new_batch_start_date}")
                                except Exception as e:
                                    print(f"Error parsing batch start date: {e}")
                            break
            # If batch_time or batch_start_date changed, regenerate student_id
            if (old_batch_time != new_batch_time) or (old_batch_start_date != new_batch_start_date):
                course_initials = student_data.get('course_initials')
                phone_number = student_data.get('student_number')
                if course_initials and phone_number:
                    # Use the simple student ID format: INITIALS PHONE_NUMBER
                    generated_id = generate_student_id_simple(course_initials, phone_number)
                    if generated_id is not None:
                        student_data['student_id'] = generated_id
                    else:
                        # If simple ID exists, keep the old complex format but with proper fallback
                        if batch_start_time == 'Unknown' or batch_end_time == 'Unknown':
                            # Try to get times from the batch record instead
                            batches = get_all_batches()
                            new_selected_batch_name = new_batch_time.split(' (')[0] if new_batch_time and ' (' in new_batch_time else new_batch_time
                            for batch in batches:
                                if batch.get('batch_name') == new_selected_batch_name or batch.get('original_batch_name') == new_selected_batch_name:
                                    batch_start_time = batch.get('start_time', batch_start_time)
                                    batch_end_time = batch.get('end_time', batch_end_time)
                                    break
                        
                        generated_id = generate_student_id(course_initials, batch_start_time, batch_end_time, new_batch_start_date)
                        student_data['student_id'] = generated_id
            # Remove the student_id from update data to keep original ID if not changed
            elif 'student_id' in student_data:
                del student_data['student_id']
            result = update_student(student_id, student_data)
            if result["success"]:
                flash("Student updated successfully!", "success")
            else:
                flash(result["error"], "danger")
                
        elif action == "delete_student":
            student_id = request.form["student_id_hidden"]
            if delete_student(student_id):
                flash("Student deleted successfully!", "warning")
            else:
                flash("Error deleting student!", "danger")
        
        elif action == "send_email":
            student_id = request.form["student_id_hidden"]
            student = get_student_by_id(student_id)
            if student and student.get('email'):
                if send_student_email(student['email'], student):
                    flash(f"Email sent successfully to {student['email']}!", "success")
                else:
                    flash("Error sending email. Please check email configuration.", "danger")
            else:
                flash("Student not found or email not provided!", "danger")
    
    batches = get_all_batches()
    all_students = get_all_students()
    
    # Determine which students to display
    if search_query:
        student = next((s for s in all_students if s.get('student_id') == search_query), None)
        if student:
            filtered_students = [student]
            flash(f"Showing result for student ID: {search_query}", "info")
        else:
            filtered_students = []
            flash(f"No student found with ID: {search_query}", "danger")
    else:
        # Apply filters if they exist
        filtered_students = all_students
        if selected_batch:
            filtered_students = [s for s in filtered_students if s.get('batch_time') == selected_batch]
        if selected_status:
            filtered_students = [s for s in filtered_students if s.get('fees_status') == selected_status]
    
    return render_template("student_details.html", students=filtered_students, batches=batches, selected_batch=selected_batch, selected_status=selected_status)

@techzone_app.route("/batch-management", methods=["GET", "POST"])
def batch_management():
    if not session.get("logged_in") or session.get("role") != "Admin":
        return redirect(url_for("login"))
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "add_batch":
            batch_data = {
                "batch_name": request.form["batch_name"],
                "start_time": request.form["start_time"],
                "end_time": request.form["end_time"],
                "batch_start_date": request.form["batch_start_date"],
                "description": request.form.get("description", "")
            }
            if add_batch(batch_data):
                flash("Batch added successfully!", "success")
            else:
                flash("Error adding batch!", "danger")
                
        elif action == "update_batch":
            batch_id = request.form["batch_id"]
            batch_data = {
                "batch_name": request.form["batch_name"],
                "start_time": request.form["start_time"],
                "end_time": request.form["end_time"],
                "batch_start_date": request.form["batch_start_date"],
                "description": request.form.get("description", "")
            }
            if update_batch(batch_id, batch_data):
                flash("Batch updated successfully!", "success")
            else:
                flash("Error updating batch!", "danger")
                
        elif action == "delete_batch":
            batch_id = request.form["batch_id"]
            if delete_batch(batch_id):
                flash("Batch deleted successfully!", "warning")
            else:
                flash("Error deleting batch!", "danger")
    
    batches = get_all_batches()
    return render_template("batch_management.html", batches=batches)

@techzone_app.route("/print-student/<student_id>")
def print_student(student_id):
    if not session.get("logged_in") or session.get("role") != "Admin":
        return redirect(url_for("login"))
    
    try:
        student = get_student_by_id(student_id)
        if student:
            if not student.get('created_at'):
                student['created_at'] = 'Not recorded'
            if not student.get('due_fees'):
                student['due_fees'] = student.get('total_fees', 0) - student.get('fees_paid', 0)
            
            return render_template("print_student.html", student=student)
        else:
            flash("Student not found!", "danger")
            return redirect(url_for("student_details"))
    except Exception as e:
        print(f"Error in print_student: {e}")
        flash("Error retrieving student details for printing!", "danger")
        return redirect(url_for("student_details"))

@techzone_app.route("/student-feedback", methods=["GET", "POST"])
def student_feedback():
    if not session.get("logged_in") or session.get("role") != "Admin":
        return redirect(url_for("login"))
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "delete_feedback":
            feedback_id = request.form.get("feedback_id")
            if feedback_id:
                if delete_student_feedback(feedback_id):
                    flash("Feedback deleted successfully!", "warning")
                else:
                    flash("Error deleting feedback!", "danger")
            else:
                flash("Feedback ID is required!", "danger")
        
        elif action == "delete_all_feedback":
            if delete_all_student_feedback():
                flash("All feedback deleted successfully!", "warning")
            else:
                flash("Error deleting all feedback!", "danger")
        
        return redirect(url_for("student_feedback"))
    
    feedbacks = get_all_student_feedback()
    students = get_all_students()
    student_lookup = {student['_id']: student for student in students}
    
    enriched_feedbacks = []
    for feedback in feedbacks:
        student_id = feedback.get('student_id')
        student_info = student_lookup.get(student_id, {})
        
        enriched_feedback = {
            'feedback_id': feedback['_id'],
            'student_id': student_id,
            'student_record_id': feedback.get('student_record_id', student_info.get('student_id', 'Unknown')),
            'student_name': feedback.get('student_name', student_info.get('student_name', 'Unknown')),
            'student_number': feedback.get('student_number', student_info.get('student_number', 'Unknown')),
            'batch_name': feedback.get('batch_name', student_info.get('batch_time', 'Unknown')),
            'feedback_text': feedback.get('feedback_text', ''),
            'submitted_by': feedback.get('submitted_by', 'Unknown'),
            'created_at': feedback.get('created_at', 'Unknown')
        }
        enriched_feedbacks.append(enriched_feedback)
    
    return render_template("student_feedback.html", feedbacks=enriched_feedbacks)

@techzone_app.route("/admin-management", methods=["GET", "POST"])
def admin_management():
    if not session.get("logged_in") or session.get("role") != "Super Admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_admin":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            if not username or not password:
                flash("Username and password are required!", "danger")
                return redirect(url_for("admin_management"))
            admin_data = {
                "username": username,
                "password": password,
                "name": username,
                "email": ""
            }
            if add_admin(admin_data):
                flash("Admin added successfully!", "success")
            else:
                flash("Error adding admin or username already exists!", "danger")
        elif action == "update_admin":
            admin_id = request.form.get("admin_id_hidden")
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            if not admin_id or not username:
                flash("Admin ID and username are required!", "danger")
                return redirect(url_for("admin_management"))
            admin_data = {
                "username": username,
                "name": username,
                "email": ""
            }
            if password:
                admin_data["password"] = password
            if update_admin(admin_id, admin_data):
                flash("Admin updated successfully!", "success")
            else:
                flash("Error updating admin!", "danger")
        elif action == "delete_admin":
            admin_id = request.form.get("admin_id_hidden")
            if not admin_id:
                flash("Admin ID is required!", "danger")
                return redirect(url_for("admin_management"))
            if delete_admin(admin_id):
                flash("Admin deleted successfully!", "warning")
            else:
                flash("Error deleting admin!", "danger")
    admins = get_all_admins()
    return render_template("admin_management.html", admins=admins)

@techzone_app.route('/send_trainer_message', methods=['POST'])
def send_trainer_message():
    if not session.get('logged_in') or session.get('role') != 'Trainer':
        return redirect(url_for('login'))

    batch_id = request.form.get('batch_id')
    message_content = request.form.get('message_content')
    trainer_name = session.get('username')

    if not batch_id or not message_content:
        flash('Batch and message are required!', 'danger')
        return redirect(url_for('dashboard'))

    if send_message(batch_id, trainer_name, message_content):
        flash('Message sent successfully!', 'success')
    else:
        flash('Failed to send message.', 'danger')

    return redirect(url_for('dashboard', batch_id=batch_id))

@techzone_app.route('/mark_as_read', methods=['POST'])
def mark_as_read():
    if 'user' not in session or session.get('role') != 'student':
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    student_id = session['user']
    student_doc = students_collection.document(student_id).get()
    if not student_doc.exists:
         # If student_id is not a doc id, it might be the username
        docs = students_collection.where(filter=('student_id', '==', student_id)).limit(1).stream()
        student_doc = next(docs, None)
        if not student_doc:
            return jsonify({'success': False, 'message': 'Student not found.'}), 404

    student_data = student_doc.to_dict()
    batch_id = student_data.get('batch_id')

    if not batch_id:
        return jsonify({'success': False, 'message': 'Student not in any batch.'}), 400

    if mark_messages_as_read(student_id, batch_id):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Failed to mark messages as read.'}), 500

@techzone_app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@techzone_app.route('/send-otp', methods=['POST'])
def send_otp():
    email = request.form.get('email')
    print('SEND OTP email:', email)
    if not email:
        return jsonify({'success': False, 'message': 'Email is required.'}), 400
    # Email format validation
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
    if not re.match(email_regex, email):
        return jsonify({'success': False, 'message': 'Invalid email format.'}), 400
    otp = str(random.randint(100000, 999999))
    session['student_email_otp'] = otp
    session['student_email_otp_email'] = email
    print('SEND OTP SESSION:', dict(session))
    # Send OTP email
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['email']
        msg['To'] = email
        msg['Subject'] = 'Your OTP for Student Registration'
        body = f"Your OTP for student registration is: <b>{otp}</b><br><br>If you did not request this, please ignore this email."
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        server.sendmail(EMAIL_CONFIG['email'], email, msg.as_string())
        server.quit()
        return jsonify({'success': True, 'message': 'OTP sent successfully.'})
    except Exception as e:
        print(f"Error sending OTP: {e}")
        return jsonify({'success': False, 'message': f'Failed to send OTP. {str(e)}'}), 500

@techzone_app.route('/verify-otp', methods=['POST'])
def verify_otp():
    email = request.form.get('email')
    otp = request.form.get('otp')
    print('VERIFY OTP email:', email, 'otp:', otp)
    print('VERIFY OTP SESSION:', dict(session))
    if (
        'student_email_otp' in session and
        'student_email_otp_email' in session and
        session['student_email_otp_email'] == email and
        session['student_email_otp'] == otp
    ):
        session['student_email_otp_verified'] = True
        return jsonify({'success': True, 'message': 'OTP verified.'})
    else:
        return jsonify({'success': False, 'message': 'Invalid OTP.'}), 400

if __name__ == "__main__":
    techzone_app.run(debug=True)
