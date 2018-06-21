class ExtendedMessage:
    def __init__(self, category_id, instance_id, template, params):
        self.category_id = category_id
        self.instance_id = instance_id
        self.template = template
        self.params = params

    def get_message(self):
        try:
            return self.template % tuple(self.params)
        except TypeError:
            # sometimes params are sent even tho the template does not include param placeholders
            # ex: ExtendedMessage: [20000, 134870373, 'Your ability to send private messages has been revoked temporarily with a GM gag.', [1000]]
            return self.template

    def __str__(self):
        return str([self.category_id, self.instance_id, self.template, self.params, self.get_message()])
