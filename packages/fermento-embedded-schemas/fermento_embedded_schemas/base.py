class BaseSchema:
    def __init__(self, *args, **kwargs) -> None:
        for k, v in kwargs.items():
            if k in self._get_fields():
                setattr(self, k, v)

    @classmethod
    def _get_fields(cls) -> list[str]:
        raise NotImplementedError("Subclasses must implement _get_fields method")

    @classmethod
    def from_dict(cls, data: dict) -> "BaseSchema":
        fields = cls._get_fields()
        filtered_data = {k: v for k, v in data.items() if k in fields}
        return cls(**filtered_data)

    def to_dict(self) -> dict:
        result = {}
        for field in self._get_fields():
            if hasattr(self, field):
                val = getattr(self, field)
            else:
                val = None
            result[field] = val
        return result

    @classmethod
    def validate(cls, data: dict) -> None:
        fields = cls._get_fields()
        for field in fields:
            if field not in data:
                raise KeyError(f"Missing field '{field}' from: {data}")
