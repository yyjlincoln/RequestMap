from typing import Any, Callable


class JITDict(dict):
    '''
    Just-in-time dictionary
    - fetches the key from getData in real time
    - stores a copy of any changes
    - returns None if a key does not exist
    '''

    def __init__(self, getData: Callable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.getData = getData

    def __getitem__(self, key: str) -> Any:
        if super().__contains__(key):
            return super().__getitem__(key)
        else:
            return self.getData(key)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)

    def __contains__(self, __o: object) -> bool:
        sup = super().__contains__(__o)
        if not sup:
            return self.getData(__o) is not None
        return True

    def get(self, key: str, default: Any = None) -> Any:
        data = self.__getitem__(key)
        if data:
            return data
        else:
            return default

    def __delitem__(self, key: str):
        self.__setitem__(key, None)
