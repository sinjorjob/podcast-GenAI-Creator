from django.contrib import admin
from django import forms
from .models import Podcast
from django_json_widget.widgets import JSONEditorWidget

class PodcastAdminForm(forms.ModelForm):
    class Meta:
        model = Podcast
        fields = '__all__'
        widgets = {
            'formatted_transcript': JSONEditorWidget,
        }

class PodcastAdmin(admin.ModelAdmin):
    form = PodcastAdminForm
    list_display = ('title', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'transcript', 'timestamped_transcript', 'formatted_transcript')
    readonly_fields = ('created_at', 'timestamped_transcript')
    fieldsets = (
        (None, {
            'fields': ('title', 'audio_file', 'transcript')
        }),
        ('タイムスタンプ付きトランスクリプト', {
            'fields': ('timestamped_transcript',),
            'classes': ('collapse',)
        }),
        ('整形済みトランスクリプト', {
            'fields': ('formatted_transcript',),
            'classes': ('collapse',)
        }),
        ('日時情報', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # 編集時
            return self.readonly_fields + ('audio_file',)
        return self.readonly_fields  # 新規作成時

admin.site.register(Podcast, PodcastAdmin)