import pandas as pd
import streamlit as st

from support_tickets import repository as repo


PAGES = ["Create Ticket", "Update Ticket", "Statistics"]
NEW_STATUS = "New"
DELETED_STATUS = "Deleted"
TICKET_DISPLAY_COLUMNS = [
    "ticket_id",
    "title",
    "ticket_status",
    "ticket_category",
    "created_by",
    "created_at",
]
TICKET_DISPLAY_HEADERS = {
    "ticket_id": "Ticket ID",
    "title": "Title",
    "ticket_status": "Status",
    "ticket_category": "Category",
    "created_by": "Created By",
    "created_at": "Created At",
}
BLUE_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@600;700&display=swap');

.stApp {
    background: linear-gradient(180deg, #eef5ff 0%, #f8fbff 100%);
    color: #12345b;
    font-family: 'Inter', sans-serif;
}

h1, h2, h3 {
    font-family: 'Poppins', sans-serif;
    color: #0f3d91;
    letter-spacing: 0.01em;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f3d91 0%, #1f5fbf 100%);
}

[data-testid="stSidebar"] * {
    color: #ffffff;
}

[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid rgba(31, 95, 191, 0.16);
    border-radius: 16px;
    padding: 0.8rem;
    box-shadow: 0 10px 30px rgba(15, 61, 145, 0.08);
}

.stButton > button,
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #1f5fbf 0%, #4f8df0 100%);
    color: #ffffff;
    border: none;
    border-radius: 999px;
    font-weight: 600;
    box-shadow: 0 10px 24px rgba(31, 95, 191, 0.2);
}

.stButton > button:hover,
.stFormSubmitButton > button:hover {
    background: linear-gradient(135deg, #184e9b 0%, #3f7fe6 100%);
}

.stAlert,
[data-testid="stDataFrame"] {
    border-radius: 16px;
}

[data-baseweb="select"] > div,
.stTextInput input,
.stTextArea textarea {
    border-radius: 12px;
}

[data-testid="stDataFrame"] [role="columnheader"] {
    justify-content: center;
    text-align: center;
    font-weight: 700;
}
</style>
"""


def _apply_theme() -> None:
    st.markdown(BLUE_THEME_CSS, unsafe_allow_html=True)


def _extract_selected_rows(table_event: object) -> list[int]:
    selection = getattr(table_event, "selection", None)
    if selection is None and isinstance(table_event, dict):
        selection = table_event.get("selection")
    if selection is None:
        return []
    if hasattr(selection, "rows"):
        return list(selection.rows)
    if isinstance(selection, dict):
        return list(selection.get("rows", []))
    return []


def _render_ticket_messages(messages: list[dict]) -> None:
    st.markdown("### Messages")
    if messages:
        for message in messages:
            st.chat_message(message["author"]).write(message["message_text"])
            st.caption(str(message["created_at"]))
    else:
        st.info("No messages yet.")


def _render_create_page(category_options: list[str]) -> None:
    st.header("Create Ticket")
    st.caption("Create a new support ticket. New tickets are always created with New status.")

    if not category_options:
        st.warning("Categories are empty. Run the SQL setup scripts first, then refresh the app.")
        return

    left, right = st.columns([1.2, 1])
    with left:
        with st.form("create_ticket_form", clear_on_submit=True):
            title = st.text_input("Title", placeholder="Briefly describe the issue")
            created_by = st.text_input("Created by", placeholder="Your name or team")
            category = st.selectbox("Category", category_options)
            submitted = st.form_submit_button("Create ticket", type="primary")
            if submitted:
                if not title or not created_by:
                    st.error("Title and created by are required.")
                else:
                    repo.create_ticket(title, created_by, category, NEW_STATUS)
                    st.success("Ticket created.")
                    st.rerun()

    with right:
        st.subheader("Tips")
        st.markdown("* Use a short, clear title.")
        st.markdown("* Pick the closest category for faster triage.")
        st.markdown("* New tickets are automatically created with New status.")


def _render_update_page(category_options: list[str], status_rows: list[dict]) -> None:
    st.header("Update Ticket")
    st.caption("Review ticket details, update values, add messages, or delete a ticket.")

    status_values = [row["status"] for row in status_rows]
    filter_options = ["All"] + status_values
    selected_status = st.selectbox("Filter tickets by status", filter_options)
    filtered_status_id = None
    if selected_status != "All":
        filtered_status_id = next((row["ticket_status_id"] for row in status_rows if row["status"] == selected_status), None)

    tickets = repo.list_tickets(filtered_status_id)
    st.metric("Tickets shown", len(tickets))

    if not tickets:
        st.info("No tickets found for the selected filter.")
        return

    df = pd.DataFrame(tickets)[TICKET_DISPLAY_COLUMNS]
    display_df = df.rename(columns=TICKET_DISPLAY_HEADERS)
    st.caption("Click a row in the table to load the ticket details below.")
    table_event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="tickets_table",
    )

    selected_rows = _extract_selected_rows(table_event)
    visible_ticket_ids = df["ticket_id"].tolist()
    if selected_rows:
        selected_ticket_id = int(df.iloc[selected_rows[0]]["ticket_id"])
        st.session_state["selected_ticket_id"] = selected_ticket_id
    else:
        selected_ticket_id = st.session_state.get("selected_ticket_id")
        if selected_ticket_id not in visible_ticket_ids:
            selected_ticket_id = int(visible_ticket_ids[0])
            st.session_state["selected_ticket_id"] = selected_ticket_id

    ticket = repo.get_ticket(selected_ticket_id)
    messages = repo.list_messages(selected_ticket_id)

    if not ticket:
        st.warning("The selected ticket could not be loaded.")
        return

    current_category = ticket.get("ticket_category")
    current_status = ticket.get("ticket_status")
    is_deleted = current_status == DELETED_STATUS
    category_index = next((i for i, value in enumerate(category_options) if value == current_category), 0)
    status_index = next((i for i, value in enumerate(status_values) if value == current_status), 0)

    st.info(f"Selected ticket: #{selected_ticket_id}")
    if is_deleted:
        st.warning("This ticket is marked as Deleted and is now read-only.")

    st.divider()
    st.subheader("Section 1: Ticket Detail")
    detail_left, detail_right = st.columns(2)
    with detail_left:
        st.markdown(f"**Ticket ID:** {ticket['ticket_id']}")
        st.markdown(f"**Title:** {ticket['title']}")
        st.markdown(f"**Created by:** {ticket['created_by']}")
    with detail_right:
        st.markdown(f"**Status:** {ticket.get('ticket_status') or 'Unknown'}")
        st.markdown(f"**Category:** {ticket.get('ticket_category') or 'Uncategorized'}")
        st.markdown(f"**Created at:** {ticket['created_at']}")
    _render_ticket_messages(messages)

    st.divider()
    st.subheader("Section 2: Update Ticket")
    if not category_options or not status_values:
        st.warning("Categories or statuses are empty. Run the SQL setup scripts first, then refresh the app.")
    else:
        with st.form("update_ticket_form"):
            new_category = st.selectbox("New category", category_options, index=category_index, disabled=is_deleted)
            new_status = st.selectbox("New status", status_values, index=status_index, disabled=is_deleted)
            submitted = st.form_submit_button("Save changes", type="primary", disabled=is_deleted)
            if submitted:
                repo.update_ticket_category(selected_ticket_id, new_category)
                repo.update_ticket_status(selected_ticket_id, new_status)
                st.success("Ticket updated.")
                st.rerun()

    st.divider()
    st.subheader("Section 3: Add Message")
    with st.form("add_message_form"):
        author = st.text_input("Author", disabled=is_deleted)
        message_text = st.text_area("Message", disabled=is_deleted)
        submitted = st.form_submit_button("Add message", disabled=is_deleted)
        if submitted:
            if not author or not message_text:
                st.error("Author and message are required.")
            else:
                repo.add_message(selected_ticket_id, message_text, author)
                st.success("Message added.")
                st.rerun()

    st.divider()
    st.subheader("Section 4: Delete Ticket")
    confirm = st.checkbox(
        "I understand this will mark the ticket as Deleted.",
        disabled=is_deleted,
    )
    typed_id = st.text_input(
        "Type the ticket ID to confirm",
        placeholder=str(selected_ticket_id),
        disabled=is_deleted,
    )
    if st.button("Delete ticket", type="primary", disabled=is_deleted or not confirm):
        if typed_id.strip() != str(selected_ticket_id):
            st.error("Confirmation ticket ID does not match.")
        else:
            repo.update_ticket_status(selected_ticket_id, DELETED_STATUS)
            st.success("Ticket marked as Deleted.")
            st.rerun()


def _render_statistics_page() -> None:
    st.header("Statistics")
    st.caption("Simple ticket volume reports by status and category.")

    status_counts = repo.count_tickets_by_status()
    category_counts = repo.count_tickets_by_category()

    total_tickets = sum(int(row["ticket_count"]) for row in status_counts)
    st.metric("Total tickets", total_tickets)

    status_df = pd.DataFrame(status_counts)
    category_df = pd.DataFrame(category_counts)

    left, right = st.columns(2)
    with left:
        st.subheader("Tickets by Status")
        if not status_df.empty:
            display_df = status_df[["status", "ticket_count"]].rename(columns={"status": "Status", "ticket_count": "Tickets"})
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            st.bar_chart(display_df.set_index("Status"))
        else:
            st.info("No status data available.")

    with right:
        st.subheader("Tickets by Category")
        if not category_df.empty:
            display_df = category_df[["category", "ticket_count"]].rename(columns={"category": "Category", "ticket_count": "Tickets"})
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            st.bar_chart(display_df.set_index("Category"))
        else:
            st.info("No category data available.")


def render_app() -> None:
    st.set_page_config(page_title="Internal Support Tickets", layout="wide")
    _apply_theme()
    st.title("Internal Support Tickets")
    st.caption("Lakebase-backed Streamlit app for ticket tracking and messaging.")

    categories = repo.list_categories()
    statuses = repo.list_statuses()
    category_options = [row["category"] for row in categories]
    status_values = [row["status"] for row in statuses]

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", PAGES)

    if page == "Create Ticket":
        _render_create_page(category_options)
    elif page == "Update Ticket":
        _render_update_page(category_options, statuses)
    else:
        _render_statistics_page()
