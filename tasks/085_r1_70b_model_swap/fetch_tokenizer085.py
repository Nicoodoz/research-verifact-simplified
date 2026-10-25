"""Download only four pinned official tokenizer/config files; never model weights."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download
import huggingface_hub

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/085_r1_70b_model_swap"
CACHE = ROOT / ".local_models/085a_r1_tokenizer"
REPO = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"
ALLOWED = ("config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json")


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert OUT.exists() and not (OUT / "tokenizer_source.json").exists()
    info = HfApi().model_info(REPO)
    listed = {x.rfilename for x in info.siblings}
    assert set(ALLOWED) <= listed
    assert all(not x.endswith((".safetensors", ".bin", ".pt", ".pth")) for x in ALLOWED)
    revision = info.sha
    assert len(revision) == 40
    CACHE.mkdir(parents=True, exist_ok=True)
    files = {}
    for name in ALLOWED:
        path = Path(hf_hub_download(repo_id=REPO, filename=name, revision=revision,
                                    local_dir=CACHE, force_download=False))
        assert path.resolve().parent == CACHE.resolve()
        assert path.stat().st_size < 25_000_000
        files[name] = {"sha256": sha(path), "bytes": path.stat().st_size}
    visible = {x.name for x in CACHE.iterdir() if x.is_file()}
    assert visible == set(ALLOWED), ("unexpected visible file", sorted(visible - set(ALLOWED)))
    assert not any(p.suffix.lower() in (".safetensors", ".bin", ".pt", ".pth") for p in CACHE.rglob("*"))
    record = {"repo": REPO, "revision": revision,
              "source": f"https://huggingface.co/{REPO}/tree/{revision}",
              "allowed_files_only": list(ALLOWED), "files": files,
              "cache_location": ".local_models/085a_r1_tokenizer (gitignored; no weights)",
              "python": sys.version.split()[0], "huggingface_hub": huggingface_hub.__version__,
              "downloaded_weights": False, "inference_calls": 0}
    (OUT / "tokenizer_source.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"revision":revision,"files":files,"weight_files":0},ensure_ascii=False))


if __name__ == "__main__":
    main()
