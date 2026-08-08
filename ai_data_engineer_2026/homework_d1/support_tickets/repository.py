from typing import Any

from support_tickets.db import connection


Params = tuple[Any, ...]

TICKET_SELECT_QUERY = """
    SELECT
        t.ticket_id,
        t.title,
        t.created_by,
        t.created_at,
        c.category AS ticket_category,
        s.status AS ticket_status,
        t.ticket_category_id,
        t.ticket_status_id
    FROM tickets t
    LEFT JOIN ticket_category c ON c.ticket_category_id = t.ticket_category_id
    LEFT JOIN ticket_status s ON s.ticket_status_id = t.ticket_status_id
"""
GET_TICKET_QUERY = TICKET_SELECT_QUERY + " WHERE t.ticket_id = %s"
LIST_MESSAGES_QUERY = """
    SELECT message_id, ticket_id, message_text, author, created_at
    FROM ticket_messages
    WHERE ticket_id = %s
    ORDER BY created_at ASC, message_id ASC
"""
LIST_CATEGORIES_QUERY = """
    SELECT ticket_category_id, category
    FROM ticket_category
    ORDER BY category ASC
"""
LIST_STATUSES_QUERY = """
    SELECT ticket_status_id, status
    FROM ticket_status
    ORDER BY status ASC
"""
UPSERT_CATEGORY_QUERY = """
    INSERT INTO ticket_category (category)
    VALUES (%s)
    ON CONFLICT (category) DO UPDATE SET category = EXCLUDED.category
    RETURNING ticket_category_id
"""
UPSERT_STATUS_QUERY = """
    INSERT INTO ticket_status (status)
    VALUES (%s)
    ON CONFLICT (status) DO UPDATE SET status = EXCLUDED.status
    RETURNING ticket_status_id
"""
CREATE_TICKET_QUERY = """
    INSERT INTO tickets (
        title,
        ticket_category_id,
        ticket_status_id,
        created_by
    )
    VALUES (%s, %s, %s, %s)
"""
ADD_MESSAGE_QUERY = """
    INSERT INTO ticket_messages (ticket_id, message_text, author)
    VALUES (%s, %s, %s)
"""
UPDATE_TICKET_STATUS_QUERY = "UPDATE tickets SET ticket_status_id = %s WHERE ticket_id = %s"
UPDATE_TICKET_CATEGORY_QUERY = "UPDATE tickets SET ticket_category_id = %s WHERE ticket_id = %s"
COUNT_TICKETS_BY_STATUS_QUERY = """
    SELECT
        s.ticket_status_id,
        s.status,
        COUNT(t.ticket_id) AS ticket_count
    FROM ticket_status s
    LEFT JOIN tickets t ON t.ticket_status_id = s.ticket_status_id
    GROUP BY s.ticket_status_id, s.status
    ORDER BY s.status ASC
"""
COUNT_TICKETS_BY_CATEGORY_QUERY = """
    SELECT
        c.ticket_category_id,
        c.category,
        COUNT(t.ticket_id) AS ticket_count
    FROM ticket_category c
    LEFT JOIN tickets t ON t.ticket_category_id = c.ticket_category_id
    GROUP BY c.ticket_category_id, c.category
    ORDER BY c.category ASC
"""
DELETE_TICKET_QUERY = "DELETE FROM tickets WHERE ticket_id = %s"



def _fetch_all(query: str, params: Params = ()) -> list[dict[str, Any]]:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return list(cur.fetchall())



def _fetch_one(query: str, params: Params = ()) -> dict[str, Any] | None:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()



def _execute(query: str, params: Params = ()) -> None:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)



def _upsert_reference_value(query: str, id_column: str, value: str) -> int:
    row = _fetch_one(query, (value.strip(),))
    if row is None:
        raise RuntimeError(f"Failed to upsert reference value for {id_column}.")
    return int(row[id_column])



def list_tickets(status_id: int | None = None) -> list[dict[str, Any]]:
    query = TICKET_SELECT_QUERY
    params: Params = ()
    if status_id is not None:
        query += " WHERE t.ticket_status_id = %s"
        params = (status_id,)
    query += " ORDER BY t.created_at DESC, t.ticket_id DESC"
    return _fetch_all(query, params)



def get_ticket(ticket_id: int) -> dict[str, Any] | None:
    return _fetch_one(GET_TICKET_QUERY, (ticket_id,))



def list_messages(ticket_id: int) -> list[dict[str, Any]]:
    return _fetch_all(LIST_MESSAGES_QUERY, (ticket_id,))



def list_categories() -> list[dict[str, Any]]:
    return _fetch_all(LIST_CATEGORIES_QUERY)



def list_statuses() -> list[dict[str, Any]]:
    return _fetch_all(LIST_STATUSES_QUERY)



def upsert_category(category: str) -> int:
    return _upsert_reference_value(UPSERT_CATEGORY_QUERY, "ticket_category_id", category)



def upsert_status(status: str) -> int:
    return _upsert_reference_value(UPSERT_STATUS_QUERY, "ticket_status_id", status)



def create_ticket(title: str, created_by: str, category: str, status: str) -> None:
    category_id = upsert_category(category)
    status_id = upsert_status(status)
    _execute(CREATE_TICKET_QUERY, (title.strip(), category_id, status_id, created_by.strip()))



def add_message(ticket_id: int, message_text: str, author: str) -> None:
    _execute(ADD_MESSAGE_QUERY, (ticket_id, message_text.strip(), author.strip()))



def update_ticket_status(ticket_id: int, status: str) -> None:
    status_id = upsert_status(status)
    _execute(UPDATE_TICKET_STATUS_QUERY, (status_id, ticket_id))



def update_ticket_category(ticket_id: int, category: str) -> None:
    category_id = upsert_category(category)
    _execute(UPDATE_TICKET_CATEGORY_QUERY, (category_id, ticket_id))



def count_tickets_by_status() -> list[dict[str, Any]]:
    return _fetch_all(COUNT_TICKETS_BY_STATUS_QUERY)



def count_tickets_by_category() -> list[dict[str, Any]]:
    return _fetch_all(COUNT_TICKETS_BY_CATEGORY_QUERY)



def delete_ticket(ticket_id: int) -> None:
    _execute(DELETE_TICKET_QUERY, (ticket_id,))
