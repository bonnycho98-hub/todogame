def test_create_and_list_npc(client):
    res = client.post("/api/npcs", json={"name": "엄마", "relation_type": "가족"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "엄마"
    assert data["sprite"]  # 자동 생성됨

    res2 = client.get("/api/npcs")
    assert res2.status_code == 200
    assert any(n["name"] == "엄마" for n in res2.json())


def test_create_quest_with_subtask_and_complete(client):
    npc = client.post("/api/npcs", json={"name": "친구", "relation_type": "친구"}).json()
    need = client.post("/api/needs", json={"npc_id": npc["id"], "title": "연락받고싶어함"}).json()
    quest = client.post("/api/quests", json={
        "need_id": need["id"], "title": "주 1회 전화",
        "quest_type": "daily", "routine": {"type": "daily"}, "intimacy_reward": 20
    }).json()
    st = client.post("/api/subtasks", json={
        "quest_id": quest["id"], "title": "안부 묻기", "order": 0
    }).json()

    res = client.post(f"/api/subtasks/{st['id']}/complete")
    assert res.status_code == 200
    result = res.json()
    assert result["subtask_done"] is True
    assert result["quest_done"] is True


def test_dashboard_returns_data(client):
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "happiness" in data
    assert data["happiness"]["level"] >= 1


def test_level_reward_create_and_claim(client):
    res = client.post("/api/rewards", json={"level": 99, "message": "케이크 사먹기"})
    assert res.status_code == 201
    reward_id = res.json()["id"]

    res2 = client.post(f"/api/rewards/{reward_id}/claim")
    assert res2.status_code == 200
    assert res2.json()["is_claimed"] is True

    res3 = client.post(f"/api/rewards/{reward_id}/claim")
    assert res3.status_code == 400


def test_need_is_not_archived_by_default(client):
    npc = client.post("/api/npcs", json={"name": "테스트NPC", "relation_type": "기타"}).json()
    need = client.post("/api/needs", json={"npc_id": npc["id"], "title": "테스트 니즈"}).json()
    assert need["is_archived"] is False


def test_complete_need_archives_it(client):
    npc = client.post("/api/npcs", json={"name": "니즈완료테스트NPC", "relation_type": "기타"}).json()
    need = client.post("/api/needs", json={"npc_id": npc["id"], "title": "완료할 니즈"}).json()

    res = client.post(f"/api/needs/{need['id']}/complete")
    assert res.status_code == 200
    assert res.json()["done"] is True

    # 목록에서 제외됐는지 확인
    needs_list = client.get(f"/api/needs?npc_id={npc['id']}").json()
    assert not any(n["id"] == need["id"] for n in needs_list)


def test_dashboard_npc_includes_needs(client):
    npc = client.post("/api/npcs", json={"name": "대시보드테스트NPC", "relation_type": "기타"}).json()
    client.post("/api/needs", json={"npc_id": npc["id"], "title": "대시보드용 니즈"})

    res = client.get("/api/dashboard")
    assert res.status_code == 200
    dashboard = res.json()

    npc_data = next((n for n in dashboard["npcs"] if n["name"] == "대시보드테스트NPC"), None)
    assert npc_data is not None
    assert "needs" in npc_data
    assert any(n["title"] == "대시보드용 니즈" for n in npc_data["needs"])


def test_double_complete_need_returns_409(client):
    npc = client.post("/api/npcs", json={"name": "409테스트NPC", "relation_type": "기타"}).json()
    need = client.post("/api/needs", json={"npc_id": npc["id"], "title": "중복완료 니즈"}).json()
    client.post(f"/api/needs/{need['id']}/complete")
    res = client.post(f"/api/needs/{need['id']}/complete")
    assert res.status_code == 409
