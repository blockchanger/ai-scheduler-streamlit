import json
from io import StringIO
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

from algorithms.resource_level import schedule_with_resources

st.set_page_config(page_title="AI-Powered Project Scheduling Assistant", layout="wide")

st.title("AI-Powered Project Scheduling Assistant")
st.caption("CPM + Greedy Resource-Leveling • Streamlit • Auto-deploy from GitHub")

with st.sidebar:
    st.header("Load / Save Project")
    sample_btn = st.button("Load Sample Project")
    uploaded_json = st.file_uploader("Upload Project JSON", type=["json"])
    uploaded_csv = st.file_uploader(
        "Upload Tasks CSV (id,name,durationDays,dependsOn,requiredResources)",
        type=["csv"]
    )
    st.markdown("---")
    st.header("Export")
    export_csv_btn = st.button("Download Schedule CSV")

# State
if "project" not in st.session_state:
    st.session_state.project = None
if "schedule" not in st.session_state:
    st.session_state.schedule = None
if "new_tasks" not in st.session_state:
    st.session_state.new_tasks = []

def parse_csv_to_project(csv_bytes: bytes):
    df = pd.read_csv(StringIO(csv_bytes.decode("utf-8"))).fillna("")
    tasks = []
    all_resources = set()
    for _, row in df.iterrows():
        depends = [d.strip() for d in str(row.get("dependsOn","")).split(";") if d.strip()]
        req = [r.strip() for r in str(row.get("requiredResources","")).split(";") if r.strip()]
        for r in req: all_resources.add(r)
        tasks.append(dict(
            id=str(row["id"]),
            name=str(row["name"]),
            durationDays=int(row["durationDays"]),
            dependsOn=depends,
            requiredResources=req
        ))
    return dict(
        startDateISO=datetime.now().date().isoformat(),
        resources=sorted(list(all_resources)),
        tasks=tasks
    )

def to_gantt_df(scheduled: list):
    df = pd.DataFrame([{
        "Task": t["name"],
        "ID": t["id"],
        "Start": t["start"],
        "Finish": t["end"],
        "Critical": "Critical" if t["critical"] else "Non-critical",
        "Resources": ", ".join(t.get("requiredResources", [])),
        "Slack": t.get("slack", 0),
        "ES": t.get("earliestStart"), "EF": t.get("earliestFinish"),
        "LS": t.get("latestStart"),   "LF": t.get("latestFinish")
    } for t in scheduled])
    if df.empty:
        return df
    df["Start"] = pd.to_datetime(df["Start"])
    df["Finish"] = pd.to_datetime(df["Finish"])
    return df

col_left, col_right = st.columns([1,1])

with col_left:
    st.subheader("Project Input")
    start_date = st.date_input("Project Start Date", value=datetime.now().date())
    resources_text = st.text_input("Resources (semicolon-separated)", value="FE;BE;DS")
    skip_weekends = st.checkbox("Skip weekends (no Sat/Sun)", value=True)

    st.markdown("**Add Task**")
    with st.form("add_task", clear_on_submit=True):
        tid = st.text_input("Task ID")
        tname = st.text_input("Task Name")
        tdur = st.number_input("Duration (days)", min_value=1, value=3, step=1)
        tdeps = st.text_input("Depends On (semicolon-separated IDs)")
        tres = st.text_input("Required Resources (semicolon-separated)")
        ok = st.form_submit_button("Add Task")
    if ok and tid and tname:
        dep_list = [d.strip() for d in tdeps.split(";") if d.strip()]
        res_list = [r.strip() for r in tres.split(";") if r.strip()]
        st.session_state.new_tasks.append(dict(
            id=tid, name=tname, durationDays=int(tdur),
            dependsOn=dep_list, requiredResources=res_list
        ))

    if sample_btn:
        with open("data/sample_project.json", "r") as f:
            sample = json.load(f)
        st.session_state.project = sample
        st.session_state.new_tasks = sample["tasks"].copy()
        st.success("Loaded sample project.")

    if uploaded_json:
        st.session_state.project = json.load(uploaded_json)
        st.session_state.new_tasks = st.session_state.project["tasks"].copy()
        st.success("Loaded JSON project.")

    if uploaded_csv:
        proj = parse_csv_to_project(uploaded_csv.getvalue())
        st.session_state.project = proj
        st.session_state.new_tasks = proj["tasks"].copy()
        st.success("Parsed CSV into project.")

    current_project = dict(
        startDateISO=start_date.isoformat(),
        resources=[r.strip() for r in resources_text.split(";") if r.strip()],
        tasks=st.session_state.new_tasks,
        skipWeekends=bool(skip_weekends),

    )

    st.text_area("Current Project (JSON)", value=json.dumps(current_project, indent=2), height=260)

    if st.button("Optimize Schedule"):
        try:
            scheduled = schedule_with_resources(current_project)
            st.session_state.schedule = scheduled
            st.success("Scheduling complete.")
        except Exception as e:
            st.error(f"Error: {e}")

with col_right:
    st.subheader("Tasks")
    if st.session_state.new_tasks:
        st.dataframe(pd.DataFrame(st.session_state.new_tasks), use_container_width=True, hide_index=True)
    else:
        st.info("No tasks yet. Add tasks on the left, or load sample/JSON/CSV.")

    st.subheader("Gantt Schedule")
    if st.session_state.schedule:
        gantt_df = to_gantt_df(st.session_state.schedule)
        if not gantt_df.empty:
            fig = px.timeline(
                gantt_df, x_start="Start", x_end="Finish", y="Task",
                color="Critical", hover_data=["ID","Resources","Slack","ES","EF","LS","LF"]
            )
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Run Optimize to see the Gantt chart.")

# Export
if export_csv_btn:
    if st.session_state.get("schedule"):
        out_df = pd.DataFrame(st.session_state.schedule)
        st.download_button("Download Scheduled Tasks CSV",
                           data=out_df.to_csv(index=False),
                           file_name="scheduled_tasks.csv",
                           mime="text/csv")
    else:
        st.warning("No schedule to export. Run Optimize first.")
