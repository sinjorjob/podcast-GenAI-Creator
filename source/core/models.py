from django.db import models

class Podcast(models.Model):
    title = models.CharField(max_length=255)
    audio_file = models.FileField(upload_to='podcasts/')
    transcript = models.TextField()
    timestamped_transcript = models.TextField()
    formatted_transcript = models.JSONField(null=True, blank=True)  # 新しいフィールド
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title