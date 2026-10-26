from decimal import Decimal
from typing import Annotated

from pydantic import Field, StringConstraints

# Monetary input: positive, at most 2 decimal places, fits NUMERIC(14,2).
# In JSON responses Decimal values are serialized as strings ("212.00") to keep precision.
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
