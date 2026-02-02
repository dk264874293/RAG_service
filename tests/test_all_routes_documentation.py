"""
测试所有API接口的说明文档完整性
验证所有接口都有中文说明
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.routes import (
    upload_router,
    retrieval_router,
    compliance_router,
    health_router,
    auth_router,
    markdown_router,
    vector_router,
)


def check_router_docstrings(router, router_name):
    """检查路由中的所有端点是否有docstring"""
    print(f"\n{'=' * 60}")
    print(f"检查 {router_name}")
    print(f"{'=' * 60}")

    routes_info = []

    for route in router.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            method = list(route.methods)[0] if route.methods else "UNKNOWN"
            path = route.path

            if (
                hasattr(route, "endpoint")
                and route.endpoint
                and hasattr(route.endpoint, "__doc__")
            ):
                docstring = route.endpoint.__doc__
                has_doc = docstring is not None and len(docstring.strip()) > 0
            else:
                has_doc = False
                docstring = None

            routes_info.append(
                {
                    "method": method,
                    "path": path,
                    "has_doc": has_doc,
                    "docstring": docstring,
                }
            )

            status = "✓" if has_doc else "✗"
            print(f"{status} {method:6} {path}")

            if has_doc and docstring:
                lines = docstring.strip().split("\n")
                first_line = lines[0] if lines else ""
                if any(ord(c) > 127 for c in first_line):
                    print(f"    包含非中文字符: {first_line[:50]}...")
                else:
                    print(f"    说明: {first_line[:60]}...")

    total_routes = len(routes_info)
    routes_with_doc = sum(1 for r in routes_info if r["has_doc"])

    print(f"\n总计: {total_routes} 个接口")
    print(
        f"有说明: {routes_with_doc} 个接口 ({routes_with_doc * 100 // total_routes if total_routes > 0 else 0}%)"
    )

    return routes_info


def main():
    print("开始检查所有API接口的说明文档...")
    print("验证所有接口都有中文说明\n")

    routers = [
        ("上传接口 (upload_router)", upload_router),
        ("语义检索接口 (retrieval_router)", retrieval_router),
        ("合规性检查接口 (compliance_router)", compliance_router),
        ("健康检查接口 (health_router)", health_router),
        ("认证接口 (auth_router)", auth_router),
        ("Markdown管理接口 (markdown_router)", markdown_router),
        ("向量管理接口 (vector_router)", vector_router),
    ]

    all_routes = []
    for router_name, router in routers:
        routes = check_router_docstrings(router, router_name)
        all_routes.extend(routes)

    total_all = len(all_routes)
    with_doc_all = sum(1 for r in all_routes if r["has_doc"])

    print(f"\n{'=' * 60}")
    print("整体统计")
    print(f"{'=' * 60}")
    print(f"总接口数: {total_all}")
    print(f"有说明的接口: {with_doc_all}")
    print(f"说明覆盖率: {with_doc_all * 100 // total_all if total_all > 0 else 0}%")

    if with_doc_all == total_all:
        print("\n✅ 所有接口都有说明文档！")
    else:
        print(f"\n⚠️  还有 {total_all - with_doc_all} 个接口缺少说明")


if __name__ == "__main__":
    main()
