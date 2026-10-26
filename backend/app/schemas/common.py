from decimal import Decimal
from typing import Annotated

from pydantic import Field, StringConstraints

# Valor monetário de entrada: positivo, no máximo 2 casas decimais, cabe em NUMERIC(14,2).
# Na resposta JSON os Decimal saem como string ("212.00") para não perder precisão.
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
