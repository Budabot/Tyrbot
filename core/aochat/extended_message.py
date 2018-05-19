class ExtendedMessage:
    def __init__(self, category_id, instance_id, template, params):
        self.category_id = category_id
        self.instance_id = instance_id
        self.template = template
        self.params = params

    def get_message(self):
        return self.template % tuple(self.params)
