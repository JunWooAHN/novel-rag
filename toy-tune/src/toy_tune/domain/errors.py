class ToyTuneError(Exception):
    """Public errors must not contain source prose or credentials."""


class ValidationError(ToyTuneError):
    pass


class ConflictError(ToyTuneError):
    pass


class IntegrityError(ToyTuneError):
    pass


class UnsupportedError(ToyTuneError):
    pass
