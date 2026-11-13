import time
from collections.abc import Callable


def retry_on_transient_error[T](
    func: Callable[[], T],
    *,
    exceptions: tuple[type[Exception], ...],
    never_retry: tuple[type[Exception], ...] = (),
    attempts: int = 2,
    delay_seconds: float = 1.5,
) -> T:
    """Repete uma chamada externa, poucas vezes, em falhas passageiras (limite de taxa,
    rede, modelo gratuito que ignora o schema pedido).

    Só repete os tipos de `exceptions`, nunca os de `never_retry`, e a exceção da
    última tentativa sempre sobe.
    """
    last_exc: Exception
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except never_retry:
            raise
        except exceptions as exc:
            last_exc = exc
            if attempt < attempts:
                time.sleep(delay_seconds)
    raise last_exc
