"""Zero-inference public tokenizer/config audit for the actual runtime profile."""
import hashlib
import json
from pathlib import Path

import preflight as p


def main():
    current_config = p.read(p.TOKENIZER / "config.json")
    current_tokenizer = p.read(p.TOKENIZER / "tokenizer_config.json")
    old_lock = p.read(p.ROOT / "tasks/085_r1_70b_autodl/identity_lock.json")
    old_config = old_lock["model"]["metadata"]["config.json"]["content"]
    old_tok_source = p.read(p.OLD / "tokenizer_source.json")
    profile = p.read(p.PUBLIC / "profile.json")
    result = {
        "status": "PUBLIC_SOURCE_AND_LOCAL_TOKENIZER_AUDIT_NO_INFERENCE",
        "actual_runtime_repo": p.MODEL,
        "public_repo_revision_downloaded": p.REVISION,
        "server_checkpoint_revision_independently_verified": False,
        "same_awq_configuration": current_config.get("quantization_config") == old_config.get("quantization_config"),
        "current_awq_configuration": current_config.get("quantization_config"),
        "old_awq_configuration": old_config.get("quantization_config"),
        "old_official_tokenizer_revision": old_tok_source["revision"],
        "old_chat_template_sha256": p.sha(p.OLD / "chat_template.jinja"),
        "actual_chat_template_sha256": hashlib.sha256(current_tokenizer["chat_template"].encode()).hexdigest(),
        "tokenizer_file_sha_matches_old_official": {
            name: profile["tokenizer_files"][name]["matches_old_official_revision"]
            for name in profile["tokenizer_files"]},
        "all_360_local_token_delta_from_old": profile["old_token_delta_stats"],
        "actual_tokenizer_config_max_length": current_tokenizer.get("model_max_length"),
        "served_max_model_len_from_live_models": p.read(p.PUBLIC / "service_identity.json")["max_model_len"],
        "no_weights_downloaded_for_this_audit": True,
        "GT_read": False,
    }
    if not result["same_awq_configuration"]:
        raise ValueError("AWQ configuration differs")
    path = p.PUBLIC / "compatibility.json"
    if not path.exists():
        p.put_json(path, result)
    else:
        old = p.read(path)
        if old != result:
            raise ValueError("existing compatibility audit differs")
    print(json.dumps({"same_awq_configuration": result["same_awq_configuration"],
                      "old_chat_template_sha256": result["old_chat_template_sha256"],
                      "actual_chat_template_sha256": result["actual_chat_template_sha256"],
                      "all_360_local_token_delta_from_old": result["all_360_local_token_delta_from_old"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
