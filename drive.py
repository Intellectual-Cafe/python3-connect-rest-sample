"""Module keeping drive things together

"""

class FileItem:
    """File data structure

    """
    def __init__(self, _id, name, created_by, date_created, summary, file_type, tags=None):
        self._id = _id,
        self.name = name
        self.created_by = created_by
        self.date_created = date_created
        self.summary = summary
        self.file_type = file_type
        self.tags = tags

    def __str__(self):
        return '{} [{}]'.format(self.name, self.file_type)

    def serialize(self):
        """JSON Encoding

        """
        return {
            'id' : self._id,
            'name' : self.name,
            'created_by' : self.created_by,
            'date_created' : self.date_created,
            'summary' : self.summary,
            'file_type' : self.file_type,
            'tags' : self.tags
        }
