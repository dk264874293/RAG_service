import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.routes.vector import router


def test_vector_router_created():
    assert router is not None
    assert router.prefix == "/api/vector"
    assert "Vector Management" in router.tags

    routes = {r.path: r for r in router.routes}

    assert "/api/vector/stats" in routes
    assert "/api/vector/rebuild" in routes
    assert "/api/vector/clear" in routes

    print("✓ 向量路由已创建")

    routes_info = [f"  - {r.path} ({r.methods})" for r in router.routes]
    print("\n可用的向量管理接口:")
    print("\n".join(routes_info))


if __name__ == "__main__":
    test_vector_router_created()
