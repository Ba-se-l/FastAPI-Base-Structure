from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import BaseModel as Base


class CasbinRule(Base):
    """Persistent storage row for a single Casbin policy or grouping line.

    The semantic meaning of v0..v5 depends on the model specification in
    rbac_model.conf. For standard policies ('p'):
        v0: Subject (role name or 'user:<id>')
        v1: Resource (object namespace)
        v2: Action (permitted operation)
    For grouping policies ('g'):
        v0: Member (user subject or child role)
        v1: Parent role

    Attributes:
        id: Primary key unique identifier.
        ptype: Policy type token ('p' for permission, 'g' for role inheritance).
        v0: First rule parameter.
        v1: Second rule parameter.
        v2: Third rule parameter.
        v3: Fourth rule parameter.
        v4: Fifth rule parameter.
        v5: Sixth rule parameter.
    """

    __tablename__ = 'casbin_rule'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ptype: Mapped[str] = mapped_column(String(255), nullable=False)
    v0: Mapped[str] = mapped_column(String(255), nullable=False)
    v1: Mapped[str] = mapped_column(String(255), nullable=False)
    v2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    v3: Mapped[str | None] = mapped_column(String(255), nullable=True)
    v4: Mapped[str | None] = mapped_column(String(255), nullable=True)
    v5: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __str__(self) -> str:
        """Serializes the rule line for Casbin's load_policy parser.

        The adapter calls str(row) for every row during load_policy(); without this
        method, Casbin fails to parse stored policy lines correctly.

        Returns:
            Comma-separated representation of the policy rule.
        """
        values: list[str] = [self.ptype]
        for val in (self.v0, self.v1, self.v2, self.v3, self.v4, self.v5):
            if val is None:
                break
            values.append(val)
        return ', '.join(values)

    def __repr__(self) -> str:
        return f'<CasbinRule {self.id}: "{self}">'
