from pydantic import BaseModel
try:
    # pydantic v2 serializer
    from pydantic import model_serializer  # type: ignore
except Exception:  # pragma: no cover
    model_serializer = None  # type: ignore


class Password(BaseModel):
    # Store the hashed value internally on the 'password' attribute.
    password: str

    # When serializing (to Mongo or API), emit the Java-compatible key 'encryptedPassword'.
    if model_serializer:
        @model_serializer(mode="plain")  # type: ignore
        def serialize_model(self):  # pragma: no cover - behavior verified via usage
            return {"encryptedPassword": self.password}
