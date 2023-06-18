

class MissingAssumptionsException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.type = kwargs['type'] if 'type' in kwargs else None
