# podcast-GenAI-Creator

# PodcastForge

PodcastForgeは、PDFやテキストファイルを魅力的なポッドキャスト形式の音声コンテンツに変換するDjangoベースのウェブアプリケーションです。
AI駆動の音声合成と同期トランスクリプト機能を備え、情報の吸収を快適かつ効率的にします。

## 主な機能

- PDF/テキストからAI生成ポッドキャストを作成
- 複数話者による自然な会話形式の音声合成
- 音声に同期したインタラクティブトランスクリプト 
　　※生成された音声ファイルからタイムスタンプ情報を抽出し文章単位の再生時間の定義データを生成AIを利用して生成（※1）  
- スタンドアロンHTML出力機能  

※1: GPT-4oを利用すると精度が高いタイムスタンプデータが生成できます。  
　　 GPT-4o-miniだと若干精度が悪いので、音声を再生した際に音声とトランスクリプトがずれるケースがあります。  

## 必要条件

- OpenAI API キー

## インストール

1. リポジトリをクローン:
   ```
   git clone https://github.com/yourusername/podcastforge.git
   cd source
   ```

2. 仮想環境を作成し、アクティベート:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

3. 依存関係をインストール:
   ```
   pip install -r requirements.txt
   ```

4. 環境変数を設定:
   `.env`ファイルをプロジェクトのルートディレクトリに作成し、以下の内容を追加:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ```

5. データベースをマイグレート:
   ```
   python manage.py makemigrations
   python manage.py migrate
   ```

## 使用方法

1. 開発サーバーを起動:
   ```
   python manage.py runserver
   ```

2. ブラウザで `http://localhost:8000` にアクセス

3. PDFファイルをアップロードするか、テキストを入力

4. 「Podcast音声の生成」ボタンをクリック

5. 生成されたポッドキャストを再生し、トランスクリプトを確認

## 主要コンポーネント

- `views.py`: メインのアプリケーションロジック
- `utils.py`: 音声生成、トランスクリプト作成などのユーティリティ関数(利用するOpenAIモデルはこのファイル内で変更できます）
- `templates/core/home.html`: メインのユーザーインターフェース
- `templates/core/podcast_result.html`: ポッドキャスト再生・表示ページ

## 設定

`settings.py`ファイルで以下の設定を確認・調整してください:

- `MEDIA_ROOT`: アップロードされたファイルの保存先
- `TEMP_ROOT`: 一時ファイルの保存先
