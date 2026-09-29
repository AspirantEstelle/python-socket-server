"""curl 요청 원본과 multipart 이미지 파일을 저장하는 실습용 소켓 서버."""

import argparse
import json
import socket
import time
from datetime import datetime
from email import policy
from email.parser import BytesHeaderParser, BytesParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAX_BODY = 20 * 1024 * 1024


def receive_request(conn):
    # TCP는 요청 전체를 한 번에 주지 않으므로 헤더 끝까지 반복해서 받는다.
    data = bytearray()
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(4096)
        if not chunk:
            raise ValueError("요청 헤더 수신 중 연결이 끊겼습니다.")
        data.extend(chunk)
        if len(data.split(b"\r\n\r\n", 1)[0]) > 65536:
            raise ValueError("요청 헤더가 너무 큽니다.")

    head, body = bytes(data).split(b"\r\n\r\n", 1)
    request_line, header_bytes = head.split(b"\r\n", 1)
    headers = BytesHeaderParser(policy=policy.default).parsebytes(header_bytes)
    if headers.get("Transfer-Encoding"):
        raise ValueError("이 실습 서버는 Content-Length 방식만 지원합니다.")
    lengths = headers.get_all("Content-Length", [])
    if len(lengths) != 1:
        raise ValueError("Content-Length 헤더가 하나 필요합니다.")
    length = int(lengths[0])
    if not 0 <= length <= MAX_BODY:
        raise ValueError("본문은 0~20 MiB 범위여야 합니다.")

    if headers.get("Expect", "").lower() == "100-continue":
        conn.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")

    # Content-Length만큼 모두 받을 때까지 반복한다. 이미지도 바이트로 유지한다.
    body = bytearray(body[:length])
    while len(body) < length:
        chunk = conn.recv(min(65536, length - len(body)))
        if not chunk:
            raise ValueError("요청 본문 수신 중 연결이 끊겼습니다.")
        body.extend(chunk)
    return head + b"\r\n\r\n" + bytes(body), headers, bytes(body), request_line


def save_raw_request(raw):
    folder = ROOT / "request"
    folder.mkdir(exist_ok=True)
    while True:
        path = folder / (datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + ".bin")
        try:
            # 같은 초에 두 요청이 와도 기존 결과를 덮어쓰지 않는다.
            with path.open("xb") as file:
                file.write(raw)
            return path
        except FileExistsError:
            time.sleep(0.1)


def save_images(headers, body, stamp):
    if headers.get_content_type() != "multipart/form-data":
        return []
    # HTTP 본문을 MIME 파서에 전달해 multipart 경계와 각 파트를 해석한다.
    mime_header = (
        "MIME-Version: 1.0\r\nContent-Type: "
        + str(headers["Content-Type"]) + "\r\n\r\n"
    ).encode("utf-8")
    message = BytesParser(policy=policy.default).parsebytes(mime_header + body)
    if not message.is_multipart():
        raise ValueError("multipart 경계(boundary)를 확인할 수 없습니다.")
    saved = []
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        if part.get_param("name", header="content-disposition") != "image":
            continue
        if not part.get_filename():
            continue
        extension = Path(part.get_filename()).suffix.lower()
        if extension not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
            extension = ".img"
        folder = ROOT / "images"
        folder.mkdir(exist_ok=True)
        # 클라이언트의 경로는 사용하지 않고 서버에서 파일명을 정한다.
        path = folder / f"{stamp}-{len(saved) + 1}{extension}"
        path.write_bytes(part.get_payload(decode=True) or b"")
        saved.append(str(path.relative_to(ROOT)))
    return saved


def respond(conn, status, result):
    body = json.dumps(result, ensure_ascii=False).encode("utf-8")
    header = (
        f"HTTP/1.1 {status}\r\n"
        "Content-Type: application/json; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    ).encode("ascii")
    conn.sendall(header + body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--once", action="store_true", help="요청 하나를 처리한 뒤 종료")
    args = parser.parse_args()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", args.port))
        server.listen(5)
        print(f"Listening: http://127.0.0.1:{args.port} (Ctrl+C to stop)", flush=True)
        while True:
            conn, address = server.accept()
            with conn:
                conn.settimeout(15)
                try:
                    raw, headers, body, request_line = receive_request(conn)
                    raw_path = save_raw_request(raw)
                    images = save_images(headers, body, raw_path.stem)
                    result = {"request": str(raw_path.relative_to(ROOT)), "images": images}
                    print(address, request_line.decode("ascii", errors="replace"), result, flush=True)
                    respond(conn, "200 OK", result)
                except (ValueError, OSError) as error:
                    print(f"Request failed: {error}", flush=True)
                    try:
                        respond(conn, "400 Bad Request", {"error": str(error)})
                    except OSError:
                        pass
            if args.once:
                break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer stopped.")
