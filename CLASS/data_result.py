class DATA_Result(dict):
    def __init__(self, result=False, message=None, data=None):
        super().__init__()
        self['result'] = result
        self['message'] = message
        self['data'] = data

    def get_result(self):
        return self['result']

    def set_result(self, value):
        if isinstance(value, str):
            self['result'] = False
            self['message'] = value
        else:
            self['result'] = value
            self['message'] = None

    def get_message(self):
        return self['message']

    def set_message(self, message):
        self['message'] = message

    def get_data(self):
        return self['data']

    def set_data(self, data):
        self['data'] = data

