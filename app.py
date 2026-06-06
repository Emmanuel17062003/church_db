from flask import Flask, request, jsonify, render_template, redirect, url_for
import os
import psycopg as psycopg2  # type: ignore

app = Flask(__name__)

# Render will look for this variable securely from the dashboard screen
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    # Establishes a direct link to your Supabase Cloud Database
    return psycopg2.connect(DATABASE_URL)

# -------------------------------------------------------------
# 1. UI FRONTEND DASHBOARD ROUTE
# -------------------------------------------------------------
@app.route('/', methods=['GET'])
def index():
    search_query = request.args.get('search', '').strip()
    members = []
    total_count = 0
    active_count = 0
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Pull real-time cloud metrics
        cursor.execute("SELECT COUNT(*) FROM member;")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM member WHERE status = 'Active';")
        active_count = cursor.fetchone()[0]
        
        if search_query:
            sql_search = f"%{search_query}%"
            query = """
                SELECT member_id, first_name, last_name, phone_number, address_loc, created_at, status 
                FROM member 
                WHERE first_name ILIKE %s OR last_name ILIKE %s OR phone_number ILIKE %s
                ORDER BY member_id DESC;
            """
            cursor.execute(query, (sql_search, sql_search, sql_search))
        else:
            query = """
                SELECT member_id, first_name, last_name, phone_number, address_loc, created_at, status 
                FROM member 
                ORDER BY member_id DESC;
            """
            cursor.execute(query)
            
        members = cursor.fetchall()
        cursor.close()
        conn.close()
        
    except Exception as e:
        print("[❌] Cloud Dashboard Query Error: ", e)
        
    return render_template('index.html', members=members, total_count=total_count, 
                           active_count=active_count, search_query=search_query)


# -------------------------------------------------------------
# 2. AUTOMATED BACKEND FORM WEBHOOK BRIDGE ENDPOINT (Google Forms)
# -------------------------------------------------------------
@app.route('/add-member', methods=['POST'])
def add_member():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "Missing payload configuration"}), 400
    
    first_name   = data.get('first_name', '').strip()
    last_name    = data.get('last_name', '').strip()
    phone_number = data.get('phone_number', '').strip().replace(" ", "")
    address      = data.get('address_loc', '').strip()
    
    if not first_name or not phone_number:
        return jsonify({"status": "error", "message": "Required fields dropped"}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Cloud duplicate scanner
        check_query = "SELECT COUNT(*) FROM member WHERE phone_number = %s;"
        cursor.execute(check_query, (phone_number,))
        if cursor.fetchone()[0] > 0:
            cursor.close()
            conn.close()
            return jsonify({"status": "duplicate", "message": "Phone number variant logged"}), 409
            
        insert_query = """
            INSERT INTO member (first_name, last_name, phone_number, address_loc) 
            VALUES (%s, %s, %s, %s);
        """
        cursor.execute(insert_query, (first_name, last_name, phone_number, address))
        conn.commit()
        
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": "Member record saved"}), 200
        
    except Exception as e:
        print("[❌] Cloud Pipeline Webhook Error: ", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# -------------------------------------------------------------
# 3. MANUAL FORM ENTRY DIRECT VIA DASHBOARD
# -------------------------------------------------------------
@app.route('/add-member-manual', methods=['POST'])
def add_member_manual():
    first_name   = request.form.get('first_name', '').strip()
    last_name    = request.form.get('last_name', '').strip()
    phone_number = request.form.get('phone_number', '').strip().replace(" ", "")
    address      = request.form.get('address_loc', '').strip()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        check_query = "SELECT COUNT(*) FROM member WHERE phone_number = %s;"
        cursor.execute(check_query, (phone_number,))
        if cursor.fetchone()[0] > 0:
            cursor.close()
            conn.close()
            return "Error: This phone number is already registered!", 409
            
        insert_query = """
            INSERT INTO member (first_name, last_name, phone_number, address_loc) 
            VALUES (%s, %s, %s, %s);
        """
        cursor.execute(insert_query, (first_name, last_name, phone_number, address))
        conn.commit()
        
        print(f"[⚡] Manually Added via Cloud Dashboard: {first_name}")
        cursor.close()
        conn.close()
        
    except Exception as e:
        print("[❌] Cloud Dashboard Manual Entry Error: ", e)
        
    return redirect(url_for('index'))


if __name__ == '__main__':
    # Local fallback for development testing
    app.run(host='0.0.0.0', port=5000, debug=True)