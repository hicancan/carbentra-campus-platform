"""Cheap packaging invariants; actual image builds remain a separate evidence gate."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def test_single_edge_source_and_contract_are_image_inputs():
    dockerfile = (ROOT / 'infra/edge.Dockerfile').read_text(encoding="utf-8")
    compose = (ROOT / 'compose.transport.yaml').read_text(encoding="utf-8")
    assert 'COPY pyproject.toml uv.lock .python-version ' in dockerfile
    assert 'uv sync --locked --only-group edge' in dockerfile
    assert 'edge/*.py /app/edge/' in dockerfile
    assert 'packages/iot-contract /app/packages/iot-contract' in dockerfile
    assert 'hardware_edge' not in dockerfile
    assert 'hardware_contracts' not in dockerfile
    assert 'CARBENTRA_HARDWARE_ROOT' not in compose
    assert 'additional_contexts' not in compose
    assert 'CARBENTRA_ENABLE_PHYSICAL_DISPATCH: "false"' in compose
    assert "CARBENTRA_PHYSICAL_RELEASES_JSON: '{}'" in compose
    assert '--enable-ble' not in compose

def test_backend_runtime_and_reload_share_authoritative_contract():
    assert 'packages/iot-contract/' in (ROOT / 'backend/Dockerfile').read_text(encoding="utf-8")
    assert (ROOT / 'compose.dev.yaml').read_text(encoding="utf-8").count('./packages/iot-contract:/app/packages/iot-contract:ro') == 2

def test_upgrade_snapshot_includes_new_runtime_inputs():
    text = (ROOT / 'tools/snapshot_system_upgrade.py').read_text(encoding="utf-8")
    assert "'edge'" in text and "'packages/iot-contract'" in text
    assert "*ROOT.glob('compose*.yaml')" in text

def test_browser_readiness_and_wrapped_labels_are_bounded_correctly():
    script = (ROOT / 'tests/system_upgrade/browser.mjs').read_text(encoding="utf-8")
    assert "locator('#main-content').waitFor({timeout:readTimeout})" in script
    assert "getByLabel(/^本次通道动作/)" in script
    assert "getByLabel(/^此通道人工接管时限/)" in script
    assert 'chromiumSandbox:true' in script
    assert 'fullPage:false' in script
