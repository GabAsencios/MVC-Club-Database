import streamlit as st
import mysql.connector
import pandas as pd
from contextlib import contextmanager
from datetime import date
import plotly.graph_objects as go
import plotly.express as px

import tempfile
import os
from dotenv import load_dotenv

# ── Config ──────────────────────────────────────────────────────────────────
st.set_page_config(page_title="MVC Club Manager", layout="wide", page_icon="🏐")


load_dotenv()

def get_secret(name, default=None):
    value = os.getenv(name)
    if value:
        return value

    try:
        return st.secrets.get(name, default)
    except Exception:
        return default

ssl_ca_path = get_secret("DB_SSL_CA")

# For Streamlit Cloud: write the Aiven CA certificate from secrets to a temp file
try:
    ca_content = st.secrets.get("DB_SSL_CA_CONTENT", None)
    if ca_content:
        cert_path = os.path.join(tempfile.gettempdir(), "aiven-ca.pem")
        with open(cert_path, "w", encoding="utf-8") as f:
            f.write(ca_content)
        ssl_ca_path = cert_path
except Exception:
    pass

DB_CONFIG = {
    "host": get_secret("DB_HOST"),
    "port": int(get_secret("DB_PORT", "3306")),
    "user": get_secret("DB_USER"),
    "password": get_secret("DB_PASSWORD"),
    "database": get_secret("DB_NAME"),
}

if ssl_ca_path:
    DB_CONFIG.update({
        "ssl_ca": ssl_ca_path,
        "ssl_verify_cert": True,
        "ssl_verify_identity": True,
    })

# ── DB helpers ───────────────────────────────────────────────────────────────
@contextmanager
def get_conn():
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

def query_df(sql, params=None):
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params=params)

def execute(sql, params=None):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        conn.commit()

def fetch_one(sql, params=None):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or [])
        return cur.fetchone()

def fetch_options(sql):
    """Returns list of (id, label) tuples for selectboxes."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        return cur.fetchall()

# ── Sidebar nav ──────────────────────────────────────────────────────────────
st.sidebar.title("🏐 MVC Club")
section = st.sidebar.radio("Navigate", [
    "Dashboard",
    "Members",
    "Personnel",
    "Teams",
    "Sessions & Formations",
    "Payments",
    "Locations",
    "Family Members",
    "Email Log",
])

st.sidebar.markdown("---")
st.sidebar.caption("Update DB_CONFIG at the top of this file with your credentials.")

# ── Global CSS Styling ──────────────────────────────────────────────────────
st.markdown("""
    <style>
    .page-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px;
        border-radius: 10px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .page-header h1 {
        margin: 0;
        font-size: 2.2em;
        font-weight: bold;
    }
    .page-header p {
        margin: 8px 0 0 0;
        opacity: 0.9;
        font-size: 0.95em;
    }
    .section-title {
        color: #white;
        font-size: 1.4em;
        font-weight: bold;
        padding: 10px 0;
        border-bottom: 3px solid #667eea;
        margin: 20px 0 15px 0;
    }
    .info-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 10px 0;
    }
    .tab-title {
        font-size: 1.2em;
        font-weight: 600;
        color: #white;
        margin-top: 15px;
    }
    </style>
""", unsafe_allow_html=True)

def render_page_header(title, subtitle):
    """Helper function to render consistent page headers"""
    st.markdown(f"""
        <div class="page-header">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
if section == "Dashboard":
    render_page_header("🏐 MVC Club Dashboard", "Club Management & Analytics Overview")

    try:
        # ── Top Metrics Row ──────────────────────────────────────────────────
        st.markdown('<div class="section-title">Key Metrics</div>', unsafe_allow_html=True)
        
        m1, m2, m3, m4, m5 = st.columns(5, gap="small")
        
        total_members = query_df("SELECT COUNT(*) n FROM ClubMember").iloc[0,0]
        personnel = query_df("SELECT COUNT(*) n FROM Personnel").iloc[0,0]
        teams = query_df("SELECT COUNT(*) n FROM Team").iloc[0,0]
        locations = query_df("SELECT COUNT(*) n FROM Location").iloc[0,0]
        sessions = query_df("SELECT COUNT(*) n FROM Session WHERE SessionDate >= CURDATE()").iloc[0,0]
        
        m1.metric("👥 Members", total_members, help="Total club members")
        m2.metric("👔 Personnel", personnel, help="Coaches, admins, staff")
        m3.metric("🏆 Teams", teams, help="Active teams")
        m4.metric("📍 Locations", locations, help="Club locations")
        m5.metric("📅 Sessions", sessions, help="Upcoming events")

        # ── Payment & Revenue Metrics ────────────────────────────────────────
        st.markdown('<div class="section-title">Payment & Revenue</div>', unsafe_allow_html=True)
        
        m6, m7, m8, m9 = st.columns(4, gap="small")
        
        paid_members = query_df("SELECT COUNT(*) n FROM ClubMember WHERE PaymentStatus = 1").iloc[0,0]
        unpaid_members = total_members - paid_members
        minors = query_df("SELECT COUNT(*) n FROM ClubMember WHERE isMinor = 1").iloc[0,0]
        
        m6.metric("✅ Paid", paid_members)
        m7.metric("❌ Unpaid", unpaid_members)
        
        # Calculate total collected and estimated missing
        total_collected = query_df("SELECT COALESCE(SUM(Amount), 0) n FROM Payment").iloc[0,0]
        estimated_missing = (unpaid_members / total_members * total_collected) if total_members > 0 else 0
        
        m8.metric("💰 Total Collected", f"${total_collected:,.2f}")
        m9.metric("📊 Missing Payments", f"${estimated_missing:,.2f}")

        # ── Payment Status Progress Bar ──────────────────────────────────────
        st.markdown('<div class="section-title">Payment Progress</div>', unsafe_allow_html=True)
        
        payment_percentage = (paid_members / total_members * 100) if total_members > 0 else 0
        col_prog = st.columns([4, 1])
        
        with col_prog[0]:
            st.progress(payment_percentage / 100, text=f"{payment_percentage:.1f}% Members Paid")
        
        with col_prog[1]:
            st.metric("", f"{paid_members}/{total_members}")

        st.markdown("---")

        # ── Charts Section ───────────────────────────────────────────────────
        st.markdown('<div class="section-title">Analytics & Distribution</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2, gap="medium")

        # Paid vs Unpaid - Pie Chart
        with col1:
            st.markdown("**Payment Status Distribution**")
            pay = query_df("SELECT PaymentStatus, COUNT(*) AS Count FROM ClubMember GROUP BY PaymentStatus")
            pay["PaymentStatus"] = pay["PaymentStatus"].map({1: "Paid", 0: "Unpaid"})
            
            fig_pay = px.pie(pay, values="Count", names="PaymentStatus", 
                            color_discrete_map={"Paid": "#2ecc71", "Unpaid": "#e74c3c"},
                            hole=0.4)
            fig_pay.update_layout(height=350, showlegend=True, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig_pay, use_container_width=True)

        # Personnel by Role - Horizontal Bar
        with col2:
            st.markdown("**Personnel Distribution**")
            roles = query_df("SELECT Role, COUNT(*) AS Count FROM Personnel GROUP BY Role ORDER BY Count DESC")
            
            fig_roles = px.bar(roles, y="Role", x="Count", orientation="h",
                              color="Count", color_continuous_scale="viridis")
            fig_roles.update_layout(height=350, showlegend=False, margin=dict(l=0, r=0, t=20, b=0),
                                   xaxis_title="", yaxis_title="")
            st.plotly_chart(fig_roles, use_container_width=True)

        # ── Teams and Members ────────────────────────────────────────────────
        col3, col4 = st.columns(2, gap="medium")

        with col3:
            st.markdown("**Teams by Gender**")
            gender_teams = query_df("SELECT team_gender, COUNT(*) AS Count FROM Team GROUP BY team_gender")
            if not gender_teams.empty:
                gender_map = {"Male": "👨 Male Teams", "Female": "👩 Female Teams"}
                gender_teams["team_gender"] = gender_teams["team_gender"].map(gender_map)
                
                fig_gender = px.bar(gender_teams, x="team_gender", y="Count",
                                   color="team_gender", color_discrete_map={"👨 Male Teams": "#3498db", "👩 Female Teams": "#e91e63"},
                                   text="Count")
                fig_gender.update_layout(height=350, showlegend=False, margin=dict(l=0, r=0, t=20, b=0),
                                        xaxis_title="", yaxis_title="Teams")
                fig_gender.update_traces(textposition='auto')
                st.plotly_chart(fig_gender, use_container_width=True)
            else:
                st.info("No team data available")

        with col4:
            st.markdown("**Members by Location**")
            location_members = query_df("""
                SELECT l.name, COUNT(cm.ClubMemberID) AS Count
                FROM ClubMember cm
                LEFT JOIN Location l ON l.locationID = cm.locationID
                GROUP BY cm.locationID, l.name
                ORDER BY Count DESC
            """)
            if not location_members.empty:
                fig_loc = px.bar(location_members, x="name", y="Count",
                                color="Count", color_continuous_scale="blues",
                                text="Count")
                fig_loc.update_layout(height=350, showlegend=False, margin=dict(l=0, r=0, t=20, b=0),
                                     xaxis_title="", yaxis_title="Members")
                fig_loc.update_traces(textposition='auto')
                st.plotly_chart(fig_loc, use_container_width=True)
            else:
                st.info("No location data available")

        st.markdown("---")

        # ── Upcoming Sessions ────────────────────────────────────────────────
        st.markdown('<div class="section-title">Upcoming Sessions</div>', unsafe_allow_html=True)
        
        upcoming = query_df(
            "SELECT SessionID, SessionDate, SessionTime, SessionType, Address "
            "FROM Session WHERE SessionDate >= CURDATE() ORDER BY SessionDate LIMIT 10"
        )
        if not upcoming.empty:
            upcoming["SessionDate"] = pd.to_datetime(upcoming["SessionDate"]).dt.strftime("%Y-%m-%d")
            upcoming["SessionTime"] = upcoming["SessionTime"].astype(str)
            upcoming["Type"] = upcoming["SessionType"].map({"Training": "🏋️ Training", "Game": "⚽ Game"})
            display_upcoming = upcoming[["SessionID", "SessionDate", "SessionTime", "Type", "Address"]]
            display_upcoming.columns = ["Session ID", "Date", "Time", "Type", "Location"]
            st.dataframe(display_upcoming, use_container_width=True, hide_index=True)
        else:
            st.info("No upcoming sessions scheduled")

        st.markdown("---")

        # ── Recent Payments & Payment Methods ─────────────────────────────────
        st.markdown('<div class="section-title">Payments Overview</div>', unsafe_allow_html=True)
        
        col5, col6 = st.columns(2, gap="medium")

        with col5:
            st.markdown("**Recent Payments**")
            recent_payments = query_df("""
                SELECT p.PaymentID, p.PaymentDate, p.Amount, p.Method, 
                       CONCAT(pr.FirstName, ' ', pr.LastName) AS MemberName
                FROM Payment p
                JOIN ClubMember cm ON p.ClubMemberID = cm.ClubMemberID
                JOIN Person pr ON cm.ClubMemberID = pr.PersonID
                ORDER BY p.PaymentDate DESC LIMIT 5
            """)
            if not recent_payments.empty:
                recent_payments["PaymentDate"] = pd.to_datetime(recent_payments["PaymentDate"]).dt.strftime("%m/%d")
                recent_payments["Amount"] = recent_payments["Amount"].apply(lambda x: f"${x:.2f}")
                display_recent = recent_payments[["PaymentDate", "MemberName", "Amount", "Method"]]
                display_recent.columns = ["Date", "Member", "Amount", "Method"]
                st.dataframe(display_recent, use_container_width=True, hide_index=True)
            else:
                st.info("No payment records found")

        with col6:
            st.markdown("**Payment Methods**")
            payment_methods = query_df("SELECT Method, COUNT(*) AS Count FROM Payment GROUP BY Method")
            if not payment_methods.empty:
                fig_methods = px.pie(payment_methods, values="Count", names="Method",
                                    color_discrete_sequence=["#9b59b6", "#3498db", "#f39c12"])
                fig_methods.update_layout(height=350, showlegend=True, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig_methods, use_container_width=True)
            else:
                st.info("No payment data available")

        st.markdown("---")

        # ── Quick Stats Summary ──────────────────────────────────────────────
        st.markdown('<div class="section-title">Team Breakdown</div>', unsafe_allow_html=True)
        
        col7, col8, col9, col10 = st.columns(4, gap="small")

        coaches = query_df("SELECT COUNT(*) n FROM Personnel WHERE Role IN ('Coach', 'Head Coach', 'Assistant Coach')").iloc[0,0]
        admins = query_df("SELECT COUNT(*) n FROM Personnel WHERE Role = 'Administrator'").iloc[0,0]
        adults = total_members - minors
        this_year_revenue = query_df("SELECT COALESCE(SUM(Amount), 0) n FROM Payment WHERE YEAR(PaymentDate) = YEAR(CURDATE())").iloc[0,0]

        col7.metric("🏋️ Coaches", coaches)
        col8.metric("👨‍💼 Admins", admins)
        col9.metric("👨 Adults", adults)
        col10.metric("💵 YTD Revenue", f"${this_year_revenue:.2f}")

    except Exception as e:
        st.error(f"❌ Database Connection Error: {e}")

# ════════════════════════════════════════════════════════════════════════════
# MEMBERS
# ════════════════════════════════════════════════════════════════════════════
elif section == "Members":
    render_page_header("👥 Club Members", "Manage member profiles, payments, and details")
    tab1, tab2, tab3 = st.tabs(["View", "Add", "Edit / Delete"])

    # ── View ────────────────────────────────────────────────────────────────
    with tab1:
        st.markdown('<div class="tab-title">Member Directory</div>', unsafe_allow_html=True)
        search = st.text_input("🔍 Search by name, email or city")
        sql = """
            SELECT cm.ClubMemberID, p.FirstName, p.LastName, p.DateOfBirth,
                   p.PhoneNo, p.Email, p.City, cm.Height, cm.Weight,
                   cm.isMinor, cm.PaymentStatus,
                   l.name AS Location
            FROM ClubMember cm
            JOIN Person p ON p.PersonID = cm.ClubMemberID
            LEFT JOIN Location l ON l.locationID = cm.locationID
        """
        df = query_df(sql)
        if search:
            mask = df.astype(str).apply(lambda c: c.str.contains(search, case=False)).any(axis=1)
            df = df[mask]
        df["PaymentStatus"] = df["PaymentStatus"].map({1: "Paid", 0: "Unpaid"})
        df["isMinor"]       = df["isMinor"].map({1: "Yes", 0: "No"})
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"📊 Total: {len(df)} members")

    # ── Add ─────────────────────────────────────────────────────────────────
    with tab2:
        st.markdown('<div class="tab-title">➕ Add New Member</div>', unsafe_allow_html=True)
        locations = fetch_options("SELECT locationID, name FROM Location")
        loc_map   = {name: lid for lid, name in locations}

        with st.form("add_member"):
            c1, c2 = st.columns(2)
            fname   = c1.text_input("First Name *")
            lname   = c2.text_input("Last Name")
            dob     = c1.date_input("Date of Birth *", min_value=date(1900,1,1))
            ssn     = c2.text_input("SSN *")
            medicare= c1.text_input("Medicare No")
            phone   = c2.text_input("Phone")
            email   = c1.text_input("Email")
            address = c2.text_input("Address")
            city    = c1.text_input("City")
            province= c2.text_input("Province")
            postal  = c1.text_input("Postal Code")
            height  = c2.number_input("Height (cm)", 0.0, 300.0, step=0.5)
            weight  = c1.number_input("Weight (kg)", 0.0, 300.0, step=0.5)
            is_minor= c2.checkbox("Is Minor?")
            paid    = c1.checkbox("Payment Status (paid)?")
            loc_name= c2.selectbox("Location", [n for _, n in locations])

            if st.form_submit_button("Add Member"):
                if not fname or not ssn:
                    st.error("First Name and SSN are required.")
                else:
                    try:
                        execute("""
                            INSERT INTO Person
                              (FirstName,LastName,DateOfBirth,SSN,MedicareNo,PhoneNo,Address,City,Province,PostalCode,Email)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, [fname, lname, dob, ssn, medicare or None, phone, address, city, province, postal, email])
                        new_id = fetch_one("SELECT PersonID FROM Person WHERE SSN=%s", [ssn])["PersonID"]
                        execute("""
                            INSERT INTO ClubMember (ClubMemberID,Height,Weight,isMinor,locationID,PaymentStatus)
                            VALUES (%s,%s,%s,%s,%s,%s)
                        """, [new_id, height or None, weight or None, is_minor, loc_map.get(loc_name), int(paid)])
                        st.success(f"✅ Member added (ID {new_id}).")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ── Edit / Delete ────────────────────────────────────────────────────────
    with tab3:
        st.markdown('<div class="tab-title">Edit / Delete Member</div>', unsafe_allow_html=True)
        members = fetch_options(
            "SELECT cm.ClubMemberID, CONCAT(p.FirstName,' ',p.LastName) "
            "FROM ClubMember cm JOIN Person p ON p.PersonID=cm.ClubMemberID ORDER BY p.LastName"
        )
        if not members:
            st.info("No members found.")
        else:
            mem_map = {label: mid for mid, label in members}
            chosen  = st.selectbox("Select member", list(mem_map.keys()))
            mid     = mem_map[chosen]

            row_p  = fetch_one("SELECT * FROM Person WHERE PersonID=%s", [mid])
            row_cm = fetch_one("SELECT * FROM ClubMember WHERE ClubMemberID=%s", [mid])
            locations = fetch_options("SELECT locationID, name FROM Location")
            loc_map   = {name: lid for lid, name in locations}
            loc_names = [n for _, n in locations]

            with st.form("edit_member"):
                c1, c2 = st.columns(2)
                fname   = c1.text_input("First Name", row_p["FirstName"])
                lname   = c2.text_input("Last Name",  row_p["LastName"] or "")
                phone   = c1.text_input("Phone",      row_p["PhoneNo"] or "")
                email   = c2.text_input("Email",      row_p["Email"] or "")
                city    = c1.text_input("City",       row_p["City"] or "")
                province= c2.text_input("Province",   row_p["Province"] or "")
                height  = c1.number_input("Height", 0.0, 300.0, float(row_cm["Height"] or 0), step=0.5)
                weight  = c2.number_input("Weight", 0.0, 300.0, float(row_cm["Weight"] or 0), step=0.5)
                paid    = c1.checkbox("Paid?", bool(row_cm["PaymentStatus"]))
                is_minor= c2.checkbox("Minor?", bool(row_cm["isMinor"]))
                cur_loc = next((n for lid, n in locations if lid == row_cm["locationID"]), loc_names[0] if loc_names else None)
                loc_name= st.selectbox("Location", loc_names, index=loc_names.index(cur_loc) if cur_loc in loc_names else 0)

                if st.form_submit_button("Save Changes"):
                    try:
                        execute("UPDATE Person SET FirstName=%s,LastName=%s,PhoneNo=%s,Email=%s,City=%s,Province=%s WHERE PersonID=%s",
                                [fname, lname, phone, email, city, province, mid])
                        execute("UPDATE ClubMember SET Height=%s,Weight=%s,isMinor=%s,locationID=%s,PaymentStatus=%s WHERE ClubMemberID=%s",
                                [height or None, weight or None, int(is_minor), loc_map.get(loc_name), int(paid), mid])
                        st.success("✅ Member updated.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            st.markdown("---")
            st.warning(f"Deleting **{chosen}** will also remove their Person record (cascade).")
            if st.button("🗑 Delete Member", type="primary"):
                try:
                    execute("DELETE FROM Person WHERE PersonID=%s", [mid])
                    st.success("✅ Deleted.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# ════════════════════════════════════════════════════════════════════════════
# PERSONNEL
# ════════════════════════════════════════════════════════════════════════════
elif section == "Personnel":
    render_page_header("👔 Personnel Management", "Manage coaches, administrators, and staff")
    tab1, tab2, tab3 = st.tabs(["View", "Add", "Edit / Delete"])

    ROLES    = ['Administrator', 'Captain', 'Coach', 'Assistant Coach', 'Head Coach']
    MANDATES = ['Volunteer', 'Salaried']

    with tab1:
        st.markdown('<div class="tab-title">Personnel Directory</div>', unsafe_allow_html=True)
        df = query_df("""
            SELECT per.PersonnelID, p.FirstName, p.LastName, per.Role, per.Mandate,
                   p.PhoneNo, p.Email, p.City
            FROM Personnel per JOIN Person p ON p.PersonID=per.PersonnelID
            ORDER BY p.LastName
        """)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"📊 Total: {len(df)} personnel")

    with tab2:
        st.markdown('<div class="tab-title">➕ Add Personnel</div>', unsafe_allow_html=True)
        with st.form("add_personnel"):
            c1, c2 = st.columns(2)
            fname    = c1.text_input("First Name *")
            lname    = c2.text_input("Last Name")
            dob      = c1.date_input("Date of Birth *", min_value=date(1900,1,1))
            ssn      = c2.text_input("SSN *")
            medicare = c1.text_input("Medicare No")
            phone    = c2.text_input("Phone")
            email    = c1.text_input("Email")
            address  = c2.text_input("Address")
            city     = c1.text_input("City")
            province = c2.text_input("Province")
            postal   = c1.text_input("Postal Code")
            role     = c2.selectbox("Role", ROLES)
            mandate  = c1.selectbox("Mandate", MANDATES)

            if st.form_submit_button("Add Personnel"):
                if not fname or not ssn:
                    st.error("First Name and SSN required.")
                else:
                    try:
                        execute("""
                            INSERT INTO Person
                              (FirstName,LastName,DateOfBirth,SSN,MedicareNo,PhoneNo,Address,City,Province,PostalCode,Email)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, [fname, lname, dob, ssn, medicare or None, phone, address, city, province, postal, email])
                        new_id = fetch_one("SELECT PersonID FROM Person WHERE SSN=%s", [ssn])["PersonID"]
                        execute("INSERT INTO Personnel (PersonnelID,Role,Mandate) VALUES (%s,%s,%s)", [new_id, role, mandate])
                        st.success(f"✅ Personnel added (ID {new_id}).")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tab3:
        st.markdown('<div class="tab-title">Edit / Delete Personnel</div>', unsafe_allow_html=True)
        personnel = fetch_options(
            "SELECT per.PersonnelID, CONCAT(p.FirstName,' ',p.LastName,' — ',per.Role) "
            "FROM Personnel per JOIN Person p ON p.PersonID=per.PersonnelID ORDER BY p.LastName"
        )
        if not personnel:
            st.info("No personnel found.")
        else:
            per_map = {label: pid for pid, label in personnel}
            chosen  = st.selectbox("Select personnel", list(per_map.keys()))
            pid     = per_map[chosen]
            row_per = fetch_one("SELECT * FROM Personnel WHERE PersonnelID=%s", [pid])
            row_p   = fetch_one("SELECT * FROM Person WHERE PersonID=%s", [pid])

            with st.form("edit_personnel"):
                c1, c2 = st.columns(2)
                fname   = c1.text_input("First Name", row_p["FirstName"])
                lname   = c2.text_input("Last Name",  row_p["LastName"] or "")
                phone   = c1.text_input("Phone",      row_p["PhoneNo"] or "")
                email   = c2.text_input("Email",      row_p["Email"] or "")
                role    = c1.selectbox("Role",    ROLES,    index=ROLES.index(row_per["Role"]) if row_per["Role"] in ROLES else 0)
                mandate = c2.selectbox("Mandate", MANDATES, index=MANDATES.index(row_per["Mandate"]))

                if st.form_submit_button("Save Changes"):
                    try:
                        execute("UPDATE Person SET FirstName=%s,LastName=%s,PhoneNo=%s,Email=%s WHERE PersonID=%s",
                                [fname, lname, phone, email, pid])
                        execute("UPDATE Personnel SET Role=%s,Mandate=%s WHERE PersonnelID=%s", [role, mandate, pid])
                        st.success("✅ Updated.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            st.markdown("---")
            if st.button("🗑 Delete Personnel", type="primary"):
                try:
                    execute("DELETE FROM Person WHERE PersonID=%s", [pid])
                    st.success("✅ Deleted.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# ════════════════════════════════════════════════════════════════════════════
# TEAMS
# ════════════════════════════════════════════════════════════════════════════
elif section == "Teams":
    render_page_header("🏆 Team Management", "Manage team rosters and assignments")
    tab1, tab2, tab3 = st.tabs(["View", "Add", "Edit / Delete"])

    with tab1:
        st.markdown('<div class="tab-title">All Teams</div>', unsafe_allow_html=True)
        df = query_df("""
            SELECT t.teamID, t.teamName, t.team_gender,
                   l.name AS Location,
                   CONCAT(p.FirstName,' ',p.LastName) AS HeadCoach
            FROM Team t
            LEFT JOIN Location l ON l.locationID=t.LocationID
            LEFT JOIN Personnel per ON per.PersonnelID=t.HeadCoachID
            LEFT JOIN Person p ON p.PersonID=per.PersonnelID
            ORDER BY t.teamName
        """)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"📊 Total: {len(df)} teams")

    with tab2:
        st.markdown('<div class="tab-title">➕ Add Team</div>', unsafe_allow_html=True)
        locations = fetch_options("SELECT locationID, name FROM Location")
        coaches   = fetch_options(
            "SELECT per.PersonnelID, CONCAT(p.FirstName,' ',p.LastName) "
            "FROM Personnel per JOIN Person p ON p.PersonID=per.PersonnelID "
            "WHERE per.Role IN ('Coach','Head Coach','Assistant Coach')"
        )
        loc_map    = {n: lid for lid, n in locations}
        coach_map  = {n: cid for cid, n in coaches}

        with st.form("add_team"):
            name    = st.text_input("Team Name *")
            gender  = st.selectbox("Gender", ["Male", "Female"])
            loc     = st.selectbox("Location", [n for _, n in locations])
            coach   = st.selectbox("Head Coach", [n for _, n in coaches])
            if st.form_submit_button("Add Team"):
                if not name:
                    st.error("Team name required.")
                else:
                    try:
                        execute("INSERT INTO Team (teamName,team_gender,LocationID,HeadCoachID) VALUES (%s,%s,%s,%s)",
                                [name, gender, loc_map[loc], coach_map[coach]])
                        st.success("✅ Team added.")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tab3:
        st.markdown('<div class="tab-title">Edit / Delete Team</div>', unsafe_allow_html=True)
        teams = fetch_options("SELECT teamID, teamName FROM Team ORDER BY teamName")
        if not teams:
            st.info("No teams found.")
        else:
            tm_map  = {n: tid for tid, n in teams}
            chosen  = st.selectbox("Select team", list(tm_map.keys()))
            tid     = tm_map[chosen]
            row     = fetch_one("SELECT * FROM Team WHERE teamID=%s", [tid])
            locations = fetch_options("SELECT locationID, name FROM Location")
            coaches   = fetch_options(
                "SELECT per.PersonnelID, CONCAT(p.FirstName,' ',p.LastName) "
                "FROM Personnel per JOIN Person p ON p.PersonID=per.PersonnelID"
            )
            loc_map   = {n: lid for lid, n in locations}
            loc_names = [n for _, n in locations]
            coach_map = {n: cid for cid, n in coaches}
            coach_names = [n for _, n in coaches]

            with st.form("edit_team"):
                name   = st.text_input("Team Name", row["teamName"])
                gender = st.selectbox("Gender", ["Male","Female"], index=0 if row["team_gender"]=="Male" else 1)
                cur_loc = next((n for lid, n in locations if lid == row["LocationID"]), loc_names[0])
                loc    = st.selectbox("Location", loc_names, index=loc_names.index(cur_loc) if cur_loc in loc_names else 0)
                cur_coach = next((n for cid, n in coaches if cid == row["HeadCoachID"]), coach_names[0])
                coach  = st.selectbox("Head Coach", coach_names, index=coach_names.index(cur_coach) if cur_coach in coach_names else 0)
                if st.form_submit_button("Save"):
                    try:
                        execute("UPDATE Team SET teamName=%s,team_gender=%s,LocationID=%s,HeadCoachID=%s WHERE teamID=%s",
                                [name, gender, loc_map[loc], coach_map[coach], tid])
                        st.success("✅ Updated.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            st.markdown("---")
            st.markdown('<div class="tab-title">👥 Team Roster</div>', unsafe_allow_html=True)
            roster = query_df("""
                SELECT mt.ClubMemberID, CONCAT(p.FirstName,' ',p.LastName) AS Name,
                       mt.startDate, mt.endDate
                FROM memberTeam mt JOIN Person p ON p.PersonID=mt.ClubMemberID
                WHERE mt.teamID=%s ORDER BY mt.startDate
            """, params=(tid,))
            if not roster.empty:
                st.dataframe(roster, use_container_width=True, hide_index=True)
            else:
                st.info("No roster members assigned")

            st.markdown("---")
            if st.button("🗑 Delete Team", type="primary"):
                try:
                    execute("DELETE FROM Team WHERE teamID=%s", [tid])
                    st.success("✅ Deleted.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# ════════════════════════════════════════════════════════════════════════════
# SESSIONS & FORMATIONS
# ════════════════════════════════════════════════════════════════════════════
elif section == "Sessions & Formations":
    render_page_header("📅 Sessions & Formations", "Schedule training sessions and game formations")
    tab1, tab2 = st.tabs(["Sessions", "Formations"])

    with tab1:
        st.markdown('<div class="tab-title">All Sessions</div>', unsafe_allow_html=True)
        df = query_df("SELECT * FROM Session ORDER BY SessionDate DESC, SessionTime DESC")
        if not df.empty:
            df["SessionDate"] = pd.to_datetime(df["SessionDate"]).dt.strftime("%Y-%m-%d")
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"📊 Total: {len(df)} sessions")
        else:
            st.info("No sessions found")

        st.markdown("---")
        st.markdown('<div class="tab-title">➕ Add Session</div>', unsafe_allow_html=True)
        with st.form("add_session"):
            c1, c2 = st.columns(2)
            s_date = c1.date_input("Date *")
            s_time = c2.time_input("Time *")
            s_addr = c1.text_input("Address *")
            s_type = c2.selectbox("Type", ["Training", "Game"])
            if st.form_submit_button("Add Session"):
                try:
                    execute("INSERT INTO Session (SessionDate,SessionTime,Address,SessionType) VALUES (%s,%s,%s,%s)",
                            [s_date, str(s_time), s_addr, s_type])
                    st.success("✅ Session added.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    with tab2:
        st.markdown('<div class="tab-title">📊 Team Formations</div>', unsafe_allow_html=True)
        df = query_df("""
            SELECT tf.FormationID, s.SessionDate, s.SessionType,
                   t1.teamName AS Team1, t2.teamName AS Team2,
                   tf.Team1Score, tf.Team2Score
            FROM TeamFormation tf
            JOIN Session s ON s.SessionID=tf.SessionID
            JOIN Team t1 ON t1.teamID=tf.Team1ID
            JOIN Team t2 ON t2.teamID=tf.Team2ID
            ORDER BY s.SessionDate DESC
        """)
        if not df.empty:
            df["SessionDate"] = pd.to_datetime(df["SessionDate"]).dt.strftime("%Y-%m-%d")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No formations found")

        st.markdown("---")
        st.markdown('<div class="tab-title">✏️ Update Scores</div>', unsafe_allow_html=True)
        formations = fetch_options(
            "SELECT tf.FormationID, CONCAT(s.SessionDate,' | ',t1.teamName,' vs ',t2.teamName) "
            "FROM TeamFormation tf "
            "JOIN Session s ON s.SessionID=tf.SessionID "
            "JOIN Team t1 ON t1.teamID=tf.Team1ID "
            "JOIN Team t2 ON t2.teamID=tf.Team2ID "
            "ORDER BY s.SessionDate DESC"
        )
        if formations:
            fm_map  = {label: fid for fid, label in formations}
            chosen  = st.selectbox("Formation", list(fm_map.keys()))
            fid     = fm_map[chosen]
            c1, c2  = st.columns(2)
            score1  = c1.number_input("Team 1 Score", 0, step=1)
            score2  = c2.number_input("Team 2 Score", 0, step=1)
            if st.button("Save Scores"):
                try:
                    execute("UPDATE TeamFormation SET Team1Score=%s, Team2Score=%s WHERE FormationID=%s",
                            [score1, score2, fid])
                    st.success("✅ Scores updated.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# ════════════════════════════════════════════════════════════════════════════
# PAYMENTS
# ════════════════════════════════════════════════════════════════════════════
elif section == "Payments":
    render_page_header("💳 Payment Management", "Track and record member payments")
    tab1, tab2 = st.tabs(["View", "Record Payment"])

    with tab1:
        st.markdown('<div class="tab-title">Payment History</div>', unsafe_allow_html=True)
        df = query_df("""
            SELECT pay.PaymentID, CONCAT(p.FirstName,' ',p.LastName) AS Member,
                   pay.PaymentDate, pay.Amount, pay.Method,
                   pay.MembershipYear, pay.InstallmentNumber
            FROM Payment pay
            JOIN ClubMember cm ON cm.ClubMemberID=pay.ClubMemberID
            JOIN Person p ON p.PersonID=cm.ClubMemberID
            ORDER BY pay.PaymentDate DESC
        """)
        st.dataframe(df, use_container_width=True, hide_index=True)
        total = df["Amount"].sum() if not df.empty else 0
        col1, col2, col3 = st.columns(3)
        col1.metric("💵 Total Collected", f"${total:,.2f}")
        col2.metric("📊 Transactions", len(df))
        if not df.empty:
            avg = df["Amount"].mean()
            col3.metric("📈 Average Payment", f"${avg:.2f}")

    with tab2:
        st.markdown('<div class="tab-title">➕ Record Payment</div>', unsafe_allow_html=True)
        members = fetch_options(
            "SELECT cm.ClubMemberID, CONCAT(p.FirstName,' ',p.LastName) "
            "FROM ClubMember cm JOIN Person p ON p.PersonID=cm.ClubMemberID ORDER BY p.LastName"
        )
        mem_map = {n: mid for mid, n in members}
        with st.form("add_payment"):
            c1, c2 = st.columns(2)
            member  = c1.selectbox("Member *", list(mem_map.keys()))
            p_date  = c2.date_input("Payment Date *", value=date.today())
            amount  = c1.number_input("Amount ($) *", 0.0, step=10.0)
            method  = c2.selectbox("Method *", ["Cash", "Debit", "Credit"])
            year    = c1.number_input("Membership Year", 2020, 2035, value=date.today().year, step=1)
            install = c2.number_input("Installment (1-4)", 1, 4, step=1)
            if st.form_submit_button("Record Payment"):
                try:
                    mid = mem_map[member]
                    execute("""
                        INSERT INTO Payment (ClubMemberID,PaymentDate,Amount,Method,MembershipYear,InstallmentNumber)
                        VALUES (%s,%s,%s,%s,%s,%s)
                    """, [mid, p_date, amount, method, int(year), int(install)])
                    execute("UPDATE ClubMember SET PaymentStatus=TRUE WHERE ClubMemberID=%s", [mid])
                    st.success("✅ Payment recorded and member marked as paid.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# ════════════════════════════════════════════════════════════════════════════
# LOCATIONS
# ════════════════════════════════════════════════════════════════════════════
elif section == "Locations":
    render_page_header("📍 Location Management", "Manage club facilities and locations")
    tab1, tab2, tab3 = st.tabs(["View", "Add", "Edit"])

    with tab1:
        st.markdown('<div class="tab-title">🏢 All Locations</div>', unsafe_allow_html=True)
        df = query_df("SELECT * FROM Location ORDER BY Type, name")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"📊 Total: {len(df)} locations")

    with tab2:
        st.markdown('<div class="tab-title">➕ Add Location</div>', unsafe_allow_html=True)
        with st.form("add_location"):
            c1, c2 = st.columns(2)
            name     = c1.text_input("Name *")
            loc_type = c2.selectbox("Type", ["Head", "Branch"])
            address  = c1.text_input("Address *")
            city     = c2.text_input("City *")
            province = c1.text_input("Province")
            postal   = c2.text_input("Postal Code")
            phone    = c1.text_input("Phone")
            web      = c2.text_input("Web Address")
            capacity = c1.number_input("Capacity", 0, step=1)
            if st.form_submit_button("Add Location"):
                try:
                    execute("""
                        INSERT INTO Location (name,Type,Address,City,Province,PostalCode,PhoneNo,WebAddress,Capacity)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, [name, loc_type, address, city, province, postal, phone, web, int(capacity)])
                    st.success("✅ Location added.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    with tab3:
        st.markdown('<div class="tab-title">✏️ Edit Location</div>', unsafe_allow_html=True)
        locs = fetch_options("SELECT locationID, name FROM Location ORDER BY name")
        if locs:
            loc_map = {n: lid for lid, n in locs}
            chosen  = st.selectbox("Select location", list(loc_map.keys()))
            lid     = loc_map[chosen]
            row     = fetch_one("SELECT * FROM Location WHERE locationID=%s", [lid])
            with st.form("edit_location"):
                c1, c2   = st.columns(2)
                name     = c1.text_input("Name", row["name"] or "")
                capacity = c2.number_input("Capacity", 0, step=1, value=int(row["Capacity"] or 0))
                phone    = c1.text_input("Phone", row["PhoneNo"] or "")
                web      = c2.text_input("Web", row["WebAddress"] or "")
                if st.form_submit_button("Save"):
                    try:
                        execute("UPDATE Location SET name=%s,Capacity=%s,PhoneNo=%s,WebAddress=%s WHERE locationID=%s",
                                [name, capacity, phone, web, lid])
                        st.success("✅ Updated.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.info("No locations found")

# ════════════════════════════════════════════════════════════════════════════
# FAMILY MEMBERS
# ════════════════════════════════════════════════════════════════════════════
elif section == "Family Members":
    render_page_header("👨‍👩‍👧‍👦 Family Members", "Manage family relationships and connections")

    st.markdown('<div class="tab-title">Family Member Directory</div>', unsafe_allow_html=True)
    df = query_df("""
        SELECT fm.FamilyMemberID, p.FirstName, p.LastName, p.PhoneNo, p.Email,
               COUNT(mfh.ClubMemberID) AS LinkedMinors
        FROM FamilyMember fm
        JOIN Person p ON p.PersonID=fm.FamilyMemberID
        LEFT JOIN minorFamilyHistory mfh ON mfh.FamilyMemberID=fm.FamilyMemberID
        GROUP BY fm.FamilyMemberID, p.FirstName, p.LastName, p.PhoneNo, p.Email
        ORDER BY p.LastName
    """)
    st.dataframe(df, use_container_width=True, hide_index=True)
    if not df.empty:
        st.caption(f"📊 Total: {len(df)} family members")
    else:
        st.info("No family members found")

    st.markdown("---")
    st.markdown('<div class="tab-title">👥 Minor — Family Relationships</div>', unsafe_allow_html=True)
    df2 = query_df("""
        SELECT mfh.FamilyMemberID,
               CONCAT(pf.FirstName,' ',pf.LastName) AS FamilyMember,
               CONCAT(pm.FirstName,' ',pm.LastName) AS Minor,
               r.TypeName AS Relationship,
               mfh.startDate, mfh.endDate
        FROM minorFamilyHistory mfh
        JOIN Person pf ON pf.PersonID=mfh.FamilyMemberID
        JOIN Person pm ON pm.PersonID=mfh.ClubMemberID
        JOIN Relationship r ON r.relationshipTypeID=mfh.relationshipTypeID
        ORDER BY pf.LastName
    """)
    if not df2.empty:
        st.dataframe(df2, use_container_width=True, hide_index=True)
        st.caption(f"📊 Total: {len(df2)} relationships")
    else:
        st.info("No family relationships found")

# ════════════════════════════════════════════════════════════════════════════
# EMAIL LOG
# ════════════════════════════════════════════════════════════════════════════
elif section == "Email Log":
    render_page_header("📧 Email Log", "Track communication history")
    
    st.markdown('<div class="tab-title">Email History</div>', unsafe_allow_html=True)
    df = query_df("SELECT * FROM EmailLog ORDER BY LogID DESC")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"📊 Total: {len(df)} emails")
    else:
        st.info("No email logs found")

    st.markdown("---")
    st.markdown('<div class="tab-title">➕ Log an Email</div>', unsafe_allow_html=True)
    with st.form("add_email"):
        c1, c2 = st.columns(2)
        receiver = c1.text_input("Receiver Email *")
        sender   = c2.text_input("Sender Location *")
        subject  = st.text_input("Subject *")
        body     = st.text_area("Body Preview")
        if st.form_submit_button("Log Email"):
            try:
                execute("""
                    INSERT INTO EmailLog (EmailDate,SenderLocation,ReceiverEmail,Subject,BodyPreview)
                    VALUES (NOW(),%s,%s,%s,%s)
                """, [sender, receiver, subject, body])
                st.success("✅ Email logged.")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")