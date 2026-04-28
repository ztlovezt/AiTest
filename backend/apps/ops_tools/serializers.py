from rest_framework import serializers

from .models import (
    OpsEnvironment,
    OpsEnvironmentCategory,
    OpsEnvironmentCategoryDirectory,
)


class OpsEnvironmentCategoryDirectorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OpsEnvironmentCategoryDirectory
        fields = [
            "id",
            "name",
            "path",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class OpsEnvironmentCategorySerializer(serializers.ModelSerializer):
    directories = OpsEnvironmentCategoryDirectorySerializer(many=True, required=False)
    directory_count = serializers.SerializerMethodField()

    class Meta:
        model = OpsEnvironmentCategory
        fields = [
            "id",
            "name",
            "code",
            "description",
            "sort_order",
            "is_active",
            "directory_count",
            "directories",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "directory_count"]

    def get_directory_count(self, obj):
        return obj.directories.count()

    def create(self, validated_data):
        directories = validated_data.pop("directories", [])
        instance = OpsEnvironmentCategory.objects.create(**validated_data)
        self._save_directories(instance, directories)
        return instance

    def update(self, instance, validated_data):
        directories = validated_data.pop("directories", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if directories is not None:
            self._save_directories(instance, directories)
        return instance

    def validate_directories(self, value):
        normalized_paths = set()
        normalized_items = []

        for index, item in enumerate(value or [], start=1):
            name = str(item.get("name", "")).strip()
            path = str(item.get("path", "")).strip()
            if not name or not path:
                raise serializers.ValidationError(f"第 {index} 个目录名称和路径不能为空")
            if path in normalized_paths:
                raise serializers.ValidationError(f"目录路径不能重复: {path}")

            normalized_paths.add(path)
            normalized_items.append(
                {
                    **item,
                    "name": name,
                    "path": path,
                    "sort_order": item.get("sort_order", 0) or 0,
                    "is_active": item.get("is_active", True),
                }
            )

        return normalized_items

    def _save_directories(self, category, directories):
        existing_map = {item.id: item for item in category.directories.all()}
        existing_path_map = {item.path: item for item in category.directories.all()}
        keep_ids = []

        for item in directories:
            item_id = item.get("id")
            payload = {
                "name": item.get("name", ""),
                "path": item.get("path", ""),
                "sort_order": item.get("sort_order", 0),
                "is_active": item.get("is_active", True),
            }
            if item_id and item_id in existing_map:
                directory = existing_map[item_id]
            elif payload["path"] in existing_path_map:
                directory = existing_path_map[payload["path"]]
            else:
                directory = OpsEnvironmentCategoryDirectory(category=category)

            for key, value in payload.items():
                setattr(directory, key, value)
            directory.category = category
            directory.save()
            keep_ids.append(directory.id)
            existing_path_map[directory.path] = directory

        if keep_ids:
            category.directories.exclude(id__in=keep_ids).delete()
        else:
            category.directories.all().delete()


class OpsEnvironmentSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)
    updated_by_name = serializers.CharField(source="updated_by.username", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_code = serializers.CharField(source="category.code", read_only=True)
    category_directories = OpsEnvironmentCategoryDirectorySerializer(
        source="category.directories",
        many=True,
        read_only=True,
    )

    class Meta:
        model = OpsEnvironment
        fields = [
            "id",
            "category",
            "category_name",
            "category_code",
            "category_directories",
            "name",
            "env_code",
            "environment_type",
            "access_mode",
            "description",
            "log_root",
            "ssh_host",
            "ssh_port",
            "ssh_username",
            "ssh_password",
            "client_url",
            "admin_url",
            "official_url",
            "image_host",
            "mysql_config",
            "redis_config",
            "mongo_config",
            "extra_config",
            "is_active",
            "created_by",
            "updated_by",
            "created_by_name",
            "updated_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_by",
            "updated_by",
            "created_by_name",
            "updated_by_name",
            "category_name",
            "category_code",
            "category_directories",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        instance = self.instance
        category = attrs.get("category", getattr(instance, "category", None))
        access_mode = attrs.get("access_mode", getattr(instance, "access_mode", OpsEnvironment.ACCESS_SSH))
        ssh_host = attrs.get("ssh_host", getattr(instance, "ssh_host", ""))
        ssh_username = attrs.get("ssh_username", getattr(instance, "ssh_username", ""))
        mysql_config = attrs.get("mysql_config", getattr(instance, "mysql_config", {})) or {}
        redis_config = attrs.get("redis_config", getattr(instance, "redis_config", {})) or {}
        mongo_config = attrs.get("mongo_config", getattr(instance, "mongo_config", {})) or {}

        if category is None:
            raise serializers.ValidationError({"category": "请选择环境分类"})

        if access_mode == OpsEnvironment.ACCESS_SSH:
            if not ssh_host:
                raise serializers.ValidationError({"ssh_host": "SSH 模式下必须填写主机地址"})
            if not ssh_username:
                raise serializers.ValidationError({"ssh_username": "SSH 模式下必须填写用户名"})

        for field_name, config in {
            "mysql_config": mysql_config,
            "redis_config": redis_config,
            "mongo_config": mongo_config,
        }.items():
            if not isinstance(config, dict):
                raise serializers.ValidationError({field_name: "配置必须是对象"})
            if config.get("use_ssh") and (not ssh_host or not ssh_username):
                raise serializers.ValidationError({field_name: "开启 SSH 连接时，需先填写环境 SSH 信息"})

        return attrs
