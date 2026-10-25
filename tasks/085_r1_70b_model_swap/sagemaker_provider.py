"""SageMaker transport only. No container payload schema is assumed here."""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AwsTarget:
    region: str = "ap-northeast-1"
    profile: str | None = None
    endpoint_name: str | None = None
    inference_component_name: str | None = None

    @classmethod
    def from_env(cls, *, region: str | None = None, profile: str | None = None,
                 endpoint_name: str | None = None, inference_component_name: str | None = None):
        return cls(region=region or os.getenv("AWS_REGION") or "ap-northeast-1",
                   profile=profile or os.getenv("AWS_PROFILE") or None,
                   endpoint_name=endpoint_name or os.getenv("SAGEMAKER_ENDPOINT_NAME") or None,
                   inference_component_name=inference_component_name or os.getenv("SAGEMAKER_INFERENCE_COMPONENT_NAME") or None)


def _session(target: AwsTarget):
    import boto3  # lazy: importing this module or offline diagnostics cannot reach AWS
    return boto3.Session(region_name=target.region, profile_name=target.profile)


def offline_configuration(target: AwsTarget) -> dict[str, Any]:
    """No credentials read, no AWS API, no inference."""
    return {"region":target.region,"profile_configured":bool(target.profile),
            "endpoint_name":target.endpoint_name,"inference_component_name":target.inference_component_name,
            "endpoint_configured":bool(target.endpoint_name),"aws_calls":0,"inference_calls":0}


def identity_summary(session) -> dict[str, Any]:
    raw=session.client("sts").get_caller_identity()
    account=str(raw.get("Account") or "")
    arn=str(raw.get("Arn") or "")
    principal_type="assumed-role" if ":assumed-role/" in arn else "role" if ":role/" in arn else "user" if ":user/" in arn else "other"
    return {"authenticated":bool(account and arn),"account_masked":("*"*max(0,len(account)-4)+account[-4:]) if account else None,
            "principal_type":principal_type}


def endpoint_summary(session, target: AwsTarget) -> dict[str, Any]:
    if not target.endpoint_name:
        raise ValueError("SAGEMAKER_ENDPOINT_NAME is required for endpoint diagnosis")
    raw=session.client("sagemaker").describe_endpoint(EndpointName=target.endpoint_name)
    variants=[]
    for item in raw.get("ProductionVariants") or []:
        variants.append({"variant_name":item.get("VariantName"),
                         "current_weight":item.get("CurrentWeight"),
                         "current_instance_count":item.get("CurrentInstanceCount"),
                         "status":[x.get("Status") for x in item.get("VariantStatus") or []],
                         "instance_pools":[{"instance_type":x.get("InstanceType"),
                                            "current_instance_count":x.get("CurrentInstanceCount")}
                                           for x in item.get("InstancePools") or []]})
    out={"endpoint_name":raw.get("EndpointName"),"region":target.region,
         "endpoint_status":raw.get("EndpointStatus"),"in_service":raw.get("EndpointStatus")=="InService",
         "variants":variants,"inference_component_name":target.inference_component_name}
    if target.inference_component_name:
        component=session.client("sagemaker").describe_inference_component(InferenceComponentName=target.inference_component_name)
        if component.get("EndpointName") != target.endpoint_name:
            raise RuntimeError("Inference component belongs to another endpoint")
        out["inference_component_status"]=component.get("InferenceComponentStatus")
    return out


def diagnose(target: AwsTarget, *, session=None) -> dict[str, Any]:
    """Only STS and DescribeEndpoint/InferenceComponent; never invokes runtime."""
    actual=session or _session(target)
    result={"identity":identity_summary(actual),"endpoint":endpoint_summary(actual,target)}
    result["inference_calls"]=0
    return result


class SageMakerTransport:
    def __init__(self, target: AwsTarget, *, session=None):
        self.target=target
        self.session=session or _session(target)

    def _kwargs(self, payload: bytes, content_type: str, accept: str):
        if not self.target.endpoint_name:
            raise ValueError("Endpoint name not configured")
        if not isinstance(payload,bytes) or not payload:
            raise ValueError("Payload plugin must return nonempty bytes")
        if not content_type or not accept:
            raise ValueError("Payload plugin must provide ContentType and Accept")
        kw={"EndpointName":self.target.endpoint_name,"Body":payload,"ContentType":content_type,"Accept":accept}
        if self.target.inference_component_name:
            kw["InferenceComponentName"]=self.target.inference_component_name
        return kw

    def invoke(self, *, payload: bytes, content_type: str, accept: str,
               allow_inference: bool=False, require_inservice: bool=True) -> dict[str, Any]:
        if not allow_inference:
            raise PermissionError("--allow-inference is required; no endpoint request sent")
        kw=self._kwargs(payload,content_type,accept)
        if require_inservice and not endpoint_summary(self.session,self.target)["in_service"]:
            raise RuntimeError("Endpoint is not InService; no inference sent")
        # Caller must persist the raw Body bytes before parsing.
        return self.session.client("sagemaker-runtime").invoke_endpoint(**kw)

    def invoke_stream(self, *, payload: bytes, content_type: str, accept: str,
                      allow_inference: bool=False, streaming_verified: bool=False) -> dict[str, Any]:
        if not allow_inference or not streaming_verified:
            raise PermissionError("Explicit inference and verified container streaming are both required")
        kw=self._kwargs(payload,content_type,accept)
        if not endpoint_summary(self.session,self.target)["in_service"]:
            raise RuntimeError("Endpoint is not InService; no streaming request sent")
        return self.session.client("sagemaker-runtime").invoke_endpoint_with_response_stream(**kw)


def main():
    parser=argparse.ArgumentParser(description="Read-only AWS identity/endpoint diagnosis; never infer")
    parser.add_argument("--region")
    parser.add_argument("--profile")
    parser.add_argument("--endpoint-name")
    parser.add_argument("--inference-component-name")
    parser.add_argument("--live",action="store_true",help="Call only STS and SageMaker Describe; no runtime")
    args=parser.parse_args()
    target=AwsTarget.from_env(region=args.region,profile=args.profile,endpoint_name=args.endpoint_name,
                              inference_component_name=args.inference_component_name)
    if args.live:
        print(json.dumps(diagnose(target),ensure_ascii=False,sort_keys=True))
    else:
        print(json.dumps(offline_configuration(target),ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
