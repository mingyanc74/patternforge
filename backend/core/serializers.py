from rest_framework import serializers


class ConnectionInput(serializers.Serializer):
    access_key = serializers.CharField(min_length=3, max_length=128, trim_whitespace=True, write_only=True)
    secret_key = serializers.CharField(min_length=8, max_length=256, trim_whitespace=False, write_only=True)
    session_token = serializers.CharField(max_length=4096, required=False, allow_blank=True, write_only=True)
    bucket = serializers.RegexField(r"^[a-zA-Z0-9][a-zA-Z0-9.\-_]{1,253}[a-zA-Z0-9]$")
    region = serializers.RegexField(r"^[a-z0-9-]{3,32}$", default="us-east-1")


class FileInput(serializers.Serializer):
    connection_id = serializers.UUIDField()
    source_key = serializers.CharField(max_length=1024, trim_whitespace=False)
    sheet = serializers.CharField(max_length=255, required=False, allow_blank=True)
    delimiter = serializers.ChoiceField(choices=[",", ";", "\t", "|"], default=",")
    encoding = serializers.ChoiceField(choices=["UTF-8", "UTF-16", "ISO-8859-1"], default="UTF-8")


class JobInput(FileInput):
    inspection_id = serializers.UUIDField()
    operation = serializers.ChoiceField(choices=["regex_replace", "regex_extract", "normalize"])
    prompt = serializers.CharField(min_length=3, max_length=4000)
    target_columns = serializers.ListField(
        child=serializers.CharField(max_length=255), min_length=1, max_length=50
    )
    replacement = serializers.CharField(
        max_length=4000, required=False, allow_blank=True, trim_whitespace=False
    )
    new_column = serializers.RegexField(r"^[\w][\w .-]{0,127}$", required=False)

    def validate(self, attrs):
        if attrs["operation"] == "regex_replace" and "replacement" not in attrs:
            raise serializers.ValidationError(
                {"replacement": "A replacement is required; empty string is allowed."}
            )
        if len(set(attrs["target_columns"])) != len(attrs["target_columns"]):
            raise serializers.ValidationError({"target_columns": "Choose each column only once."})
        if attrs["operation"] == "regex_extract":
            if len(attrs["target_columns"]) != 1 or not attrs.get("new_column"):
                raise serializers.ValidationError(
                    "Extraction requires one source column and a new column name."
                )
        return attrs
