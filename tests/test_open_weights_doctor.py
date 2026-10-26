import json
from pathlib import Path
from leafreel import open_weights as ow, doctor

def test_bundled_workflows_use_only_local_nodes():
    assert all(not v for v in ow.audit_offline().values())

def test_audit_flags_partner_nodes(tmp_path):
    wf = {"1": {"class_type": "KSampler", "inputs": {}}, "2": {"class_type": "ElevenLabsTextToSpeech", "inputs": {}}}
    (tmp_path / "x.api.json").write_text(json.dumps(wf))
    assert ow.audit_offline(tmp_path) == {"x.api.json": ["ElevenLabsTextToSpeech"]}
    oi = {"KSampler": {"category": "sampling"}, "ElevenLabsTextToSpeech": {"category": "partner/audio/ElevenLabs", "api_node": True}}
    assert ow.audit_live(oi, tmp_path) == {"x.api.json": ["ElevenLabsTextToSpeech"]}

def test_doctor_model_check_reports_missing_files_and_nodes():
    names = {"UNETLoader": {"input": {"required": {"unet_name": [["flux-2-klein-4b-fp8.safetensors", "acestep_v1.5_xl_turbo_bf16.safetensors"]]}}},
             "VAELoader": {"input": {"required": {"vae_name": [["flux2-vae.safetensors"]]}}}}
    oi = {t: names.get(t, {"input": {"required": {}}}) for t in ow.ALLOWED if t != "UnetLoaderGGUF"}
    oi.update(names)
    missing = doctor.check_models(oi)
    assert any("UnetLoaderGGUF" in m for m in missing["ltx25_i2v.api.json"])           # custom node not installed
    assert any("ace_1.5_vae" in m for m in missing["acestep15_music.api.json"])          # VAE file absent
    assert missing["flux2_klein_t2i.api.json"] == [] or all("clip_name" in m for m in missing["flux2_klein_t2i.api.json"])
