"""Canonical models live in database.models. Do not define a second Base here."""
from database.models import *  # noqa: F401,F403
from database.models import Base  # noqa: F401
