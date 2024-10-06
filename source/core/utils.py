import io
import os
import uuid
from pathlib import Path
from typing import Tuple
from typing import List, Literal
from openai import OpenAI
from pypdf import PdfReader
from tenacity import retry, retry_if_exception_type
from promptic import llm
from pydantic import BaseModel, ValidationError
from django.conf import settings
import json

class DialogueItem(BaseModel):
    text: str
    speaker: Literal["ホスト", "ゲスト1", "ゲスト2"]

    @property
    def voice(self):
        return {
            "ホスト": "nova",
            "ゲスト1": "alloy",
            "ゲスト2": "shimmer",
        }[self.speaker]

class Dialogue(BaseModel):
    scratchpad: str
    dialogue: List[DialogueItem]

def get_mp3(text: str, voice: str, api_key: str) -> bytes:
    client = OpenAI(api_key=api_key)

    with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice=voice,
        input=text,
    ) as response:
        with io.BytesIO() as file:
            for chunk in response.iter_bytes():
                file.write(chunk)
            return file.getvalue()

def generate_audio(file_path: str, openai_api_key: str) -> Tuple[str, str]:
    if file_path.endswith('.pdf'):
        with Path(file_path).open("rb") as f:
            reader = PdfReader(f)
            text = "\n\n".join([page.extract_text() for page in reader.pages])
            print("pdf-text-info=",text)
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            print("text-info=",text)

    @retry(retry=retry_if_exception_type(ValidationError))
    @llm(model="gpt-4o-mini")

    def generate_dialogue(text: str) -> Dialogue:
        """
        Your task is to take the input text provided and turn it into an engaging, informative podcast dialogue in Japanese. The input text may be messy or unstructured, as it could come from a variety of sources like PDFs or web pages. Don't worry about the formatting issues or any irrelevant information; your goal is to extract the key points and interesting facts that could be discussed in a Japanese podcast.

        Here is the input text you will be working with:

        <input_text>
        {text}
        </input_text>

        First, carefully read through the input text and identify the main topics, key points, and any interesting facts or anecdotes. Think about how you could present this information in a fun, engaging way that would be suitable for an audio podcast.

        <scratchpad>
        以下の点を考慮しながら、入力テキストから抽出した主要なトピックやポイントについて、クリエイティブな議論の方法をブレインストーミングしてください：

        1. アナロジー、ストーリーテリング技法、仮説的なシナリオを使用して、内容をリスナーにとってより身近で魅力的なものにする方法
        2. 一般的な聴衆にとってアクセスしやすいように、専門用語の使用を避け、複雑な概念を簡単な言葉で説明する方法
        3. 入力テキストのギャップを埋めたり、ポッドキャストで探求できる思考を促す質問を考える方法
        4. 情報提供と娯楽のバランスを取りながら、クリエイティブなアプローチを取る方法

        ここに、日本語でブレインストーミングのアイデアとポッドキャストの対話の大まかな概要を書いてください。最後に繰り返したい主要な洞察や要点を必ず記述してください。
        </scratchpad>

        Now that you have brainstormed ideas and created a rough outline, it's time to write the actual podcast dialogue in Japanese. Aim for a natural, conversational flow between the host and any guest speakers. Incorporate the best ideas from your brainstorming session and make sure to explain any complex topics in an easy-to-understand way.

        <podcast_dialogue>
        ブレインストーミングセッションで考えた主要なポイントやクリエイティブなアイデアに基づいて、魅力的で情報量の多いポッドキャストの対話を以下に日本語で書いてください。以下の点に注意してください：

        1. 自然な会話調を使用し、一般の聴衆にも理解できるように必要な文脈や説明を含めてください。
        2. ゲストは入力テキスト内で裏付けられていない内容を含めてはいけません。
        3. 音声として読み上げられることを想定して出力をデザインしてください。これは直接音声に変換されます。
        4. [ホスト]や[ゲスト]などの括弧付きのプレースホルダーは使用しないでください。
        5. ホストやゲストは相手の話を注意深く聞いてから発言しますが、互いに話を途中で遮ることでテンポよく会話を進めることが出来ます。
        6. スクリプトをリアルにするために、「そうですね」「なるほど」などの相づちや、「えーと」や「あの」などの考え込む様子を表す表現を適切に使用してください。
        7. トピックに沿って魅力的な流れを維持しながら、できるだけ長く詳細な対話を作成してください。
        8. 入力テキストからの重要な情報を楽しい方法で伝えながら、可能な限り長いポッドキャストエピソードを作成することを目指してください。

        対話の最後に、ホストとゲストスピーカーが自然に議論の主な洞察と要点をまとめるようにしてください。これは会話から自然に流れ出すようにし、カジュアルで会話的な方法で主要なポイントを繰り返すようにしてください。明らかな要約のように聞こえないようにし、締めくくる前に中心的なアイデアを最後にもう一度強調してリスナーの印象に残すことが目標です。
        </podcast_dialogue>
        """

    llm_output = generate_dialogue(text)

    audio = b""
    transcript = ""

    for line in llm_output.dialogue:
        audio_chunk = get_mp3(line.text, line.voice, openai_api_key)
        audio += audio_chunk
        transcript += f"{line.speaker}: {line.text}\n\n"

    audio_filename = f"{uuid.uuid4()}.mp3"
    audio_path = os.path.join(settings.TEMP_ROOT, audio_filename)
    with open(audio_path, 'wb') as f:
        f.write(audio)

    return audio_path, transcript


def generate_timestamped_transcript(audio_file_path, api_key):
    client = OpenAI(api_key=api_key)
    
    with open(audio_file_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            language="ja",
            timestamp_granularities=["word"]
        )
    
    timestamped_transcript = []

    # レスポンスの構造をチェック
    if hasattr(response, 'words') and response.words:
        # 単語レベルのタイムスタンプが利用可能な場合
        for word in response.words:
            timestamped_transcript.append({
                "start": word.start,
                "end": word.end,
                "text": word.word
            })
    elif hasattr(response, 'segments') and response.segments:
        # セグメントレベルのタイムスタンプしか利用できない場合
        for segment in response.segments:
            timestamped_transcript.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            })
    else:
        # どちらも利用できない場合、全体のテキストを1つのセグメントとして扱う
        timestamped_transcript.append({
            "start": 0,
            "end": getattr(response, 'duration', 0),
            "text": getattr(response, 'text', '')
        })

    return json.dumps(timestamped_transcript, ensure_ascii=False, indent=2)




def format_transcript_with_gpt(transcript, timestamped_transcript, api_key):
    client = OpenAI(api_key=api_key)
    
    prompt = f"""
#transcriptは生成AIが生成した会話データに話者の情報を追加したものです。
#timestamped transcriptは#transcriptを元にWhisperで音声データを生成し、その音声データのタイムスタンプ情報をWhisterで取得したデータです。
#timestamped transcriptのタイムスタンプ情報を活用して、音声データを再生した際にリアルタイムで再生されている単語をハイライト表示する必要があります。
ただし、#timestamped transcriptの情報は、#transcriptと比べて、各発言者の情報や文章の終わり「。」等のデータが欠落していたり、テキストが誤変換されているケースがあります。
そのため、画面上にきれいな会話形式の情報を表示させつつ、適切な単語レベルのハイライトが実現できません。

上記の課題を解決するために、#変換ルールに従い、#transcriptと#timestamped transcriptを活用してJson形式の#出力フォーマットのデータを生成してください。
最終回答には余計な文字列や記号「```jsonなど」をつけないでください。

#変換ルール
---
1. #transcriptの情報と#timestamped transcriptの情報を並行して参照しながら処理を進めてください。

2. 話し手は「ホスト:」「ゲスト1:」「ゲスト2:」の3種類です。各話し手の発言は、その話し手を表す文字列（例：「ホスト:」）から、次の話し手を表す文字列が出現するまでの全ての文章を1つの発言としてまとめてください。最後の話し手の発言は、次の話し手を表す文字列が現れるまで、もしくはデータの終わりまでを1つの発言としてまとめてください。

3. 話し手を表す文字列（「ホスト:」「ゲスト1:」「ゲスト2:」）は、発言内容から除外し、speakerフィールドに該当する話し手名（「ホスト」「ゲスト1」「ゲスト2」）のみを入力してください。

4. 各話し手の連続した発言は、途中に他の話し手の発言が入らない限り、1つのオブジェクトにまとめてください。他の話し手の発言が入った場合は、新しいオブジェクトを作成してください。

5. まとめた発言内の改行や段落分けを取り除き、1つの連続した文章にしてください。これは変換後のtext値となります。

6. #timestamped transcriptの情報から、1つの連続した文章の最初の単語の開始時間（start）と、一番最後の単語の終了時間（end）を抽出してください。
   - 開始時間（start）は、その発言の最初の単語の"start"値をそのまま使用します。
   - 終了時間（end）は、その発言の最後の単語の"end"値をそのまま使用します。
   - これらの値は変更せず、そのまま転記してください。

7. #timestamped transcriptの情報に誤変換がある場合は、#transcriptの情報を優先して使用してください。前後の文脈を考慮して、正しいテキストを選択し、1つの文章にまとめてください。

8. 各発言を以下のJSON形式でまとめ、以下の構造を持つオブジェクトの配列を作成してください：
   ```
   {{
     "speaker": "発言者名",
     "text": "1つにまとめた発言内容",
     "start": 1つにまとめた発言内容の最初の単語の#timestamped transcriptからそのまま転記した開始時間,
     "end": 1つにまとめた発言内容の最後の単語の#timestamped transcriptからそのまま転記した終了時間
   }}
   ```

9. 発言の順序は#transcriptの情報に従ってください。

10. すべての時間は秒単位で、#timestamped transcriptに記載されている通りの小数点以下の桁数を保持してください。

11. 最終的な出力は、#出力フォーマットに従って整形してください。

12. 処理中に疑問が生じた場合は、文脈や前後の情報を考慮して最も適切と思われる判断を行ってください。

13. これまでに生成した文章毎のタイムスタンプ情報と#transcript、#timestamped transcriptを再度比較して文章毎の開始時刻(start),終了時刻(end)にずれがないか再チェックし、ずれがある場合はずれがない状態に修正してください。

14. 最終的な変換した情報JSONデータの#出力フォーマットで出力し、出力には余計な文字列や記号「```jsonなど」をつけないでください。
---


#出力フォーマット:
[
    {{
    "speaker": "xx",
    "text": "xxx",
    "start": xxx,
    "end": xxx
    }},
    {{
    "speaker": "xx",
    "text": "xxx",
    "start": xxx,
    "end": xxx
    }}
]

#transcript:
{transcript}

#timestamped transcript:
{timestamped_transcript}
"""
    #print("prompt=",prompt)
    response = client.chat.completions.create(
        temperature=0.1,
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that formats transcripts."},
            {"role": "user", "content": prompt}
        ]
    )

    formatted_transcript = json.loads(response.choices[0].message.content)
    return formatted_transcript




def update_formatted_transcript(timestamped_transcript, formatted_transcript, api_key):
    client = OpenAI(api_key=api_key)
    
    prompt = f"""
#formated-transcriptは#timestamped_transcriptのデータを元にスピーカごとに一定のまとまりの文章でタイムスタンプをまとめ直した情報です。
#formated-transcriptを使って音声再生すると音声と#formated-transcriptの時間がずれている箇所があります。

#timestamped_transcriptの情報と#formated-transcriptを比較して、#formated-transcriptの各データのstart,endの時間が#timestamped_transcriptの情報内の情報とずれている箇所を特定して、再生時間が一致するように#formated-transcriptを修正してください。

修正後のすべての#formated-transcriptのデータを同じJSON形式で出力し、出力には余計な文字列や記号「```jsonなど」をつけないでください。

#timestamped_transcript
===
{timestamped_transcript}
===

#formated-transcript
===
{json.dumps(formatted_transcript, ensure_ascii=False)}
===
    """
    print("修正用プロンプト＝",prompt)
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.1,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that updates transcripts."},
            {"role": "user", "content": prompt}
        ]
    )

    updated_formatted_transcript = json.loads(response.choices[0].message.content)
    return updated_formatted_transcript


def generate_podcast_title(input_text, api_key, max_length=50):
    client = OpenAI(api_key=api_key)
    
    prompt = f"""
Generate a concise and descriptive title for a podcast based on the following text in japanese. The title should be catchy, informative, and no longer than {max_length} characters:

{input_text[:500]}  # Using first 500 characters to keep the prompt short

Output the title only, without any additional text or formatting.
"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Using a smaller model for faster response
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates podcast titles."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=60,  # Limiting the response length
        temperature=0.7  # Slightly creative, but not too random
    )

    title = response.choices[0].message.content.strip()
    return title[:max_length]  # Ensuring the title doesn't exceed max_length