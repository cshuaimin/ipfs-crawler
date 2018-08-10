from django.db import models

class Html(models.Model):
    multihash = models.CharField(max_length=49)
    filename = models.CharField(max_length=128)
    type = models.CharField(max_length=4)
    title = models.TextField()
    text = models.TextField()

    def __str__(self):
        return self.title or self.filename or self.multihash