from pathlib import Path

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .connection_utils import (
    build_test_result,
    list_local_directory,
    list_remote_directory,
    open_cached_ssh_client,
    resolve_local_path,
    tail_local_file,
    tail_remote_file,
    test_mongo_connection,
    test_mysql_connection,
    test_redis_connection,
    test_ssh_connection,
    validate_remote_path,
)
from .models import (
    OpsEnvironment,
    OpsEnvironmentCategory,
    OpsEnvironmentCategoryDirectory,
)
from .serializers import (
    OpsEnvironmentCategorySerializer,
    OpsEnvironmentSerializer,
)


class OpsEnvironmentPagination(PageNumberPagination):
    """运维模块通用分页。"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class OpsEnvironmentCategoryViewSet(viewsets.ModelViewSet):
    """环境分类管理。"""

    queryset = OpsEnvironmentCategory.objects.all().prefetch_related("directories")
    serializer_class = OpsEnvironmentCategorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OpsEnvironmentPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_active"]

    def get_queryset(self):
        queryset = super().get_queryset()
        keyword = str(self.request.query_params.get("keyword", "")).strip()
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword)
                | Q(code__icontains=keyword)
                | Q(description__icontains=keyword)
                | Q(directories__name__icontains=keyword)
                | Q(directories__path__icontains=keyword)
            ).distinct()
        return queryset

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.environments.exists():
            return Response(
                {"detail": "该分类已关联环境，无法删除"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def active(self, request):
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class OpsEnvironmentViewSet(viewsets.ModelViewSet):
    """运维环境管理。"""

    queryset = OpsEnvironment.objects.all().select_related("category").prefetch_related("category__directories")
    serializer_class = OpsEnvironmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OpsEnvironmentPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["category", "environment_type", "access_mode", "is_active"]
    search_fields = ["name", "env_code", "ssh_host", "category__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        keyword = str(self.request.query_params.get("keyword", "")).strip()
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword)
                | Q(env_code__icontains=keyword)
                | Q(description__icontains=keyword)
                | Q(ssh_host__icontains=keyword)
                | Q(category__name__icontains=keyword)
                | Q(category__code__icontains=keyword)
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="import")
    def import_environments(self, request):
        """批量导入环境配置。"""

        payload = request.data
        items = payload.get("items", []) if isinstance(payload, dict) else payload
        if not isinstance(items, list) or not items:
            return Response({"detail": "请提供环境配置列表"}, status=status.HTTP_400_BAD_REQUEST)

        created = 0
        updated = 0
        errors = []
        for index, item in enumerate(items, start=1):
            env_code = str(item.get("env_code", "")).strip()
            if not env_code:
                errors.append({"index": index, "detail": "缺少 env_code"})
                continue

            instance = OpsEnvironment.objects.filter(env_code=env_code).first()
            serializer = self.get_serializer(instance=instance, data=item, partial=bool(instance))
            try:
                serializer.is_valid(raise_exception=True)
                if instance:
                    serializer.save(updated_by=request.user)
                    updated += 1
                else:
                    serializer.save(created_by=request.user, updated_by=request.user)
                    created += 1
            except serializers.ValidationError as exc:
                errors.append({"index": index, "env_code": env_code, "detail": exc.detail})

        return Response({"created": created, "updated": updated, "errors": errors})

    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, pk=None):
        """测试 SSH 和中间件连接。"""

        environment = self.get_object()
        ssh_config = {
            "host": environment.ssh_host,
            "port": environment.ssh_port,
            "username": environment.ssh_username,
            "password": environment.ssh_password,
        }

        ssh_result = test_ssh_connection(**ssh_config) if environment.ssh_host else build_test_result(False, "未配置 SSH")
        mysql_result = test_mysql_connection(environment.mysql_config or {}, ssh_config)
        redis_result = test_redis_connection(environment.redis_config or {}, ssh_config)
        mongo_result = test_mongo_connection(environment.mongo_config or {}, ssh_config)

        results = {
            "ssh": ssh_result,
            "mysql": mysql_result,
            "redis": redis_result,
            "mongo": mongo_result,
        }
        overall_success = all(item.get("success") or item.get("detail", {}).get("skipped") for item in results.values())
        return Response({"success": overall_success, "results": results})


class OpsLogViewSet(viewsets.ViewSet):
    """日志查询接口。"""

    permission_classes = [IsAuthenticated]

    def _get_environment(self, request):
        environment_id = request.query_params.get("environment_id") or request.data.get("environment_id")
        if not environment_id:
            raise serializers.ValidationError({"environment_id": "缺少环境 ID"})
        try:
            return OpsEnvironment.objects.select_related("category").prefetch_related("category__directories").get(
                pk=environment_id,
                is_active=True,
            )
        except OpsEnvironment.DoesNotExist as exc:
            raise serializers.ValidationError({"environment_id": "环境不存在或已停用"}) from exc

    def _get_directory(self, request, environment):
        directory_id = request.query_params.get("directory_id") or request.data.get("directory_id")
        queryset = environment.category.directories.filter(is_active=True).order_by("sort_order", "id") if environment.category else OpsEnvironmentCategoryDirectory.objects.none()
        if directory_id:
            directory = queryset.filter(id=directory_id).first()
        else:
            directory = queryset.first()
        if directory is None:
            raise serializers.ValidationError({"directory_id": "当前环境分类下没有可用目录"})
        return directory

    def _parse_keywords(self, request):
        keywords = request.query_params.getlist("keywords")
        if keywords:
            return keywords
        raw = request.query_params.get("keywords", "") or request.data.get("keywords", [])
        if isinstance(raw, list):
            return raw
        return [item.strip() for item in str(raw).split(",") if item.strip()]

    @action(detail=False, methods=["get"])
    def environments(self, request):
        queryset = (
            OpsEnvironment.objects.filter(is_active=True, category__isnull=False)
            .select_related("category")
            .prefetch_related("category__directories")
            .order_by("category__sort_order", "category__id", "name")
        )
        serializer = OpsEnvironmentSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def connect(self, request):
        environment = self._get_environment(request)
        directory = self._get_directory(request, environment)

        if environment.access_mode == OpsEnvironment.ACCESS_SSH:
            connect_result = test_ssh_connection(
                environment.ssh_host,
                environment.ssh_port,
                environment.ssh_username,
                environment.ssh_password,
            )
        else:
            root = Path(directory.path).expanduser().resolve(strict=False)
            connect_result = build_test_result(root.exists() and root.is_dir(), "本机目录可用" if root.exists() and root.is_dir() else "本机目录不可用")

        return Response(
            {
                "success": connect_result["success"],
                "connection": connect_result,
                "environment": OpsEnvironmentSerializer(environment).data,
                "directories": list(
                    environment.category.directories.filter(is_active=True).values(
                        "id",
                        "name",
                        "path",
                        "sort_order",
                    )
                ),
                "selected_directory": {
                    "id": directory.id,
                    "name": directory.name,
                    "path": directory.path,
                },
            }
        )

    @action(detail=False, methods=["post"])
    def disconnect(self, request):
        return Response({"success": True, "message": "连接已断开"})

    @action(detail=False, methods=["get"])
    def browser(self, request):
        environment = self._get_environment(request)
        directory = self._get_directory(request, environment)
        relative_path = request.query_params.get("path", "")

        try:
            if environment.access_mode == OpsEnvironment.ACCESS_SSH:
                with open_cached_ssh_client(
                    environment.ssh_host,
                    environment.ssh_port,
                    environment.ssh_username,
                    environment.ssh_password,
                ) as ssh_client:
                    current_path, items = list_remote_directory(
                        ssh_client,
                        directory.path,
                        relative_path,
                    )
            else:
                root = Path(directory.path).expanduser().resolve(strict=False)
                current_path, items = list_local_directory(root, relative_path)
        except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": f"目录读取失败: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parent_path = ""
        if current_path:
            parts = current_path.split("/")
            parent_path = "/".join(parts[:-1])

        return Response(
            {
                "environment": {"id": environment.id, "name": environment.name},
                "directory": {"id": directory.id, "name": directory.name, "path": directory.path},
                "current_path": current_path,
                "parent_path": parent_path,
                "items": items,
            }
        )

    @action(detail=False, methods=["get"])
    def content(self, request):
        environment = self._get_environment(request)
        directory = self._get_directory(request, environment)
        relative_path = request.query_params.get("path", "")
        lines = min(max(int(request.query_params.get("lines", 200)), 20), 3000)
        keywords = self._parse_keywords(request)
        if not relative_path:
            return Response({"detail": "缺少文件路径"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if environment.access_mode == OpsEnvironment.ACCESS_SSH:
                with open_cached_ssh_client(
                    environment.ssh_host,
                    environment.ssh_port,
                    environment.ssh_username,
                    environment.ssh_password,
                ) as ssh_client:
                    payload = tail_remote_file(
                        ssh_client,
                        directory.path,
                        relative_path,
                        lines,
                    )
            else:
                root = Path(directory.path).expanduser().resolve(strict=False)
                payload = tail_local_file(root, relative_path, lines)
        except (FileNotFoundError, IsADirectoryError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": f"日志读取失败: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload["keywords"] = keywords
        return Response(payload)

    @action(detail=False, methods=["get"], url_path="download")
    def download(self, request):
        from django.http import HttpResponse

        environment = self._get_environment(request)
        directory = self._get_directory(request, environment)
        relative_path = request.query_params.get("path", "")
        if not relative_path:
            return Response({"detail": "缺少文件路径"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if environment.access_mode == OpsEnvironment.ACCESS_SSH:
                with open_cached_ssh_client(
                    environment.ssh_host,
                    environment.ssh_port,
                    environment.ssh_username,
                    environment.ssh_password,
                ) as ssh_client:
                    _, target = validate_remote_path(directory.path, relative_path)
                    sftp = ssh_client.open_sftp()
                    with sftp.open(target, "rb") as file_obj:
                        content = file_obj.read()
                    sftp.close()
                    filename = Path(target).name
            else:
                root = Path(directory.path).expanduser().resolve(strict=False)
                _, target = resolve_local_path(root, relative_path)
                if not target.exists() or not target.is_file():
                    return Response(
                        {"detail": "文件不存在"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                content = target.read_bytes()
                filename = target.name
        except (FileNotFoundError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": f"文件下载失败: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = HttpResponse(content, content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

