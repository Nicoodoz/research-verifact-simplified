"""Offline replay into a new directory; frozen material checked, mutable docs excluded."""
from contextlib import ExitStack,redirect_stdout
from io import StringIO
from pathlib import Path
import argparse
import json
import shutil
import socket
import subprocess
import tempfile
from unittest.mock import patch
import common as c
import build_stages as bs
import check_preparation
import check_judge_inputs
import score_results


def verify(output):
    assert output.resolve().is_relative_to(c.OUT.resolve()),"Verification output must stay inside 008"
    output.mkdir(parents=True,exist_ok=False)
    unchanged={}
    protected=[c.OUT/"preparation_001",c.OUT/"plans_001",c.OUT/"candidates_001",c.OUT/"judge_preparation_001",c.OUT/"live",c.OUT/"run_001/analysis"]
    for directory in protected:
        for p in directory.rglob("*"):
            if p.is_file():
                unchanged[p]=c.pilot.digest_file(p)
    matching=[]
    with ExitStack() as stack:
        for name in ("socket.create_connection","socket.socket.connect","socket.socket.connect_ex"):
            stack.enter_context(patch(name,side_effect=AssertionError("008 offline verification blocks network")))
        stack.enter_context(patch("services.HttpClient.send",side_effect=AssertionError("No paid calls in replay")))
        preparation=check_preparation.check()
        judge_inputs=check_judge_inputs.check()
        for dirname in ("preparation_001","plans_001","candidates_001","judge_preparation_001","run_001/analysis"):
            manifest=c.check_files(c.OUT/dirname)
            for name,h in manifest.get("dependencies",{}).items():
                assert c.pilot.digest_file(c.ROOT/name)==h
            for name,h in manifest.get("code_sha256",{}).items():
                assert c.pilot.digest_file(c.ROOT/name)==h
        with redirect_stdout(StringIO()):
            score_results.score(output/"analysis_replay")
        for p in (c.OUT/"run_001/analysis").iterdir():
            if p.is_file() and p.name!="manifest.json":
                assert c.pilot.digest_file(p)==c.pilot.digest_file(output/"analysis_replay"/p.name),p.name
                matching.append(p.name)
        # Rebuild rankings and all future model bodies from original paid receipts.
        # A repository-local temporary parent keeps relative artifact links meaningful.
        with tempfile.TemporaryDirectory(prefix="008_offline_rebuild_",dir=c.OUT) as temporary:
            temp=Path(temporary)
            assert temp.resolve().is_relative_to(c.OUT.resolve()),"Temporary cleanup target escapes 008"
            for name in ("preparation_001","live"):
                # Junctions are unnecessary: copying only inputs/receipts preserves originals.
                shutil.copytree(c.OUT/name,temp/name)
            original_out=c.OUT
            with patch.object(c,"OUT",temp),redirect_stdout(StringIO()):
                bs.plans()
                bs.candidates()
                bs.judge()
            rebuilt=[]
            for name in ("plans_001","candidates_001","judge_preparation_001"):
                for p in (original_out/name).iterdir():
                    if p.is_file() and p.name!="manifest.json":
                        assert c.pilot.digest_file(p)==c.pilot.digest_file(temp/name/p.name),(name,p.name)
                        rebuilt.append(name+"/"+p.name)
    for p,h in unchanged.items():
        assert c.pilot.digest_file(p)==h,"Existing artifact changed during replay"
    result=dict(execution_self_check=True,independent_audit=False,network_disabled=True,api_calls=0,
        preparation=preparation,judge_inputs=judge_inputs,matching_analysis_files=matching,matching_rebuilt_files=rebuilt,
        protected_existing_files_unchanged=len(unchanged),mutable_readme_agents_reviews_not_freeze_dependencies=True,
        model_results_and_core_metrics_unchanged=True)
    c.pilot.write_json(output/"verification.json",result)
    print(c.pilot.canonical(result))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=c.OUT/"verification_001")
    args=parser.parse_args()
    verify(args.output)
