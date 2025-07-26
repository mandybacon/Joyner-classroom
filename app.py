import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pytz
import os
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
# Add a new state variable to track speed entry mode
if 'speed_mode_active' not in st.session_state:
    st.session_state.speed_mode_active = False


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

    # --- STYLING BLOCK FOR BUTTONS AND NEW HEADER ---
    colors = st.session_state.behavior_tracker.get_color_options()
    style_css = """
    <style>
        /* Color Stripe Banner Style */
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
        .color-stripe {
            display: flex;
            height: 15px;
            width: 100%;
            border-radius: 10px;
            overflow: hidden; /* Ensures the child elements respect the border radius */
        }
        .color-box {
            flex-grow: 1; /* Each color box takes up equal space */
        }
    """
    # Add button styles to the same CSS block
    for color, hex_code in colors.items():
        style_css += f"""
            div.div-{color} div[data-testid="stButton"] > button {{
                background-color: {hex_code} !important;
                color: white !important;
                font-weight: bold !important;
                border: 1px solid black !important;
                border-radius: 6px !important;
            }}
        """
    style_css += "</style>"
    st.markdown(style_css, unsafe_allow_html=True)
    # --- END STYLING BLOCK ---

    # --- COLOR STRIPE HEADER ---
    # Generate the HTML for the color boxes dynamically
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
    """,
                unsafe_allow_html=True)

    # --- Speed Entry Button in the top-right corner ---
    if st.session_state.students_df is not None:
        # Add some vertical space to push the button down
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
                # Wrap button in a styled div
                st.markdown(f'<div class="div-{color}">',
                            unsafe_allow_html=True)
                if st.button(color,
                             key=f"speed_color_{color}_{current_student}",
                             use_container_width=True):
                    st.session_state.data_manager.add_behavior_entry(
                        current_student, color, date_str)
                    st.session_state.speed_entry_index += 1
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

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
                # Removed the st.write("") calls to move content up
                display_student_details(st.session_state.selected_student)
            else:
                st.info(
                    "👈 Select a student from the list to view their behavior statistics"
                )

    else:
        # --- INITIAL EMPTY VIEW ---
        st.info(
            "First time here, Lexi? Open the sidebar and upload your student roster to get started!"
        )


def display_student_details(student_name):
    st.header(f"{student_name}")

    # Behavior entry section
    st.subheader("Record Behavior")

    colors = st.session_state.behavior_tracker.get_color_options()
    color_names = list(colors.keys())

    record_previous = st.checkbox("Record behavior for previous date?")

    chicago_tz = pytz.timezone('America/Chicago')
    current_date_chicago = datetime.now(chicago_tz).date()

    if record_previous:
        selected_date = st.date_input(
            "Select date:",
            value=current_date_chicago,
            max_value=current_date_chicago,
            help=
            "Choose the date for the behavior entry (cannot be in the future)",
            format="MM/DD/YYYY")
    else:
        selected_date = current_date_chicago

    date_display = selected_date.strftime("%m/%d/%Y")
    st.write(f"**Recording for:** {date_display}")

    cols = st.columns(7)
    for i, color in enumerate(color_names):
        with cols[i]:
            # Wrap button in a styled div
            st.markdown(f'<div class="div-{color}">', unsafe_allow_html=True)
            if st.button(color,
                         key=f"color_{color}_{student_name}",
                         use_container_width=True):
                st.session_state.data_manager.add_behavior_entry(
                    student_name, color, selected_date.strftime("%Y-%m-%d"))
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

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

        # Re-added the subheader for the timeline and kept the space before it.
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
            # Removed the title from the layout to avoid duplication
            fig_timeline.update_layout(xaxis_title="Date",
                                       yaxis_title="Behavior Color",
                                       xaxis=dict(tickformat='%m/%d'),
                                       yaxis=dict(categoryorder='array',
                                                  categoryarray=color_names))
            st.plotly_chart(fig_timeline, use_container_width=True)

        # Add more space before the clear button and move it further right
        st.write("")
        st.write("")
        clear_col1, clear_col2 = st.columns([0.8, 0.2])
        with clear_col2:
            if st.button("Clear behavior data?",
                         key=f"clear_link_{student_name}",
                         help="Click to clear behavior data"):
                st.session_state[f'show_clear_dialog_{student_name}'] = True

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
