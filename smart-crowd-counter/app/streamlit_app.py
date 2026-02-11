# Copyright 2026 Kamesh Sampath
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Import python packages
import streamlit as st
import io
import pandas as pd
import altair as alt
from snowflake.core import Root, CreateMode
from snowflake.core.stage import Stage, StageEncryption, StageDirectoryTable
from snowflake.snowpark.context import get_active_session
import time
import json

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Smart Crowd Counter",
    page_icon=":material/groups:",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session & deployment context
# ---------------------------------------------------------------------------
# The Streamlit runtime sets the session database/schema to the deployment
# target. All demo objects (schema, stage, view) live in this same database.

session = get_active_session()
root = Root(session)

_DATABASE = session.get_current_database()
_SCHEMA = session.get_current_schema()
_STAGE_NAME = "SNAPS"
_STAGE_FQN = f"@{_DATABASE}.{_SCHEMA}.{_STAGE_NAME}"
_VIEW_FQN = f"{_DATABASE}.{_SCHEMA}.SMART_CROWD_COUNTER"

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "selected_row" not in st.session_state:
    st.session_state.selected_row = []

if "files_uploaded" not in st.session_state:
    st.session_state.files_uploaded = False

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = set()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("Smart Crowd Counter :material/groups:")
st.write(
    """This Streamlit app helps track conference attendees and badge distribution
    using AI-powered image analysis.

    **How it works:**
    - Upload images (JPG, PNG, JPEG) from your conference sessions
    - AI analyzes the images to count total attendees and identify raised hands
    - View conversion rates and visualize badge distribution
    - Select any row from the table below to see detailed analytics

    **Get started:** Use the file uploader below to upload your session photos.
    """
)

st.caption(
    f"Database: `{_DATABASE}` | Schema: `{_SCHEMA}` | Stage: `{_STAGE_NAME}`"
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def refresh_data() -> pd.DataFrame:
    """Load all rows from the AI-powered view."""
    return session.sql(f"SELECT * FROM {_VIEW_FQN}").to_pandas()


def get_image_url_from_stage(file_json_str):
    """Get presigned URL for image from Snowflake stage using the file JSON."""
    try:
        if file_json_str is None:
            return None

        # Parse the JSON string to get file info
        if isinstance(file_json_str, str):
            file_obj = json.loads(file_json_str)
        else:
            file_obj = file_json_str

        # Extract stage and relative path
        stage = file_obj.get("STAGE")
        relative_path = file_obj.get("RELATIVE_PATH")

        if not stage or not relative_path:
            st.warning("Missing STAGE or RELATIVE_PATH in file metadata")
            return None

        # Get presigned URL (valid for 7 days = 604800 seconds)
        url_sql = (
            f"SELECT GET_PRESIGNED_URL('{stage}', '{relative_path}', 604800) as url"
        )
        result = session.sql(url_sql).collect()

        if result and len(result) > 0:
            return result[0][0]
        else:
            return None

    except Exception as e:
        st.error(f"Error getting presigned URL: {str(e)}")
        return None


def extract_filename_from_json(file_name_json):
    """Extract RELATIVE_PATH from the FILE_NAME JSON column."""
    try:
        if isinstance(file_name_json, str):
            file_info = json.loads(file_name_json)
            return file_info.get("RELATIVE_PATH", None)
        elif isinstance(file_name_json, dict):
            return file_name_json.get("RELATIVE_PATH", None)
        else:
            return None
    except (json.JSONDecodeError, AttributeError, TypeError) as e:
        st.warning(f"Could not parse filename JSON: {str(e)}")
        return None


def create_ratio_chart(row: pd.Series):
    """Create a donut chart showing attendees vs raised hands."""
    total_attendees = int(row["TOTAL_ATTENDEES"])
    raised_hands = float(row["RAISED_HANDS"])

    ratio_data = pd.DataFrame(
        {
            "Category": ["Total Attendees", "Raised Hands"],
            "Count": [total_attendees, raised_hands],
        }
    )

    chart = (
        alt.Chart(ratio_data.dropna())
        .mark_arc(innerRadius=50)
        .encode(
            theta=alt.Theta("Count:Q"),
            color=alt.Color(
                "Category:N", scale=alt.Scale(range=["#2ca02c", "#ff7f0e"])
            ),
            tooltip=["Category:N", "Count:Q"],
        )
        .properties(
            width=300,
            height=300,
        )
    )

    return chart


# ---------------------------------------------------------------------------
# Data initialisation
# ---------------------------------------------------------------------------

if "df" not in st.session_state:
    try:
        st.session_state.df = refresh_data()
    except Exception:
        st.session_state.df = pd.DataFrame()

# Refresh after file upload (flag set by upload handler)
if st.session_state.get("files_uploaded", False):
    try:
        st.session_state.df = refresh_data()
    except Exception as e:
        st.warning(f"Could not refresh data: {e}")
    st.session_state.files_uploaded = False

# ---------------------------------------------------------------------------
# Ensure stage exists (idempotent)
# ---------------------------------------------------------------------------

snap_stage = Stage(
    name=_STAGE_NAME,
    encryption=StageEncryption(type="SNOWFLAKE_SSE"),
    directory_table=StageDirectoryTable(enable=True, auto_refresh=True),
)
root.databases[_DATABASE].schemas[_SCHEMA].stages.create(
    snap_stage,
    mode=CreateMode.if_not_exists,
)

# ---------------------------------------------------------------------------
# File upload
# ---------------------------------------------------------------------------

_files = st.file_uploader(
    label="Upload a photo from conference session",
    accept_multiple_files=True,
    type=["jpg", "jpeg", "png"],
)

if _files is not None and len(_files) > 0:
    # Check if these are new files
    new_files = [f for f in _files if f.name not in st.session_state.uploaded_files]

    if new_files:
        upload_success = True
        upload_errors = []

        with st.spinner("Uploading files and refreshing data..."):
            for _file in new_files:
                _file_bytes = io.BytesIO(_file.getvalue())
                __stage_file = f"{_STAGE_FQN}/{_file.name}"

                try:
                    session.file.put_stream(
                        _file_bytes,
                        __stage_file,
                        auto_compress=False,
                        overwrite=True,
                    )
                    st.success(f"Uploaded: {_file.name}")
                    st.session_state.uploaded_files.add(_file.name)

                except Exception as e:
                    upload_errors.append(f"Error uploading {_file.name}: {str(e)}")
                    upload_success = False

            # Refresh stage after all uploads
            if upload_success and new_files:
                try:
                    session.sql(
                        f"ALTER STAGE {_STAGE_FQN[1:]} REFRESH"
                    ).collect()
                    st.success("Stage refreshed successfully!")

                    # Small delay to ensure processing is complete
                    time.sleep(2)

                    st.session_state.df = refresh_data()
                    st.session_state.files_uploaded = True

                except Exception as e:
                    st.error(f"Error refreshing stage: {str(e)}")
                    upload_success = False

            # Display any upload errors
            if upload_errors:
                for error in upload_errors:
                    st.error(error)

# Manual refresh button
if st.button("Refresh Data"):
    with st.spinner("Refreshing data..."):
        try:
            session.sql(f"ALTER STAGE {_STAGE_FQN[1:]} REFRESH").collect()
            time.sleep(2)
            st.session_state.df = refresh_data()
            st.session_state.files_uploaded = True
            st.success("Data refreshed successfully!")

        except Exception as e:
            st.error(f"Error refreshing data: {str(e)}")

# ---------------------------------------------------------------------------
# Data table
# ---------------------------------------------------------------------------

if not st.session_state.df.empty:
    event = st.dataframe(
        st.session_state.df,
        on_select="rerun",
        selection_mode="single-row",
        hide_index=True,
        column_config={
            "CAPTION": None,
            "FILE_NAME": None,
            "RAW": None,
        },
    )

    if event.selection:
        st.session_state.selected_row = event.selection.rows
else:
    st.info("No data available. Upload some files to get started!")

# ---------------------------------------------------------------------------
# Selected row details -- image + analytics
# ---------------------------------------------------------------------------

if st.session_state.selected_row and not st.session_state.df.empty:
    __idx = st.session_state.selected_row[0]
    if __idx < len(st.session_state.df):
        selected_row = st.session_state.df.iloc[__idx]

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader(":material/photo_camera: Session image")

            image_url = None
            filename = None

            if (
                "FILE_NAME" in selected_row.index
                and selected_row["FILE_NAME"]
            ):
                file_name_json = selected_row["FILE_NAME"]
                filename = extract_filename_from_json(file_name_json)

                with st.spinner("Getting image URL..."):
                    image_url = get_image_url_from_stage(file_name_json)

            caption = selected_row["CAPTION"]
            if image_url and filename:
                st.image(
                    image_url,
                    caption=f"Session: {caption}",
                    use_container_width=True,
                )

                # File metadata
                try:
                    file_info = (
                        json.loads(selected_row["FILE_NAME"])
                        if isinstance(selected_row["FILE_NAME"], str)
                        else selected_row["FILE_NAME"]
                    )

                    with st.expander(":material/description: File details"):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(
                                f"**Content Type:** {file_info.get('CONTENT_TYPE', 'N/A')}"
                            )
                            st.write(
                                f"**File Size:** {file_info.get('SIZE', 'N/A'):,} bytes"
                            )
                        with col_b:
                            st.write(
                                f"**Last Modified:** {file_info.get('LAST_MODIFIED', 'N/A')}"
                            )
                            st.write(
                                f"**ETag:** {file_info.get('ETAG', 'N/A')[:16]}..."
                            )
                except Exception as e:
                    st.warning(f"Could not parse file metadata: {str(e)}")

                # Analytics caption
                st.caption(
                    f"**Attendees:** {selected_row['TOTAL_ATTENDEES']} | "
                    f"**Raised Hands:** {selected_row['RAISED_HANDS']} | "
                    f"**Conversion:** {selected_row.get('PERCENTAGE_WITH_HANDS_UP', 'N/A')}%"
                )

            elif filename:
                st.error(f"Could not generate presigned URL for: {filename}")
                st.info(
                    "Check Snowflake permissions for GET_PRESIGNED_URL function"
                )
            else:
                st.info("No valid image file found in selected row")
                with st.expander(":material/bug_report: Debug info"):
                    st.write("Available columns:", list(selected_row.index))
                    if "FILE_NAME" in selected_row.index:
                        st.write(
                            "FILE_NAME content:",
                            selected_row["FILE_NAME"],
                        )
                        try:
                            parsed = (
                                json.loads(selected_row["FILE_NAME"])
                                if isinstance(selected_row["FILE_NAME"], str)
                                else selected_row["FILE_NAME"]
                            )
                            st.json(parsed)
                        except Exception as e:
                            st.write(
                                f"Could not parse FILE_NAME as JSON: {str(e)}"
                            )

        with col2:
            st.subheader(":material/analytics: Analytics")
            chart = create_ratio_chart(selected_row)
            st.altair_chart(chart, use_container_width=True)

            st.metric(
                label="Conversion Rate",
                value=f'{float(selected_row.get("PERCENTAGE_WITH_HANDS_UP", 0)):.1f}%',
                delta=None,
            )
            st.metric(
                label="Total Attendees",
                value=int(selected_row["TOTAL_ATTENDEES"]),
                delta=None,
            )
            st.metric(
                label="Raised Hands",
                value=int(selected_row["RAISED_HANDS"]),
                delta=None,
            )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.caption(f"Built using [Streamlit](https://streamlit.io) v{st.__version__}")
