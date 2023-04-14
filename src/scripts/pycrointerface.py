import pycromanager

class PycroConnectionError(Exception):
    pass

class PycroInterface:
    def __init__(self):
        try:
            self.core = pycromanager.Core()
        except Exception as e:
            raise PycroConnectionError(str(e))
        
