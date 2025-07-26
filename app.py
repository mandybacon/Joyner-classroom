import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pytz
import os
import io
import base64
from behavior_tracker import BehaviorTracker
from data_manager import DataManager

# Initialize session state
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()
if 'selected_student' not in st.session_state:
    st.session_state.selected_student = None
if 'students_df' not in st.session_state:
    st.session_state.students_df = None
if 'behavior_tracker' not in st.session_state:
    st.session_state.behavior_tracker = BehaviorTracker()
if 'speed_mode_active' not in st.session_state:
    st.session_state.speed_mode_active = False
if 'record_previous_date_active' not in st.session_state:
    st.session_state.record_previous_date_active = False
if 'persistent_date' not in st.session_state:
    st.session_state.persistent_date = None
if 'show_report_dialog' not in st.session_state:
    st.session_state.show_report_dialog = False


def generate_rich_html_report(student_list):
    """Generates a rich, interactive HTML report that opens in a new tab."""
    
    all_student_html = ""
    for student_name in student_list:
        student_data = st.session_state.data_manager.get_student_behavior_data(student_name)
        
        pie_chart_html = "<h4>Behavior Distribution</h4><p>No data to display.</p>"
        bar_chart_html = "<h4>Behavior Percentages</h4><p>No data to display.</p>"
        timeline_html = "<h4>Recent Behavior</h4><p>No data to display.</p>"

        if not student_data.empty:
            colors = st.session_state.behavior_tracker.get_color_options()
            color_names = list(colors.keys())
            color_counts = student_data['color'].value_counts()
            total_entries = len(student_data)
            percentages = {color: (color_counts.get(color, 0) / total_entries) * 100 for color in color_names}

            # --- Generate Pie Chart ---
            fig_pie = px.pie(values=list(percentages.values()), names=color_names, color=color_names, color_discrete_map=colors)
            fig_pie.update_layout(showlegend=False, width=300, height=300, margin=dict(l=10, r=10, t=10, b=10))
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            pie_chart_html = f"<h4>Behavior Distribution</h4>{fig_pie.to_html(full_html=False, include_plotlyjs='cdn')}"

            # --- Generate Bar Chart ---
            fig_bar = px.bar(x=color_names, y=[percentages[c] for c in color_names], color=color_names, color_discrete_map=colors)
            fig_bar.update_layout(showlegend=False, width=300, height=300, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Percentage (%)")
            bar_chart_html = f"<h4>Behavior Percentages</h4>{fig_bar.to_html(full_html=False, include_plotlyjs='cdn')}"

            # --- Generate Timeline Chart ---
            recent_data = student_data.sort_values('date', ascending=False).head(10)
            fig_timeline = go.Figure()
            if not recent_data.empty:
                min_date = recent_data['date'].min()
                for color in color_names:
                    fig_timeline.add_trace(go.Scatter(x=[min_date], y=[color], mode='markers', marker=dict(size=0, opacity=0), showlegend=False))
                for _, row in recent_data.iterrows():
                    fig_timeline.add_trace(go.Scatter(x=[row['date']], y=[row['color']], mode='markers', marker=dict(size=15, color=colors[row['color']], line=dict(width=2, color='black')), name=row['color'], showlegend=False))
            fig_timeline.update_layout(width=650, height=300, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(categoryorder='array', categoryarray=color_names), xaxis_title="Date")
            timeline_html = f"<h4>Recent Behavior Timeline</h4>{fig_timeline.to_html(full_html=False, include_plotlyjs='cdn')}"

        points_summary = st.session_state.behavior_tracker.calculate_points_summary(student_data)
        
        all_student_html += f"""
        <div class="student-report">
            <h2>{student_name}</h2>
            <div class="top-row">
                <div class="summary-table">
                    <h4>Point System Summary</h4>
                    <table>
                        <tr><th>Category</th><th>Value</th></tr>
                        <tr><td>Good Points</td><td>{points_summary['total_good_points']}</td></tr>
                        <tr><td>Bad Points</td><td>{points_summary['total_bad_points']}</td></tr>
                        <tr><td>Good Behavior %</td><td>{points_summary['good_percentage']}%</td></tr>
                        <tr><td>Days Recorded</td><td>{points_summary['days_recorded']}</td></tr>
                    </table>
                </div>
                <div class="chart-cell">{pie_chart_html}</div>
            </div>
            <div class="bottom-row">
                <div class="chart-cell">{bar_chart_html}</div>
                <div class="chart-cell timeline">{timeline_html}</div>
            </div>
        </div>
        """

    full_html = f"""
    <html><head><title>Behavior Report</title><style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
        body {{ font-family: 'Poppins', sans-serif; padding: 20px; }}
        .student-report {{ page-break-inside: avoid; border: 1px solid #ccc; border-radius: 10px; padding: 15px; margin-bottom: 20px; }}
        h1 {{ text-align: center; }} h2 {{ border-bottom: 2px solid #eee; padding-bottom: 5px; }} h4 {{ text-align: center; margin-top: 0; }}
        .top-row, .bottom-row {{ display: flex; align-items: center; justify-content: space-around; margin-bottom: 15px; }}
        .summary-table, .chart-cell {{ flex: 1; padding: 10px; text-align: center; }}
        .chart-cell.timeline {{ flex: 2; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style></head><body>
        <h1>Behavior Report</h1>
        {all_student_html}
    </body></html>
    """
    return full_html


def main():
    # Auto-load the last uploaded file if it exists
    if st.session_state.students_df is None and os.path.exists(
            "last_uploaded_roster.csv"):
        try:
            df = pd.read_csv("last_uploaded_roster.csv")
            students = df['name'].dropna().astype(str).tolist()
            st.session_state.students_df = df
            st.session_state.data_manager.load_or_create_behavior_data(
                students)
        except Exception as e:
            st.sidebar.error(f"Failed to load previous student list: {str(e)}")

    st.set_page_config(page_title="Mrs. Joyner's Class",
                       page_icon="📚",
                       layout="wide",
                       initial_sidebar_state="collapsed")

    # --- STYLING BLOCK FOR HEADER AND BUTTONS ---
    colors = st.session_state.behavior_tracker.get_color_options()
    style_css = """
    <style>
        /* Light Mode Banner Styles */
        .stripe-banner {
            background-color: #FFFFFF;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            border: 1px solid #E0E0E0;
        }
        .stripe-title {
            font-size: 2.8em;
            font-weight: bold;
            text-align: center;
            margin-bottom: 20px;
            color: #333;
        }

        /* Dark Mode Banner Styles */
        body[data-theme="dark"] .stripe-banner {
            background-color: #262730; /* Streamlit's dark background */
            border: 1px solid #444;
        }
        body[data-theme="dark"] .stripe-title {
            color: #FAFAFA; /* Light text for dark mode */
        }

        /* Common Banner Elements */
        .color-stripe {
            display: flex;
            height: 15px;
            width: 100%;
            border-radius: 10px;
            overflow: hidden;
        }
        .color-box {
            flex-grow: 1;
        }
    </style>
    """
    st.markdown(style_css, unsafe_allow_html=True)

    # --- COLOR STRIPE HEADER ---
    color_boxes_html = "".join([
        f'<div class="color-box" style="background-color: {hex_code};"></div>'
        for hex_code in colors.values()
    ])
    
    st.markdown(f"""
        <div class="stripe-banner">
            <div class="stripe-title">Mrs. Joyner's Class</div>
            <div class="color-stripe">
                {color_boxes_html}
            </div>
        </div>
    """, unsafe_allow_html=True)


    # --- Speed Entry Button in the top-right corner ---
    if st.session_state.students_df is not None:
        st.markdown("<div style='margin-top: 10px;'></div>",
                    unsafe_allow_html=True)
        _, col_btn = st.columns([0.8, 0.2])
        with col_btn:
            if st.session_state.speed_mode_active:
                if st.button("Back to Home Page",
                             use_container_width=True,
                             type="primary"):
                    st.session_state.speed_mode_active = False
                    st.rerun()
            else:
                if st.button("Enter Today's Data",
                             use_container_width=True,
                             type="primary"):
                    st.session_state.speed_entry_index = 0
                    st.session_state.speed_mode_active = True
                    st.rerun()

    # --- SIDEBAR: File uploader ---
    st.sidebar.header("Upload Student Roster")
    st.sidebar.info(
        "Format: One student name per row in first column of file.")
    uploaded_file = st.sidebar.file_uploader(
        "Choose a CSV or Excel file",
        type=['csv', 'xlsx', 'xls'],
        help="Upload a file with student names in the first column")

    if uploaded_file is not None:
        try:
            file_size = uploaded_file.size if hasattr(
                uploaded_file, 'size') else len(uploaded_file.getvalue())
            if file_size > 200 * 1024 * 1024:
                st.error("File size exceeds 200MB limit.")
                return
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            if df.empty or df.columns.empty:
                st.error(
                    "The uploaded file appears to be empty or has no columns.")
                return
            students = df.iloc[:, 0].dropna().astype(str).tolist()
            if not students:
                st.error(
                    "No student names found in the first column of the uploaded file."
                )
                return
            st.session_state.students_df = pd.DataFrame({'name': students})
            st.session_state.data_manager.load_or_create_behavior_data(
                students)
            st.session_state.students_df.to_csv("last_uploaded_roster.csv",
                                                index=False)
            st.sidebar.success(
                f"Loaded {len(students)} students successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
            return

    # --- MAIN CONTENT AREA: Render based on the active mode ---
    if st.session_state.get(
            'speed_mode_active',
            False) and st.session_state.students_df is not None:
        # --- SPEED MODE VIEW ---
        from zoneinfo import ZoneInfo
        students = st.session_state.students_df['name'].tolist()
        color_names = list(colors.keys())

        if "speed_entry_index" not in st.session_state:
            st.session_state.speed_entry_index = 0

        if st.session_state.speed_entry_index >= len(students):
            st.success("All students logged for today!")
            if st.button("Change Today's Data"):
                st.session_state.speed_entry_index = 0
                st.rerun()
            st.stop()

        current_student = students[st.session_state.speed_entry_index]
        st.subheader(f"Log behavior for: {current_student}")

        current_date = datetime.now(ZoneInfo("America/Chicago")).date()
        date_str = current_date.strftime("%Y-%m-%d")
        date_display = current_date.strftime("%m/%d/%Y")
        st.markdown(f"**Recording for:** {date_display}")

        cols = st.columns(len(color_names))
        for i, color in enumerate(color_names):
            with cols[i]:
                if st.button(color,
                             key=f"speed_color_{color}_{current_student}",
                             use_container_width=True):
                    st.session_state.data_manager.add_behavior_entry(
                        current_student, color, date_str)
                    st.session_state.speed_entry_index += 1
                    st.rerun()

        st.markdown("###")
        if st.button("Skip Student"):
            st.session_state.speed_entry_index += 1
            st.rerun()

        st.stop()

    elif st.session_state.students_df is not None:
        # --- DASHBOARD VIEW ---
        if st.session_state.selected_student is None:
            first_student = st.session_state.students_df['name'].iloc[0]
            st.session_state.selected_student = first_student

        col1, spacer, col2 = st.columns([1, 0.2, 3])

        with col1:
            st.header("Student Roster")
            st.markdown("""
                <style>
                div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div > div > div > button {
                    font-size: 12px !important; padding: 6px 8px !important; margin: 1px 0px !important;
                    height: 32px !important; width: 150px !important; max-width: 150px !important;
                }
                </style>
            """,
                        unsafe_allow_html=True)
            for student in st.session_state.students_df['name']:
                if st.button(student,
                             key=f"btn_{student}",
                             use_container_width=True):
                    st.session_state.selected_student = student
                    st.rerun()
        with col2:
            if st.session_state.selected_student:
                display_student_details(st.session_state.selected_student)
            else:
                st.info(
                    "👈 Select a student from the list to view their behavior statistics"
                )

    else:
        # --- INITIAL EMPTY VIEW ---
        st.info(
            "👈 Please upload a student roster file using the sidebar to get started"
        )


def display_student_details(student_name):
    st.header(f"{student_name}")

    # Behavior entry section
    st.subheader("Record Behavior")

    colors = st.session_state.behavior_tracker.get_color_options()
    color_names = list(colors.keys())

    # --- MODIFIED: Persistent Date Logic ---
    chicago_tz = pytz.timezone('America/Chicago')
    current_date_chicago = datetime.now(chicago_tz).date()

    if st.session_state.persistent_date is None:
        st.session_state.persistent_date = current_date_chicago

    st.session_state.record_previous_date_active = st.checkbox(
        "Record behavior for previous date?",
        value=st.session_state.record_previous_date_active
    )

    if st.session_state.record_previous_date_active:
        selected_date = st.date_input(
            "Select date:",
            value=st.session_state.persistent_date,
            max_value=current_date_chicago,
            help="This date will be used for all students until the box is unchecked.",
            format="MM/DD/YYYY"
        )
        st.session_state.persistent_date = selected_date
    else:
        selected_date = current_date_chicago
        st.session_state.persistent_date = current_date_chicago


    date_display = selected_date.strftime("%m/%d/%Y")
    st.write(f"**Recording for:** {date_display}")

    cols = st.columns(7)
    for i, color in enumerate(color_names):
        with cols[i]:
            if st.button(color,
                         key=f"color_{color}_{student_name}",
                         use_container_width=True):
                st.session_state.data_manager.add_behavior_entry(
                    student_name, color, selected_date.strftime("%Y-%m-%d"))
                st.rerun()

    student_data = st.session_state.data_manager.get_student_behavior_data(
        student_name)

    if student_data is not None and not student_data.empty:
        color_counts = student_data['color'].value_counts()
        total_entries = len(student_data)
        percentages = {}
        for color in color_names:
            count = color_counts.get(color, 0)
            percentages[color] = (
                count / total_entries) * 100 if total_entries > 0 else 0

        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Behavior Distribution")
            fig_pie = px.pie(values=list(percentages.values()),
                             names=list(percentages.keys()),
                             color=list(percentages.keys()),
                             color_discrete_map=colors)
            fig_pie.update_traces(textposition='inside',
                                  textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            st.subheader("Behavior Percentages")
            fig_bar = px.bar(x=list(percentages.keys()),
                             y=list(percentages.values()),
                             color=list(percentages.keys()),
                             color_discrete_map=colors,
                             labels={
                                 'x': 'Behavior Color',
                                 'y': 'Percentage (%)'
                             })
            fig_bar.update_layout(showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("Point System Distribution")
        points_summary = st.session_state.behavior_tracker.calculate_points_summary(
            student_data)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Good Points", points_summary['total_good_points'])
        with col2:
            st.metric("Bad Points", points_summary['total_bad_points'])
        with col3:
            st.metric("Good Behavior %",
                      f"{points_summary['good_percentage']}%")
        with col4:
            st.metric("Days Recorded", points_summary['days_recorded'])

        st.write("")
        st.subheader("Recent Behavior Timeline")
        recent_data = student_data.sort_values('date',
                                               ascending=False).head(10)
        if not recent_data.empty:
            fig_timeline = go.Figure()
            min_date = recent_data['date'].min()
            for color in color_names:
                fig_timeline.add_trace(
                    go.Scatter(x=[min_date],
                               y=[color],
                               mode='markers',
                               marker=dict(size=0, opacity=0),
                               showlegend=False,
                               hoverinfo='skip'))
            for _, row in recent_data.iterrows():
                fig_timeline.add_trace(
                    go.Scatter(x=[row['date']],
                               y=[row['color']],
                               mode='markers',
                               marker=dict(size=15,
                                           color=colors[row['color']],
                                           line=dict(width=2, color='black')),
                               name=row['color'],
                               showlegend=False))
            fig_timeline.update_layout(xaxis_title="Date",
                                       yaxis_title="Behavior Color",
                                       xaxis=dict(tickformat='%m/%d'),
                                       yaxis=dict(categoryorder='array',
                                                  categoryarray=color_names))
            st.plotly_chart(fig_timeline, use_container_width=True)

        # --- ACTION BUTTONS ---
        st.write("")
        st.write("")
        report_col, clear_col = st.columns([0.8, 0.2])
        with report_col:
            if st.button("Generate Report..."):
                st.session_state.show_report_dialog = True
                st.rerun()
        with clear_col:
            if st.button("Clear Behavior Data",
                         key=f"clear_link_{student_name}"):
                st.session_state[f'show_clear_dialog_{student_name}'] = True

        # --- REPORT DIALOG ---
        if st.session_state.show_report_dialog:
            with st.form("report_form"):
                st.markdown("---")
                st.markdown("#### Generate Report")
                
                report_option = st.radio(
                    "Select which students to include:",
                    (f"Only {student_name}", "All Students"),
                    key="report_radio"
                )
                
                submitted = st.form_submit_button("Generate & Open Report")

                if submitted:
                    if report_option == f"Only {student_name}":
                        student_list = [student_name]
                    else:
                        student_list = st.session_state.students_df['name'].tolist()
                    
                    with st.spinner("Generating report..."):
                        report_html = generate_rich_html_report(student_list)
                        b64 = base64.b64encode(report_html.encode()).decode()
                        href = f'<a href="data:text/html;base64,{b64}" target="_blank" rel="noopener noreferrer">Click here to open your report in a new tab</a>'
                        st.markdown(href, unsafe_allow_html=True)
                        st.success("Your report is ready!")

            if st.button("Close Report View"):
                st.session_state.show_report_dialog = False
                st.rerun()

        # --- CLEAR DATA DIALOG ---
        if st.session_state.get(f'show_clear_dialog_{student_name}', False):
            with st.container():
                st.markdown("---")
                st.markdown("**Clear Behavior Data**")
                clear_option = st.radio(
                    "Choose what to clear:",
                    [f"Only {student_name}", "All students"],
                    key=f"clear_radio_{student_name}")
                if clear_option == f"Only {student_name}":
                    st.write(f"Data will be cleared for **{student_name}**")
                else:
                    st.write("Data will be cleared for **all students**")
                password = st.text_input("Enter password to confirm:",
                                         type="password",
                                         key=f"clear_password_{student_name}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Clear Data",
                                 type="primary",
                                 key=f"confirm_clear_{student_name}"):
                        if password == "MRSJOYNER":
                            if clear_option == f"Only {student_name}":
                                success = st.session_state.data_manager.clear_student_data(
                                    student_name)
                                if success:
                                    st.success(
                                        f"All behavior data cleared for {student_name}"
                                    )
                                    st.session_state[
                                        f'show_clear_dialog_{student_name}'] = False
                                    st.rerun()
                                else:
                                    st.error("Failed to clear student data")
                            else:
                                success = st.session_state.data_manager.clear_all_data(
                                )
                                if success:
                                    st.success(
                                        "All behavior data cleared for all students"
                                    )
                                    st.session_state[
                                        f'show_clear_dialog_{student_name}'] = False
                                    st.rerun()
                                else:
                                    st.error("Failed to clear all data")
                        else:
                            st.error("Incorrect password")
                with col2:
                    if st.button("Cancel", key=f"cancel_clear_{student_name}"):
                        st.session_state[
                            f'show_clear_dialog_{student_name}'] = False
                        st.rerun()
    else:
        st.info("No behavior data recorded for this student yet.")


if __name__ == "__main__":
    main()
