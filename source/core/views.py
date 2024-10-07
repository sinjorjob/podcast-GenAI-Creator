import os
import uuid
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from .utils import generate_audio, generate_timestamped_transcript, format_transcript_with_gpt,update_formatted_transcript,generate_podcast_title
from .models import Podcast
from django.views.decorators.csrf import csrf_protect
from urllib.parse import unquote
import json
from django.http import HttpResponse
from django.template.loader import render_to_string
import base64
import urllib
from urllib.parse import unquote, quote

def home(request):
    return render(request, 'core/home.html')
@csrf_protect
def upload_pdf(request):
    if request.method == 'POST':
        pdf_file = request.FILES.get('pdf_file')
        special_instructions = request.POST.get('special_instructions', '')
        if pdf_file:
            original_filename = os.path.splitext(pdf_file.name)[0]
            temp_filename = f"{uuid.uuid4()}.pdf"
            temp_path = os.path.join(settings.TEMP_ROOT, temp_filename)
            with open(temp_path, 'wb+') as destination:
                for chunk in pdf_file.chunks():
                    destination.write(chunk)
            
            # Generate podcast title from PDF content
            with open(temp_path, 'rb') as f:
                pdf_content = f.read()
            podcast_title = generate_podcast_title(pdf_content, settings.OPENAI_API_KEY)
            
            # URLエンコードを行う
            encoded_podcast_title = quote(podcast_title)
            
            # special_instructions が空でない場合のみ、URLに含める
            if special_instructions:
                encoded_special_instructions = quote(special_instructions)
                return redirect('generate_podcast', 
                                input_type='pdf', 
                                input_filename=temp_filename, 
                                podcast_title=encoded_podcast_title, 
                                special_instructions=encoded_special_instructions)
            else:
                return redirect('generate_podcast', 
                                input_type='pdf', 
                                input_filename=temp_filename, 
                                podcast_title=encoded_podcast_title)
    return redirect('home')

@csrf_protect
def upload_text(request):
    if request.method == 'POST':
        input_text = request.POST.get('input_text')
        special_instructions = request.POST.get('special_instructions', '')
        if input_text:
            temp_filename = f"{uuid.uuid4()}.txt"
            temp_path = os.path.join(settings.TEMP_ROOT, temp_filename)
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(input_text)
            podcast_title = generate_podcast_title(input_text, settings.OPENAI_API_KEY)
            
            # URLエンコードを行う
            encoded_podcast_title = quote(podcast_title)
            
            # special_instructions が空でない場合のみ、URLに含める
            if special_instructions:
                encoded_special_instructions = quote(special_instructions)
                return redirect('generate_podcast', 
                                input_type='text', 
                                input_filename=temp_filename, 
                                podcast_title=encoded_podcast_title, 
                                special_instructions=encoded_special_instructions)
            else:
                return redirect('generate_podcast', 
                                input_type='text', 
                                input_filename=temp_filename, 
                                podcast_title=encoded_podcast_title)
    return redirect('home')

def generate_podcast(request, input_type, input_filename, podcast_title, special_instructions=None):
    try:
        decoded_title = unquote(podcast_title)
        decoded_special_instructions = unquote(special_instructions) if special_instructions else ''
        input_path = os.path.join(settings.TEMP_ROOT, input_filename)
        
        audio_file_path, transcript = generate_audio(input_path, settings.OPENAI_API_KEY, decoded_special_instructions)
        timestamped_transcript = generate_timestamped_transcript(audio_file_path, settings.OPENAI_API_KEY)

        formatted_transcript = format_transcript_with_gpt(transcript, timestamped_transcript, settings.OPENAI_API_KEY)

        podcast = Podcast(
            title=decoded_title,
            transcript=transcript,
            timestamped_transcript=timestamped_transcript,
            formatted_transcript=formatted_transcript
        )
        
        with open(audio_file_path, 'rb') as audio_file:
            podcast.audio_file.save(f"{uuid.uuid4()}.mp3", audio_file)
        
        podcast.save()

        updated_formatted_transcript = update_formatted_transcript(podcast.timestamped_transcript, podcast.formatted_transcript, settings.OPENAI_API_KEY)
        
        podcast.formatted_transcript = updated_formatted_transcript
        podcast.save()
        
        os.remove(input_path)

        return JsonResponse({
            'status': 'success',
            'audio_url': podcast.audio_file.url,
            'formatted_transcript': json.dumps(updated_formatted_transcript, ensure_ascii=False),
            'podcast_id': podcast.id
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'エラーが発生しました。エラー内容は以下です。{str(e)}'
        })
        
         
def format_transcript(transcript):
    lines = transcript.split('\n')
    formatted_lines = []
    for line in lines:
        if ':' in line:
            speaker, text = line.split(':', 1)
            speaker = speaker.strip().lower()
            if 'host' in speaker:
                formatted_lines.append(f'<span class="speaker speaker-host">{speaker}</span>:{text}')
            elif 'guest1' in speaker:
                formatted_lines.append(f'<span class="speaker speaker-guest1">{speaker}</span>:{text}')
            elif 'guest2' in speaker:
                formatted_lines.append(f'<span class="speaker speaker-guest2">{speaker}</span>:{text}')
            else:
                formatted_lines.append(f'<span class="speaker">{speaker}</span>:{text}')
        else:
            formatted_lines.append(line)
    return '\n'.join(formatted_lines)

def podcast_list(request):
    podcasts = Podcast.objects.all().order_by('-created_at')
    return render(request, 'core/podcast_list.html', {'podcasts': podcasts})


def podcast_detail(request, podcast_id):
    podcast = Podcast.objects.get(id=podcast_id)
    return render(request, 'core/podcast_result.html', {
        'audio_url': podcast.audio_file.url,
        'formatted_transcript': json.dumps(podcast.formatted_transcript, ensure_ascii=False),
        'podcast_id': podcast.id
    })


def generate_standalone_html(request, podcast_id):
    podcast = Podcast.objects.get(id=podcast_id)
    
    # 音声ファイルをBase64エンコード
    with open(podcast.audio_file.path, 'rb') as audio_file:
        encoded_audio = base64.b64encode(audio_file.read()).decode('utf-8')
    
    context = {
        'audio_base64': f"data:audio/mpeg;base64,{encoded_audio}",
        'formatted_transcript': json.dumps(podcast.formatted_transcript, ensure_ascii=False),
        'podcast_id': podcast.id,
        'is_standalone': True
    }
    
    html_content = render_to_string('core/podcast_result.html', context)
    
    response = HttpResponse(html_content, content_type='text/html')
    response['Content-Disposition'] = f'attachment; filename="podcast_{podcast_id}.html"'
    
    return response