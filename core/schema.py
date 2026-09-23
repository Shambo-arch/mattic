from drf_spectacular.openapi import AutoSchema


class EnvelopeAutoSchema(AutoSchema):
    def _get_response_for_code(self, serializer, status_code, media_types=None, direction="response"):
        response = super()._get_response_for_code(serializer, status_code, media_types, direction)
        for media_type, content in response.get("content", {}).items():
            if media_type == "application/json" and "schema" in content:
                content["schema"] = {
                    "type": "object",
                    "required": ["success", "message", "data"],
                    "properties": {
                        "success": {"type": "boolean"},
                        "message": {"type": "string"},
                        "data": content["schema"],
                    },
                }
        return response
