"""tests/precision_testing 公共 fixture。

把 ``backend/`` 注入 ``sys.path``,以便测试可以直接 ``import apps.precision_testing.*``,
不依赖 Django settings。
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def sample_django_views_source() -> str:
    """模拟一个 DRF ViewSet 文件,覆盖装饰器 / @action / 嵌套类等关键场景。"""
    return textwrap.dedent('''\
        from rest_framework import viewsets
        from rest_framework.decorators import action


        class ProjectViewSet(viewsets.ModelViewSet):
            queryset = []
            serializer_class = None

            def list(self, request):
                return None

            def create(self, request):
                return None

            @action(detail=True, methods=["post"])
                def archive(self, request, pk=None):
                return None

            @action(detail=False, methods=["get", "post"])
                def dashboard(self, request):
                return None


        async def health(request):
            return None


        def free_function(x):
            if x:
                return x + 1
            return 0
    ''').replace("    @action", "    @action").replace("        def ", "    def ")


@pytest.fixture
def viewset_source() -> str:
    """精确缩进的 ViewSet 源码,供 AST/路由解析共用。"""
    return (
        "from rest_framework import viewsets\n"
        "from rest_framework.decorators import action\n"
        "\n"
        "\n"
        "class ProjectViewSet(viewsets.ModelViewSet):\n"
        "    queryset = []\n"
        "    serializer_class = None\n"
        "\n"
        "    def list(self, request):\n"
        "        return None\n"
        "\n"
        "    def create(self, request):\n"
        "        return None\n"
        "\n"
        "    def retrieve(self, request, pk=None):\n"
        "        return None\n"
        "\n"
        "    @action(detail=True, methods=['post'])\n"
        "    def archive(self, request, pk=None):\n"
        "        return None\n"
        "\n"
        "    @action(detail=False, methods=['get', 'post'])\n"
        "    def dashboard(self, request):\n"
        "        return None\n"
        "\n"
        "\n"
        "async def health(request):\n"
        "    return None\n"
        "\n"
        "\n"
        "def free_function(x):\n"
        "    if x:\n"
        "        return x + 1\n"
        "    return 0\n"
    )


@pytest.fixture
def make_git_repo(tmp_path):
    """构造一个本地 Git 仓库的工厂 fixture。

    用法::

        repo, base, head = make_git_repo([
            ("apps/foo.py", "def a(): return 1\n"),
            ("apps/foo.py", "def a(): return 2\n"),  # 第二次提交=修改
        ])
    """
    from git import Actor, Repo

    def _factory(commits: list[tuple[str, str]]) -> tuple[Path, str, str]:
        repo_path = tmp_path / f"repo_{abs(hash(tuple(commits))) % 10**8}"
        repo_path.mkdir(parents=True, exist_ok=True)
        repo = Repo.init(str(repo_path), initial_branch="main")
        actor = Actor("Tester", "tester@example.com")
        shas: list[str] = []
        for path, content in commits:
            full = repo_path / path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
            repo.index.add([str(full.relative_to(repo_path)).replace("\\", "/")])
            commit = repo.index.commit(
                f"commit {len(shas) + 1}",
                author=actor,
                committer=actor,
            )
            shas.append(commit.hexsha)
        if len(shas) < 2:
            # 至少需要 base/head 两个提交;补一个空提交
            commit = repo.index.commit(
                "empty",
                author=actor,
                committer=actor,
            )
            shas.append(commit.hexsha)
        return repo_path, shas[0], shas[-1]

    return _factory
