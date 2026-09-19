from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings

# Le limiteur était figé à "60/minute" alors que la configuration exposait déjà
# RATE_LIMIT_REQUESTS et RATE_LIMIT_WINDOW : les tests posaient la variable en croyant
# désarmer la limite, et se faisaient limiter au bout de soixante requêtes. Ce sont
# désormais les valeurs de configuration qui s'appliquent, et RATE_LIMIT_ENABLED=false
# désarme complètement le limiteur — ce dont les harnais ont besoin.
_WINDOW_UNIT = "minute" if settings.rate_limit_window == 60 else "second"
DEFAULT_LIMIT = f"{settings.rate_limit_requests}/{_WINDOW_UNIT}"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[DEFAULT_LIMIT],
    enabled=settings.rate_limit_enabled,
)
