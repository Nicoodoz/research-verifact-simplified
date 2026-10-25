"""Small follow-up to make remaining live policy references unambiguous."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(rel, old, new):
    p = ROOT / rel
    b = p.read_bytes()
    o = old.encode("utf-8")
    if b.count(o) != 1:
        raise RuntimeError(f"expected one occurrence: {rel}: {old[:60]}")
    p.write_bytes(b.replace(o, new.encode("utf-8"), 1))


def main():
    replace_once("docs/API_POLICY.md", "本次审计和文档同步没有新增收费调用或查询余额。", "本政策文件不触发收费调用或余额查询；068新增请求单独按10元总上限登记。")
    replace_once("docs/aliyun/CURRENT.md", "本轮仅更新现行说明，没有新的API请求或余额探测，也没有声称统一跨平台自动路由器已经实现。", "本节原同步没有API请求或余额探测；068的新增请求由其独立10元账本记录，未声称统一跨平台自动路由器已经实现。")


if __name__ == "__main__":
    main()
