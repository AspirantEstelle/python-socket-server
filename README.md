# Python Socket Server 실습

Python 표준 라이브러리만 사용한다. 별도 패키지 설치는 필요 없다.

## 실행 (Windows PowerShell)

이 폴더에서 첫 번째 터미널:

```powershell
py server.py
```

서버를 켜둔 상태에서 같은 폴더의 두 번째 터미널:

```powershell
curl.exe --http1.1 -X POST -S -H "Authorization: JWT test-token" -H "Accept: application/json" -F "author=1" -F "title=curl 테스트" -F "text=API curl로 작성된 AP 테스트 입력 입니다." -F "created_date=2024-06-10T18:34:00+09:00" -F "published_date=2024-06-10T18:34:00+09:00" -F "image=@sample.png;type=image/png" http://127.0.0.1:8000/api_root/Post/
```

`py`를 찾지 못하면 설치된 Python 실행 파일의 전체 경로로 실행한다.
8000 포트가 사용 중이면 `py server.py --port 8001`로 실행하고 curl 주소도 8001로 바꾼다.

## 결과와 제출

- `request/년-월-일-시-분-초.bin`: 요청 줄, HTTP 헤더, 빈 줄, multipart 본문을 포함한 수신 원본 바이트.
- `images/년-월-일-시-분-초-1.png`: multipart의 `image` 필드에서 추출한 파일. 원본 확장자에 따라 달라진다.
- 이미지 파일을 열어 원본과 동일하게 보이는지 확인한다.
- `server.py`, 이 설명, 실제 생성된 `.bin`과 이미지 파일을 GitHub에 올려 저장소 URL을 제출한다.

`sample.png`는 수업 예제 프로젝트의 `media/images/pig.png`를 복사한 테스트 입력이다.
예제 인증 문자열은 테스트 값이며 이 서버는 인증을 검사하지 않는다.
이 서버의 역할은 요청 저장이며 Django 게시글이나 데이터베이스를 만들지 않는다.
Content-Length가 포함된 일반 curl 파일 업로드를 대상으로 한다(본문 최대 20 MiB).
`--once`를 붙이면 요청 하나를 처리한 후 종료한다.
