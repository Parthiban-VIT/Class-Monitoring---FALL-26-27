import re
import html as html_lib

import bcrypt
import streamlit as st
import pandas as pd
from datetime import datetime
from supabase_db import supabase


st.set_page_config(
    page_title="VIT - SAS Class Monitoring",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


# =============================================================
# Global styling — makes the app look like a custom product
# instead of a default Streamlit app, and keeps it mobile friendly.
# =============================================================
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
}

#MainMenu, header, footer {visibility: hidden;}

.block-container {
    padding-top: 1.6rem;
    padding-bottom: 2rem;
    max-width: 1150px;
}

.stApp {
    background: linear-gradient(180deg, #f6f8fc 0%, #eef2f8 100%);
}

/* Buttons */
.stButton>button {
    border-radius: 10px;
    border: none;
    background: linear-gradient(135deg, #002B5C 0%, #01498f 100%);
    color: #ffffff;
    font-weight: 600;
    padding: 0.55rem 1.2rem;
    transition: all 0.15s ease-in-out;
    box-shadow: 0 2px 6px rgba(0,43,92,0.25);
}
.stButton>button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(0,43,92,0.3);
    color: #ffffff;
}

/* Inputs */
.stTextInput>div>div>input,
.stNumberInput>div>div>input,
.stTextArea textarea,
.stSelectbox>div>div,
.stDateInput>div>div>input {
    border-radius: 10px !important;
    border: 1px solid #dfe4ee !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #eef1f7;
    border-radius: 12px;
    padding: 14px 16px;
    box-shadow: 0 2px 6px rgba(0,43,92,0.05);
}
[data-testid="stMetricLabel"] { color:#5b6472; font-weight:600; }
[data-testid="stMetricValue"] { color:#002B5C; }

/* Radio buttons styled as pill selectors */
div[role="radiogroup"] {
    gap: 8px;
    flex-wrap: wrap;
}
div[role="radiogroup"] label {
    background: #ffffff;
    border: 1px solid #dfe4ee;
    border-radius: 999px;
    padding: 6px 16px;
    margin-right: 6px;
    cursor: pointer;
}
div[role="radiogroup"] label:hover {
    border-color:#002B5C;
}

/* Custom, mobile-friendly data table */
.table-wrapper {
    overflow-x: auto;
    border-radius: 12px;
    border: 1px solid #eef1f7;
    box-shadow: 0 2px 8px rgba(0,43,92,0.06);
    margin-bottom: 10px;
}
.custom-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
    background: #ffffff;
    min-width: 640px;
}
.custom-table thead th {
    background: #002B5C;
    color: #ffffff;
    text-align: left;
    padding: 10px 14px;
    font-weight: 600;
    white-space: nowrap;
    position: sticky;
    top: 0;
}
.custom-table tbody td {
    padding: 10px 14px;
    border-bottom: 1px solid #f0f2f7;
    color: #2d3542;
    white-space: nowrap;
}
.custom-table tbody tr:nth-child(even) { background: #f9fbfd; }
.custom-table tbody tr:hover { background: #eef4fb; }

.badge {
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    display: inline-block;
    white-space: nowrap;
}
.badge-green { background:#e6f7ee; color:#1a7f4e; }
.badge-red { background:#fdecec; color:#c62828; }

@media (max-width: 640px) {
    .block-container { padding-left: 0.6rem; padding-right: 0.6rem; }
    h1 { font-size: 22px !important; }
    h4 { font-size: 14px !important; }
    h5 { font-size: 12px !important; }
    .custom-table { font-size: 12px; }
    .custom-table thead th, .custom-table tbody td { padding: 8px 10px; }
}
</style>
"""


def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# -----------------------------
# Shared UI helpers
# -----------------------------
def page_header(title, subtitle=None, small=None, tag=None):
    st.markdown(
        f"""
        <h1 style='text-align:center;color:#002B5C;margin-bottom:0px;'>
            {title}
        </h1>
        {"<h4 style='text-align:center;color:#555;margin-top:5px;'>" + subtitle + "</h4>" if subtitle else ""}
        {"<h5 style='text-align:center;color:#666;margin-top:-10px;'>" + small + "</h5>" if small else ""}
        {"<p style='text-align:center;color:#777;font-size:16px;'>" + tag + "</p>" if tag else ""}
        <hr>
        """,
        unsafe_allow_html=True
    )


def card_start(title, icon=""):
    st.markdown(
        f"""
        <div style='background:#ffffff;border:1px solid #eaeaea;border-radius:14px;
                    padding:20px 24px;margin-bottom:20px;
                    box-shadow:0 2px 8px rgba(0,43,92,0.06);'>
            <div style='font-size:17px;font-weight:700;color:#002B5C;
                        margin-bottom:14px;letter-spacing:0.2px;'>
                {icon} {title}
            </div>
        """,
        unsafe_allow_html=True
    )


def card_end():
    st.markdown("</div>", unsafe_allow_html=True)


def footer():
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align:center;color:gray;font-size:13px;">
        Internal Academic Portal<br>
        <br><br>
        © Department of Mathematics
        </div>
        """,
        unsafe_allow_html=True
    )


def top_bar():
    """Shared welcome + logout bar used by both monitoring_page() and admin_page()."""
    top_left, top_right = st.columns([4, 1])
    with top_left:
        role_tag = st.session_state.get("role", "")
        st.markdown(
            f"<div style='color:#555;font-size:15px;margin-top:6px;'>"
            f"Signed in as <b style='color:#002B5C;'>Dr. {st.session_state.get('name','')}</b>"
            f"&nbsp;<span style='color:#999;'>({role_tag})</span>"
            f"</div>",
            unsafe_allow_html=True
        )
    with top_right:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    change_password_section()
    st.write("")


def hash_password(plain):
    """Hashes a plain-text password for storage."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def is_bcrypt_hash(value):
    value = str(value or "")
    return value.startswith("$2a$") or value.startswith("$2b$") or value.startswith("$2y$")


def verify_password(plain, stored):
    """Checks a plain-text password against a stored value.
    Supports both bcrypt hashes and legacy plain-text passwords, so
    existing accounts keep working until they're migrated on next login."""
    if stored is None:
        return False
    stored = str(stored)
    if is_bcrypt_hash(stored):
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
        except ValueError:
            return False
    # Legacy plain-text password
    return plain == stored


def change_password_section():
    """Lets a logged-in user change their own password."""
    with st.expander("🔑 Change Password"):
        current_pw = st.text_input("Current Password", type="password", key="cp_current")
        new_pw = st.text_input("New Password", type="password", key="cp_new")
        confirm_pw = st.text_input("Confirm New Password", type="password", key="cp_confirm")

        if st.button("Update Password", key="cp_submit"):
            emp_id = str(st.session_state.emp_id).strip()
            current_pw = current_pw.strip()
            new_pw = new_pw.strip()
            confirm_pw = confirm_pw.strip()

            response = (
                supabase.table("users")
                .select("*")
                .eq("employee_id", emp_id)
                .execute()
            )

            if not response.data:
                st.error("❌ Could not find your account.")
            elif not verify_password(current_pw, response.data[0].get("password")):
                st.error("❌ Current password is incorrect.")
            elif len(new_pw) < 6:
                st.error("❌ New password must be at least 6 characters long.")
            elif new_pw != confirm_pw:
                st.error("❌ New password and confirmation do not match.")
            elif new_pw == current_pw:
                st.error("❌ New password must be different from the current password.")
            else:
                supabase.table("users").update(
                    {"password": hash_password(new_pw)}
                ).eq("employee_id", emp_id).execute()
                st.success("✅ Password updated successfully. Use it next time you log in.")


def clean(value):
    if pd.isna(value):
        return ""
    if hasattr(value, "item"):
        value = value.item()
    return str(value)


def status_badge(is_on_time):
    if is_on_time:
        return '<span class="badge badge-green">&#10004; On Time</span>'
    return '<span class="badge badge-red">&#10008; Late</span>'


def recorded_badge(is_recorded):
    if is_recorded:
        return '<span class="badge badge-green">&#10004; Recorded</span>'
    return '<span class="badge badge-red">&#10008; Not Recorded</span>'


def split_delay_comment(row):
    """Splits the combined comments field into a Delay column and a Comments column."""
    on_time = bool(row.get("on_time"))
    comments = str(row.get("comments") or "").strip()

    if on_time:
        return "-", "-"

    match = re.match(r"Delay:\s*(\d+)\s*minutes?\.\s*Reason:\s*(.*)", comments, re.IGNORECASE | re.DOTALL)
    if match:
        delay = f"{match.group(1)} min"
        reason = match.group(2).strip()
        return delay, (reason if reason else "-")

    return "-", (comments if comments else "-")


def render_table(df, raw_html_cols=None, empty_message="No data available.", key="table"):
    """Compact, scrollable, sortable table with CSV download."""
    if df is None or df.empty:
        st.info(empty_message)
        return

    raw_html_cols = set(raw_html_cols or [])
    display_df = df.copy().fillna("")

    # Streamlit dataframes provide native click-to-sort column headers.
    # Strip HTML from status columns because st.dataframe renders plain values.
    for col in raw_html_cols:
        if col in display_df.columns:
            display_df[col] = (
                display_df[col].astype(str)
                .str.replace(r"<[^>]+>", "", regex=True)
                .str.replace("&#10004;", "✓", regex=False)
                .str.replace("&#10008;", "✘", regex=False)
            )

    csv_df = display_df.copy()

    c1, c2 = st.columns([20, 1])
    with c1:
        st.caption(f"{len(display_df)} record(s). Click a column header to sort.")
    with c2:
        st.download_button(
            "⬇️",
            csv_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{key}.csv",
            mime="text/csv",
            key=f"{key}_download",
            help="Download table as CSV"
        )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=245,
        key=f"{key}_dataframe"
    )


# -----------------------------
# Shared data loading
# -----------------------------
@st.cache_data(ttl=30)
def load_timetable():
    response = supabase.table("timetable").select("*").execute()

    #st.write("Raw response:", response.data)

    df = pd.DataFrame(response.data)

    #st.write("Number of rows:", len(df))
    #st.write("Actual columns:", df.columns.tolist())

    return df

def prepare_timetable(df):
    """Adds Day_order / Start columns used for sorting."""
    df = df.copy()
    day_order = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4,
                 "Friday": 5, "Saturday": 6, "Sunday": 7}
    df["Day_order"] = df["Day"].map(day_order)
    df["Start"] = pd.to_datetime(
        df["Time"].str.split("to").str[0].str.strip(),
        format="%H:%M", errors="coerce"
    )
    return df


@st.cache_data(ttl=30)
def load_observations():
    response = supabase.table("observations").select("*").execute()
    return pd.DataFrame(response.data)


def find_timestamp_column(obs_df):
    """Best-effort detection of a real datetime column Supabase may auto-populate."""
    for candidate in ["created_at", "inserted_at", "timestamp", "observed_at", "date"]:
        if candidate in obs_df.columns:
            return candidate
    return None


def login_page():

    page_header(
        "🎓 VIT - SAS Class Monitoring Portal",
        subtitle="Department of Mathematics",
        small="School of Advanced Sciences",
        tag="Vellore Institute of Technology, Chennai Campus"
    )

    # -----------------------------
    # Center Login Card
    # -----------------------------
    left, center, right = st.columns([1, 2, 1])

    with center:

        st.markdown("## Welcome Back")
        st.caption("Sign in using your Employee Credentials")

        emp_id = st.text_input(
            "Employee ID",
            placeholder="Enter Employee ID"
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter Password"
        )

        if st.button("🔐 Login", use_container_width=True):

            response = (
                supabase.table("users")
                .select("*")
                .eq("employee_id", emp_id.strip())
                .execute()
            )

            if not response.data or not verify_password(
                password.strip(), response.data[0].get("password")
            ):
                st.error("❌ Invalid Employee ID or Password.")
            else:
                user = response.data[0]

                # Lazy-migrate legacy plain-text passwords to bcrypt hashes
                if not is_bcrypt_hash(user.get("password")):
                    supabase.table("users").update(
                        {"password": hash_password(password.strip())}
                    ).eq("employee_id", user["employee_id"]).execute()

                st.session_state.logged_in = True
                st.session_state.emp_id = user["employee_id"]
                st.session_state.name = user["name"]
                st.session_state.role = user["role"]

                st.success(f"Welcome Dr. {user['name']}")
                st.rerun()
    footer()


def monitoring_page():

    df = prepare_timetable(load_timetable())

    page_header(
        "🎓 Class Monitoring System",
        subtitle="Department of Mathematics",
        small="School of Advanced Sciences",
        tag="Vellore Institute of Technology, Chennai"
    )

    top_bar()

    emp_id = str(st.session_state.emp_id).strip()

    emp_df = df[
        df["ID"].astype(str).str.strip() == emp_id
    ]

    if emp_df.empty:
        st.warning("No timetable records found for your Employee ID.")
        st.stop()

    # -----------------------------
    # Employee Information
    # -----------------------------
    #card_start("Employee Information", "👤")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Employee ID", emp_id)
    with col2:
        st.metric("Employee Name", f"Dr. {emp_df.iloc[0]['Name']}")

    card_end()

    # -----------------------------
    # View toggle
    # -----------------------------
    view = st.radio("View", ["Today's Classes", "Complete Timetable"], horizontal=True)

    today = datetime.today().strftime("%A")
    if view == "Today's Classes":
        emp_df = emp_df[emp_df["Day"].str.strip().str.lower() == today.lower()]
        if emp_df.empty:
            st.warning("No classes scheduled for today.")
            st.stop()

    emp_df = emp_df.sort_values(["Day_order", "Start"])

    # -----------------------------
    # Timetable
    # -----------------------------
    card_start(
        "Today's Monitoring Duty" if view == "Today's Classes" else "Complete Timetable",
        "📅"
    )

    # For Today's Classes, identify observations already submitted today.
    recorded_keys = set()
    if view == "Today's Classes":
        current_obs = load_observations()
        if not current_obs.empty and {"monitor_id", "day", "slot"}.issubset(current_obs.columns):
            date_col_monitor = find_timestamp_column(current_obs)
            if date_col_monitor:
                current_obs["_observed_date"] = pd.to_datetime(
                    current_obs[date_col_monitor], errors="coerce"
                ).dt.date
                current_obs = current_obs[
                    current_obs["_observed_date"] == datetime.today().date()
                ]
            else:
                current_obs = current_obs[
                    current_obs["day"].astype(str).str.strip().str.lower() == today.lower()
                ]

            recorded_keys = set(zip(
                current_obs["monitor_id"].astype(str).str.strip(),
                current_obs["day"].astype(str).str.strip().str.lower(),
                current_obs["slot"].astype(str).str.strip().str.lower(),
                current_obs["faculty_id"].astype(str).str.strip()
            ))

    timetable_df = emp_df[["Day", "Slot", "Time", "Venue", "Faculty Name"]].copy()
    if view == "Today's Classes":
        timetable_df["Status"] = emp_df.apply(
            lambda r: "🔒 Already Observed" if (
                str(r["ID"]).strip(),
                str(r["Day"]).strip().lower(),
                str(r["Slot"]).strip().lower(),
                str(r["Faculty ID"]).strip()
            ) in recorded_keys else "⏳ Pending",
            axis=1
        )
    render_table(
        timetable_df,
        empty_message="No classes to show.",
        key="monitoring_timetable"
    )

    card_end()

    # -----------------------------
    # Class selection
    # -----------------------------
    emp_df = emp_df.reset_index(drop=True)
    emp_df["_observed"] = emp_df.apply(
        lambda r: (
            str(r["ID"]).strip(),
            str(r["Day"]).strip().lower(),
            str(r["Slot"]).strip().lower(),
            str(r["Faculty ID"]).strip()
        ) in recorded_keys,
        axis=1
    )

    pending_df = emp_df[~emp_df["_observed"]].copy()
    recorded_df = emp_df[emp_df["_observed"]].copy()

    card_start("Select Class", "🎯")

    if pending_df.empty:
        st.success("🎉 All of your classes for today have already been observed.")
        card_end()
        footer()
        return

    display_options = (
        pending_df["Slot"].astype(str) + " | " +
        pending_df["Time"].astype(str) + " | " +
        pending_df["Venue"].astype(str) + " | " +
        pending_df["Faculty Name"].astype(str)
    ).tolist()

    selected = st.selectbox(
        "Select Class",
        display_options,
        label_visibility="collapsed"
    )

    card_end()

    row = pending_df.iloc[display_options.index(selected)]

    # -----------------------------
    # Class Observation
    # -----------------------------
    card_start("Class Observation", "📝")

    on_time = st.radio(
        "Faculty on time to class?",
        ["Yes", "No"],
        horizontal=True
    )

    delay = ""
    reason = ""

    if on_time == "No":

        delay = st.number_input(
            "How many minutes late to the class",
            min_value=1,
            max_value=180,
            step=1
        )

        reason = st.text_area(
            "Comments by Monitoring Faculty",
            height=120
        )

    if st.button("✅ Submit", use_container_width=True):

        if on_time == "No" and reason.strip() == "":
            st.error("Please enter the reason for the delay.")
            st.stop()

        if on_time == "Yes":
            comments = "Faculty reached the class on time."
        else:
            comments = f"Delay: {delay} minutes. Reason: {reason.strip()}"

        # Check whether this class has already been observed
        existing = (
            supabase.table("observations")
            .select("id")
            .eq("monitor_id", clean(row["ID"]))
            .eq("observation_date", datetime.today().date().isoformat())
            .eq("slot", clean(row["Slot"]))
            .eq("faculty_id", clean(row["Faculty ID"]))
            .eq("venue", clean(row["Venue"]))
            .execute()
        )

        if existing.data:
            st.warning("⚠️ Observation for this class has already been submitted.")
        else:
            try:
                supabase.table("observations").insert({
                    "monitor_id": clean(row["ID"]),
                    "monitor_name": clean(row["Name"]),
                    "class_name": clean(row["Class"]),
                    "day": clean(row["Day"]),
                    "time": clean(row["Time"]),
                    "slot": clean(row["Slot"]),
                    "faculty_id": clean(row["Faculty ID"]),
                    "faculty_name": clean(row["Faculty Name"]),
                    "class_strength": clean(row["Class Strength"]),
                    "venue": clean(row["Venue"]),
                    "observation_date": datetime.today().date().isoformat(),
                    "on_time": (on_time == "Yes"),
                    "comments": comments
                }).execute()

                load_observations.clear()
                st.success("✅ Observation submitted successfully.")
                st.rerun()

            except Exception as e:
                st.exception(e)

    card_end()

    footer()


def admin_page():

    df_all = prepare_timetable(load_timetable())
    obs_df = load_observations()

    page_header(
        "🎓 Class Monitoring — Admin Dashboard",
        subtitle="Department of Mathematics",
        small="School of Advanced Sciences",
        tag="Vellore Institute of Technology, Chennai"
    )

    top_bar()

    if st.button("🔄 Refresh Data"):
        load_observations.clear()
        st.rerun()

    # Normalize on_time to real booleans (Supabase can return it as text)
    if not obs_df.empty:
        obs_df["on_time"] = (
            obs_df["on_time"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "false": False, "1": True, "0": False})
        )

    date_col = find_timestamp_column(obs_df)
    if date_col:
        obs_df["_observed_date"] = pd.to_datetime(obs_df[date_col], errors="coerce").dt.date

    today_date = datetime.today().date()
    today_name = datetime.today().strftime("%A")

    st.caption(f"📅 Showing statistics for **today — {today_name}, {today_date.strftime('%d %b %Y')}**")

    # -----------------------------
    # Scope overview / coverage cards to TODAY
    # -----------------------------
    df = df_all[df_all["Day"].str.strip().str.lower() == today_name.lower()]

    if date_col:
        obs_today = obs_df[obs_df["_observed_date"] == today_date] if not obs_df.empty else obs_df
    else:
        obs_today = (
            obs_df[obs_df["day"].astype(str).str.strip().str.lower() == today_name.lower()]
            if not obs_df.empty else obs_df
        )

    total_classes = len(df)
    total_observations = len(obs_today)
    pending = max(total_classes - total_observations, 0)
    completion_pct = (total_observations / total_classes * 100) if total_classes else 0

    on_time_count = int(obs_today["on_time"].sum()) if not obs_today.empty else 0
    late_count = total_observations - on_time_count

    # -----------------------------
    # Overview stats
    # -----------------------------
    card_start("Today's Overview", "📊")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Today's Classes", total_classes)
    with c2:
        st.metric("Observations Submitted", total_observations)
    with c3:
        st.metric("Pending", pending)
    with c4:
        st.metric("Completion", f"{completion_pct:.1f}%")

    c1, c2 = st.columns(2)
    with c1:
        st.metric("✅ On Time", on_time_count)
    with c2:
        st.metric("⏰ Late", late_count)

    if not date_col:
        st.caption(
            "⚠️ No timestamp column (e.g. 'created_at') found on the 'observations' table, "
            "so today's observation count falls back to matching weekday name — add a "
            "timestamp column in Supabase for exact date accuracy."
        )

    card_end()

    # -----------------------------
    # Faculty monitored vs not monitored (unique by Faculty ID)
    # -----------------------------
    card_start("Faculty Coverage — Today", "👥")

    faculty_today = df[["Faculty ID", "Faculty Name"]].dropna(subset=["Faculty ID"]).drop_duplicates(subset="Faculty ID")
    faculty_today["Faculty ID"] = faculty_today["Faculty ID"].astype(str).str.strip()
    faculty_id_to_name = dict(zip(faculty_today["Faculty ID"], faculty_today["Faculty Name"]))
    all_faculty_ids = set(faculty_today["Faculty ID"])

    monitored_ids = (
        set(obs_today["faculty_id"].astype(str).str.strip().unique()) & all_faculty_ids
        if not obs_today.empty else set()
    )
    not_monitored_ids = sorted(all_faculty_ids - monitored_ids)
    monitored_ids = sorted(monitored_ids)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f"**✅ Faculty Monitored ({len(monitored_ids)})**")
        render_table(
            pd.DataFrame({
                "Faculty ID": monitored_ids,
                "Faculty Name": [faculty_id_to_name.get(fid, "") for fid in monitored_ids]
            }),
            empty_message="No faculty monitored yet today.", key="faculty_monitored"
        )

    with c2:
        st.markdown(f"**❌ Faculty Not Monitored ({len(not_monitored_ids)})**")
        render_table(
            pd.DataFrame({
                "Faculty ID": not_monitored_ids,
                "Faculty Name": [faculty_id_to_name.get(fid, "") for fid in not_monitored_ids]
            }),
            empty_message="All of today's scheduled faculty have been monitored.", key="faculty_not_monitored"
        )

    card_end()

    # -----------------------------
    # Monitors who went vs did not go (unique by Employee ID)
    # -----------------------------
    card_start("Monitor Attendance — Today", "🧑‍🏫")

    monitors_today = df[["ID", "Name"]].dropna(subset=["ID"]).drop_duplicates(subset="ID")
    monitors_today["ID"] = monitors_today["ID"].astype(str).str.strip()
    monitor_id_to_name = dict(zip(monitors_today["ID"], monitors_today["Name"]))
    all_monitor_ids = set(monitors_today["ID"])

    went_ids = (
        set(obs_today["monitor_id"].astype(str).str.strip().unique()) & all_monitor_ids
        if not obs_today.empty else set()
    )
    not_went_ids = sorted(all_monitor_ids - went_ids)
    went_ids = sorted(went_ids)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f"**✅ Monitors Who Went ({len(went_ids)})**")
        render_table(
            pd.DataFrame({
                "Employee ID": went_ids,
                "Name": [monitor_id_to_name.get(mid, "") for mid in went_ids]
            }),
            empty_message="No monitor has submitted an observation yet today.", key="monitors_went"
        )

    with c2:
        st.markdown(f"**❌ Monitors Who Did Not Go ({len(not_went_ids)})**")
        render_table(
            pd.DataFrame({
                "Employee ID": not_went_ids,
                "Name": [monitor_id_to_name.get(mid, "") for mid in not_went_ids]
            }),
            empty_message="Every monitor scheduled today has submitted an observation.", key="monitors_not_went"
        )

    card_end()

  
    # -----------------------------
    # Classes not yet observed today
    # (pending list — uniquely matched by monitor + slot + faculty + venue)
    # -----------------------------
    card_start("Pending Classes — Today", "🕓")
    
    if obs_today.empty:
        pending_df = df.copy()
    else:
        # Each observation belongs to one specific:
        # Monitor + Slot + Faculty + Venue
        obs_keys = set(
            zip(
                obs_today["monitor_id"].astype(str).str.strip(),
                obs_today["slot"].astype(str).str.strip().str.lower(),
                obs_today["faculty_id"].astype(str).str.strip(),
                obs_today["venue"].astype(str).str.strip().str.lower()
            )
        )
    
        mask = ~df.apply(
            lambda r: (
                str(r["ID"]).strip(),
                str(r["Slot"]).strip().lower(),
                str(r["Faculty ID"]).strip(),
                str(r["Venue"]).strip().lower()
            ) in obs_keys,
            axis=1
        )
    
        pending_df = df[mask]
    
    if pending_df.empty:
        st.success("🎉 Every class scheduled today has been observed.")
    else:
        render_table(
            pending_df.sort_values(["Start"])[
                ["Day", "Slot", "Time", "Venue", "Faculty Name", "Name"]
            ].rename(columns={"Name": "Monitor"}),
            key="pending_classes"
        )
    
    card_end()

    # -----------------------------
    # Observation Log — Faculty
    # (browsable log of actually submitted observations, any date range)
    # -----------------------------
    card_start("Observation Log — Faculty", "📋")

    if obs_df.empty:
        st.info("No observations submitted yet.")
    else:
        f1, f2, f3 = st.columns(3)

        with f1:
            if date_col:
                valid_dates = obs_df["_observed_date"].dropna()
                min_date = valid_dates.min() if not valid_dates.empty else today_date
                max_date = valid_dates.max() if not valid_dates.empty else today_date
                date_range = st.date_input(
                    "Filter by Date",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                    key="faculty_log_date_range"
                )
            else:
                date_range = None
                st.caption("Add a 'created_at' timestamp column to filter by date.")

        with f2:
            faculty_filter = st.multiselect(
                "Filter by Faculty",
                sorted(obs_df["faculty_name"].dropna().unique()),
                key="faculty_log_faculty_filter"
            )
        with f3:
            status_filter = st.multiselect(
                "Filter by Status",
                ["On Time", "Late"],
                key="faculty_log_status_filter"
            )

        filtered = obs_df.copy()

        if date_col and date_range:
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
                filtered = filtered[
                    (filtered["_observed_date"] >= start_date) &
                    (filtered["_observed_date"] <= end_date)
                ]
            elif hasattr(date_range, "year"):
                filtered = filtered[filtered["_observed_date"] == date_range]

        if faculty_filter:
            filtered = filtered[filtered["faculty_name"].isin(faculty_filter)]
        if status_filter:
            statuses = set(status_filter)
            want_on_time = "On Time" in statuses
            want_late = "Late" in statuses
            if want_on_time and not want_late:
                filtered = filtered[filtered["on_time"] == True]
            elif want_late and not want_on_time:
                filtered = filtered[filtered["on_time"] == False]

        if filtered.empty:
            st.info("No observations match the selected filters.")
        else:
            if date_col:
                dates_display = filtered["_observed_date"].apply(
                    lambda d: d.strftime("%d %b %Y") if pd.notna(d) else "-"
                ).tolist()
            else:
                dates_display = ["-"] * len(filtered)

            delays, comments = zip(*filtered.apply(split_delay_comment, axis=1))
            status_html = filtered["on_time"].map(status_badge).tolist()

            faculty_log_df = pd.DataFrame({
                "Date": dates_display,
                "Day": filtered["day"].tolist(),
                "Slot": filtered["slot"].tolist(),
                "Time": filtered["time"].tolist(),
                "Venue": filtered["venue"].tolist(),
                "Faculty": filtered["faculty_name"].tolist(),
                "Monitored By": filtered["monitor_name"].tolist(),
                "Status": status_html,
                "Delay": list(delays),
                "Comments": list(comments),
            })

            render_table(faculty_log_df, raw_html_cols={"Status"}, key="faculty_observation_log")

    card_end()

   
    # -----------------------------
    # Observation Log — Monitor
    # (class-by-class matching using monitor + slot + faculty + venue)
    # -----------------------------
    card_start("Observation Log — Monitor", "🧾")
    
    selected_date = st.date_input(
        "Select Date",
        value=today_date,
        key="monitor_log_selected_date"
    )
    
    selected_weekday = selected_date.strftime("%A")
    
    schedule_for_date = df_all[
        df_all["Day"].str.strip().str.lower() == selected_weekday.lower()
    ].copy()
    
    if schedule_for_date.empty:
        st.info(f"No classes are scheduled on {selected_weekday}.")
    else:
    
        # ---------------------------------------------------------
        # Get observations for the selected date
        # ---------------------------------------------------------
        if date_col:
            obs_for_date = (
                obs_df[obs_df["_observed_date"] == selected_date]
                if not obs_df.empty
                else obs_df
            )
        else:
            obs_for_date = (
                obs_df[
                    obs_df["day"].astype(str).str.strip().str.lower()
                    == selected_weekday.lower()
                ]
                if not obs_df.empty
                else obs_df
            )
    
            st.caption(
                "⚠️ No timestamp column found — matching is done by weekday name, "
                "so this may include observations from other weeks on the same weekday."
            )

        # ---------------------------------------------------------
        # Build observation lookup
        #
        # IMPORTANT:
        # One observation is identified by:
        # Monitor + Slot + Faculty + Venue
        #
        # This prevents one observed class from marking another
        # class of the same monitor as observed.
        # ---------------------------------------------------------
        obs_lookup = {}
    
        for _, orow in obs_for_date.iterrows():
    
            key = (
                str(orow.get("monitor_id", "")).strip(),
                str(orow.get("slot", "")).strip().lower(),
                str(orow.get("faculty_id", "")).strip(),
                str(orow.get("venue", "")).strip().lower()
            )
    
            obs_lookup[key] = orow
    
        # ---------------------------------------------------------
        # Build class-by-class monitoring log
        # ---------------------------------------------------------
        rows = []
    
        for _, srow in schedule_for_date.sort_values("Start").iterrows():
    
            key = (
                str(srow["ID"]).strip(),
                str(srow["Slot"]).strip().lower(),
                str(srow["Faculty ID"]).strip(),
                str(srow["Venue"]).strip().lower()
            )
    
            orow = obs_lookup.get(key)
    
            if orow is not None:
    
                delay, comment = split_delay_comment(orow)
    
                punctuality_html = status_badge(
                    bool(orow.get("on_time"))
                )
    
                recorded = True
    
            else:
    
                delay = "-"
                comment = "-"
                punctuality_html = "-"
                recorded = False
    
            rows.append({
                "Date": selected_date.strftime("%d %b %Y"),
                "Day": srow["Day"],
                "Slot": srow["Slot"],
                "Time": srow["Time"],
                "Venue": srow["Venue"],
                "Faculty": srow["Faculty Name"],
                "Monitor": srow["Name"],
                "Recorded": recorded_badge(recorded),
                "Status": punctuality_html,
                "Delay": delay,
                "Comments": comment
            })
    
        monitor_log_df = pd.DataFrame(rows)
    
        render_table(
            monitor_log_df,
            raw_html_cols={"Recorded", "Status"},
            key="monitor_observation_log"
        )
    
    card_end()

    footer()


def dispatch():
    inject_css()

    if not st.session_state.logged_in:
        login_page()
        return

    role = str(st.session_state.get("role", "")).strip().lower()

    if role == "admin":
        if "admin_view_mode" not in st.session_state:
            st.session_state.admin_view_mode = "🛠️ Admin Dashboard"

        left, center, right = st.columns([1, 2, 1])
        with center:
            st.radio(
                "Switch View",
                ["🛠️ Admin Dashboard", "📋 Monitoring View"],
                horizontal=True,
                key="admin_view_mode",
                label_visibility="collapsed"
            )

        if st.session_state.admin_view_mode == "🛠️ Admin Dashboard":
            admin_page()
        else:
            monitoring_page()
    else:
        monitoring_page()


dispatch()
