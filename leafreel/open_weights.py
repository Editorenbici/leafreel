"""Open-weights audit: the bundled workflows may only use local nodes (ComfyUI core + ComfyUI-GGUF), never partner/API nodes.

Offline check: every node type must be on the allow-list below. Live check (when ComfyUI is reachable): ComfyUI marks partner nodes with
`api_node: true` and a `partner/...` category in /object_info; none of the used nodes may carry that flag."""
import json
from pathlib import Path

CORE_NODES = ['CFGGuider', 'CLIPLoader', 'CLIPTextEncode', 'ConditioningZeroOut', 'CreateVideo', 'DualCLIPLoader', 'EmptyAceStep1.5LatentAudio', 'EmptyFlux2LatentImage', 'EmptyLTXVLatentVideo', 'Flux2Scheduler', 'KSampler', 'KSamplerSelect', 'LTXVAudioVAEDecode', 'LTXVConcatAVLatent', 'LTXVConditioning', 'LTXVDualCFGGuider', 'LTXVEmptyLatentAudio', 'LTXVImgToVideoInplace', 'LTXVLatentUpsampler', 'LTXVPreprocess', 'LTXVSeparateAVLatent', 'LatentUpscaleModelLoader', 'LoadImage', 'ManualSigmas', 'ModelSamplingAuraFlow', 'RandomNoise', 'ReferenceLatent', 'SamplerCustomAdvanced', 'SaveAudioAdvanced', 'SaveImage', 'SaveVideo', 'TextEncodeAceStepAudio1.5', 'UNETLoader', 'VAEDecode', 'VAEDecodeAudio', 'VAEDecodeTiled', 'VAEEncode', 'VAELoader']
COMMUNITY_NODES = ['UnetLoaderGGUF']   # ComfyUI-GGUF (Apache-2.0): loads the GGUF-quantized LTX-2.5 weights
ALLOWED = set(CORE_NODES) | set(COMMUNITY_NODES)
WF_DIR = Path(__file__).parent / "workflows"

def node_types(workflow: dict) -> set:
    return {n["class_type"] for n in workflow.values() if isinstance(n, dict) and "class_type" in n}

def audit_offline(workflow_dir=WF_DIR) -> dict:
    """{workflow file: sorted list of node types that are NOT on the allow-list} (empty list = clean)."""
    return {f.name: sorted(node_types(json.loads(f.read_text())) - ALLOWED) for f in sorted(Path(workflow_dir).glob("*.api.json"))}

def audit_live(object_info: dict, workflow_dir=WF_DIR) -> dict:
    """With a live /object_info: nodes flagged api_node (partner) or in a partner/ category, per workflow."""
    out = {}
    for f in sorted(Path(workflow_dir).glob("*.api.json")):
        bad = [t for t in sorted(node_types(json.loads(f.read_text()))) if object_info.get(t, {}).get("api_node") or str(object_info.get(t, {}).get("category", "")).startswith("partner")]
        out[f.name] = bad
    return out
