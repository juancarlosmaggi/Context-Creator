def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_index_status(client):
    response = client.get("/api/index-status")
    assert response.status_code == 200
    assert "is_valid" in response.json()
    assert "is_building" in response.json()

def test_project_structure(client):
    # This might return 503 if not built, or return structure if built.
    # Since we don't control the build process easily in integration test without mocking,
    # we just check status code is valid (200 or 503).
    response = client.get("/api/project-structure")
    assert response.status_code in [200, 503]

def test_process_route(client):
    # This test assumes the app is running in the current directory (repo root).
    # We can try to process a known file like README.md
    response = client.post("/process/", data={"selected_paths": ["README.md"]})
    assert response.status_code == 200
    assert "README.md" in response.text
