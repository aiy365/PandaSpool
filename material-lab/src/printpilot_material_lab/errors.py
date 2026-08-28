class MaterialLabError(Exception):
    """Base error with a stable machine-readable code."""

    code = "material_lab_error"


class InputError(MaterialLabError):
    code = "invalid_input"


class EvidenceConflictError(MaterialLabError):
    code = "evidence_conflict"


class ProfileBuildError(MaterialLabError):
    code = "profile_build_error"


class DatabaseError(MaterialLabError):
    code = "database_error"
