from starlette.testclient import TestClient
from app.models.team import Team
from app.models.request import RequestType


def test_keyset_pagination_no_duplicates_and_ordered(
    client: TestClient,
    alice_auth_headers: dict[str, str],
):
    """
    Keyset pagination with (last_activity_at DESC, id DESC) ensures:
    - Page 1 and Page 2 contain completely disjoint sets of items
    - Items within and across pages follow strict descending order
    """
    # 1. Fetch page 1
    page1_res = client.get("/requests?limit=10", headers=alice_auth_headers)
    assert page1_res.status_code == 200
    p1_data = page1_res.json()
    p1_items = p1_data["items"]
    assert len(p1_items) == 10
    assert p1_data["has_more"] is True
    cursor = p1_data["next_cursor"]
    assert cursor is not None

    # 2. Fetch page 2
    page2_res = client.get(f"/requests?limit=10&cursor={cursor}", headers=alice_auth_headers)
    assert page2_res.status_code == 200
    p2_data = page2_res.json()
    p2_items = p2_data["items"]
    assert len(p2_items) == 10

    # 3. Check for duplicates
    p1_ids = {item["id"] for item in p1_items}
    p2_ids = {item["id"] for item in p2_items}
    overlap = p1_ids.intersection(p2_ids)
    assert len(overlap) == 0, f"Found overlapping items across pages: {overlap}"

    # 4. Check sorting order: last item of page 1 >= first item of page 2
    last_p1 = (p1_items[-1]["last_activity_at"], p1_items[-1]["id"])
    first_p2 = (p2_items[0]["last_activity_at"], p2_items[0]["id"])
    assert last_p1 > first_p2, f"Expected {last_p1} > {first_p2}"


def test_keyset_pagination_stable_under_concurrent_inserts(
    client: TestClient,
    alice_auth_headers: dict[str, str],
    platform_team: Team,
    platform_types: dict[str, RequestType],
):
    """
    Keyset pagination does not shift or skip rows when a new item is inserted
    at the top of the table after reading page 1.
    """
    # Fetch page 1
    page1_res = client.get("/requests?limit=5", headers=alice_auth_headers)
    assert page1_res.status_code == 200
    p1_data = page1_res.json()
    cursor = p1_data["next_cursor"]

    # Insert a brand new request at the top
    client.post(
        "/requests",
        headers=alice_auth_headers,
        json={
            "team_id": str(platform_team.id),
            "type_id": str(platform_types["none"].id),
            "title": "Brand new top request",
        },
    )

    # Fetch page 2 with original cursor
    page2_res = client.get(f"/requests?limit=5&cursor={cursor}", headers=alice_auth_headers)
    assert page2_res.status_code == 200
    p2_data = page2_res.json()

    # The newly inserted row should not appear in page 2
    p2_titles = [i["title"] for i in p2_data["items"]]
    assert "Brand new top request" not in p2_titles

    # Page 1 and Page 2 still have zero overlap
    p1_ids = {i["id"] for i in p1_data["items"]}
    p2_ids = {i["id"] for i in p2_data["items"]}
    assert len(p1_ids.intersection(p2_ids)) == 0
